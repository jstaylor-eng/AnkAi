from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()  # Load .env before other imports

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import anki_client
from models import (
    DeckSelection, ArticleRequest, ReviewRequest,
    ProcessedArticle, Word, VocabStatus,
    RecallGenerateRequest, RecallGenerateResponse,
    RecallPassageRequest,
    ChatRequest, ChatResponse, ChatMessageModel
)
from llm_service import llm_service
from vocab_manager import VocabManager
from article_processor import ArticleProcessor


# Global instances
vocab_manager = VocabManager()
article_processor: ArticleProcessor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global article_processor
    article_processor = ArticleProcessor(vocab_manager)
    yield


app = FastAPI(
    title="AnkAi API",
    description="Language learning with Anki vocabulary",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check

@app.get("/api/health")
async def health_check():
    """Check if API and Anki are available, and sync with AnkiWeb"""
    try:
        version = await anki_client.version()

        # Auto-sync with AnkiWeb to get latest reviews from other devices
        try:
            await anki_client.sync()
            print("Auto-synced with AnkiWeb on startup")
            sync_status = "synced"
        except Exception as sync_err:
            print(f"Auto-sync failed (non-critical): {sync_err}")
            sync_status = "sync_failed"

        return {"status": "ok", "anki_connect_version": version, "sync": sync_status}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Deck operations

@app.get("/api/decks")
async def get_decks():
    """Get available Anki decks"""
    try:
        decks = await anki_client.get_deck_names()
        return {"decks": decks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/decks/select")
async def select_decks(selection: DeckSelection):
    """Select decks to use for vocabulary"""
    try:
        stats = await vocab_manager.select_decks(selection.deck_names)
        # Get daily new card limit from deck config
        daily_limit = await vocab_manager.update_daily_limit_from_deck()
        # Reinitialize article processor with updated vocab
        global article_processor
        article_processor = ArticleProcessor(vocab_manager)
        return {
            "selected": selection.deck_names,
            "stats": stats,
            "daily_new_limit": daily_limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Vocabulary operations

@app.get("/api/vocab")
async def get_vocabulary():
    """Get loaded vocabulary grouped by status"""
    vocab = vocab_manager.get_vocab_list()
    return {
        "total": len(vocab),
        "by_status": {
            "new": [w.model_dump() for w in vocab if w.status == VocabStatus.NEW],
            "due": [w.model_dump() for w in vocab if w.status == VocabStatus.DUE],
            "learned": [w.model_dump() for w in vocab if w.status == VocabStatus.LEARNED],
        }
    }


@app.get("/api/vocab/due")
async def get_due_vocab():
    """Get vocabulary due for review"""
    due_words = vocab_manager.get_words_by_status(VocabStatus.DUE)
    return {"due_words": [w.model_dump() for w in due_words]}


@app.get("/api/vocab/new")
async def get_new_vocab():
    """Get new vocabulary not yet learned"""
    new_words = vocab_manager.get_words_by_status(VocabStatus.NEW)
    return {"new_words": [w.model_dump() for w in new_words]}


@app.get("/api/vocab/daily-stats")
async def get_daily_stats():
    """Get daily new word introduction stats"""
    return vocab_manager.get_daily_stats()


@app.get("/api/word/{hanzi}")
async def get_word(hanzi: str):
    """Get info for a specific word"""
    word = vocab_manager.classify_word(hanzi)
    return word.model_dump()


def format_interval(interval: int) -> str:
    """Format interval (negative=seconds, positive=days) to human readable"""
    if interval < 0:
        # Seconds (negative value) - learning intervals use "<" prefix like Anki
        seconds = abs(interval)
        if seconds < 60:
            return "<1m"
        elif seconds < 3600:
            mins = seconds // 60
            return f"<{mins}m"
        else:
            hours = seconds // 3600
            return f"<{hours}h"
    else:
        # Days (positive value) - review intervals
        if interval == 0:
            return "<1d"
        elif interval == 1:
            return "1d"
        elif interval < 30:
            return f"{interval}d"
        elif interval < 365:
            return f"{interval // 30}mo"
        else:
            return f"{interval // 365}y"


def calculate_review_intervals(card_info: dict, deck_config: dict) -> dict:
    """
    Calculate the 4 button intervals based on card state and deck settings.

    Queue values: 0=new, 1=learning, 2=review, 3=relearning
    """
    queue = card_info.get("queue", 0)
    interval = card_info.get("interval", 0)  # Current interval in days
    factor = card_info.get("factor", 2500)   # Ease factor (2500 = 2.5x)
    left = card_info.get("left", 0)          # Learning steps remaining

    # Get deck settings
    new_config = deck_config.get("new", {})
    rev_config = deck_config.get("rev", {})
    lapse_config = deck_config.get("lapse", {})

    # Learning steps in minutes (e.g., [1, 10] for 1m, 10m)
    learning_steps = new_config.get("delays", [1, 10])
    # Graduating interval in days
    graduating_ivl = new_config.get("ints", [1, 4])[0] if new_config.get("ints") else 1
    # Easy interval in days
    easy_ivl = new_config.get("ints", [1, 4])[1] if new_config.get("ints") and len(new_config.get("ints", [])) > 1 else 4
    # Lapse (relearning) steps in minutes
    lapse_steps = lapse_config.get("delays", [10])

    # Convert minutes to negative seconds for format_interval
    def mins_to_secs(m):
        return -int(m * 60)

    def ensure_distinct(intervals_dict):
        """Ensure all 4 interval strings are distinct by adjusting duplicates."""
        keys = ["again", "hard", "good", "easy"]
        seen = {}
        result = {}

        def parse_interval(val):
            """Parse interval string and return (base, suffix, has_lt)."""
            has_lt = val.startswith("<")
            clean = val.lstrip("<")
            # Handle all possible suffixes: m, h, d, mo, y
            if clean.endswith("mo"):
                return int(clean[:-2]) if clean[:-2] else 0, "mo", has_lt
            elif clean.endswith("m"):
                return int(clean[:-1]) if clean[:-1] else 0, "m", has_lt
            elif clean.endswith("h"):
                return int(clean[:-1]) if clean[:-1] else 0, "h", has_lt
            elif clean.endswith("d"):
                return int(clean[:-1]) if clean[:-1] else 0, "d", has_lt
            elif clean.endswith("y"):
                return int(clean[:-1]) if clean[:-1] else 0, "y", has_lt
            return 0, "", has_lt

        for key in keys:
            val = intervals_dict[key]
            if val in seen:
                # Duplicate found - modify to make distinct
                base, suffix, has_lt = parse_interval(val)
                if suffix:
                    # Try incrementing until we find a unique value
                    max_increments = {"m": 60, "h": 24, "d": 365, "mo": 12, "y": 10}
                    for i in range(1, max_increments.get(suffix, 30)):
                        new_val = f"{base + i}{suffix}"
                        if new_val not in seen:
                            val = new_val
                            break
            seen[val] = True
            result[key] = val

        return result

    if queue == 0:  # New card
        if len(learning_steps) >= 2:
            # Use actual learning steps for again/good
            # Hard = midpoint between step1 and step2 (matches Anki v3 behavior)
            step1 = learning_steps[0]
            step2 = learning_steps[1]
            hard_mins = (step1 + step2 + 1) // 2  # e.g., (1+10+1)//2 = 6

            result = {
                "again": format_interval(mins_to_secs(step1)),
                "hard": format_interval(mins_to_secs(hard_mins)),
                "good": format_interval(mins_to_secs(step2)),
                "easy": format_interval(easy_ivl),
            }
        elif len(learning_steps) == 1:
            step1 = learning_steps[0]
            result = {
                "again": format_interval(mins_to_secs(step1)),
                "hard": format_interval(mins_to_secs(step1 * 5)),  # Reasonable intermediate
                "good": format_interval(graduating_ivl),
                "easy": format_interval(easy_ivl),
            }
        else:
            result = {
                "again": format_interval(mins_to_secs(1)),
                "hard": format_interval(mins_to_secs(6)),
                "good": format_interval(graduating_ivl),
                "easy": format_interval(easy_ivl),
            }
        return ensure_distinct(result)

    elif queue == 1:  # Learning card
        # Determine current step from 'left' field
        steps_remaining = left % 1000 if left else 1
        current_step_idx = len(learning_steps) - steps_remaining
        if current_step_idx < 0:
            current_step_idx = 0
        if current_step_idx >= len(learning_steps):
            current_step_idx = len(learning_steps) - 1

        current_step = learning_steps[current_step_idx] if learning_steps else 1
        next_step = learning_steps[current_step_idx + 1] if current_step_idx + 1 < len(learning_steps) else None

        # Hard = midpoint between current step and next (or current * 1.5 if last step)
        if next_step:
            hard_mins = (current_step + next_step + 1) // 2
        else:
            hard_mins = max(current_step + 1, int(current_step * 1.5))

        result = {
            "again": format_interval(mins_to_secs(learning_steps[0])),
            "hard": format_interval(mins_to_secs(hard_mins)),
            "good": format_interval(mins_to_secs(next_step)) if next_step else format_interval(graduating_ivl),
            "easy": format_interval(easy_ivl),
        }
        return ensure_distinct(result)

    elif queue == 2:  # Review card
        # Calculate based on current interval and ease factor
        ease = factor / 1000  # Convert 2500 to 2.5
        hard_factor = 1.2
        easy_bonus = 1.3

        # Again: go to relearning
        again = mins_to_secs(lapse_steps[0]) if lapse_steps else mins_to_secs(10)
        # Hard: slightly longer than current (ensure at least 1 day more)
        hard = max(interval + 1, int(interval * hard_factor))
        # Good: current * ease (ensure at least 1 day more than hard)
        good = max(hard + 1, int(interval * ease))
        # Easy: good * easy bonus (ensure at least 1 day more than good)
        easy = max(good + 1, int(interval * ease * easy_bonus))

        result = {
            "again": format_interval(again),
            "hard": format_interval(hard),
            "good": format_interval(good),
            "easy": format_interval(easy),
        }
        return ensure_distinct(result)

    elif queue == 3:  # Relearning (day)
        lapse_step = lapse_steps[0] if lapse_steps else 10
        result = {
            "again": format_interval(mins_to_secs(lapse_step)),
            "hard": format_interval(mins_to_secs(max(lapse_step + 1, lapse_step * 2))),
            "good": format_interval(max(1, interval)),
            "easy": format_interval(max(interval + 1, int(interval * 1.5), 2)),
        }
        return ensure_distinct(result)

    # Fallback defaults
    return {
        "again": "<1m",
        "hard": "6m",
        "good": "1d",
        "easy": "4d",
    }


@app.get("/api/card/{card_id}/intervals")
async def get_card_intervals(card_id: int):
    """Get next review intervals for all 4 ease buttons based on deck settings"""
    try:
        # Get card info
        cards_info = await anki_client.get_cards_info([card_id])
        if not cards_info:
            print(f"[Intervals] No card info found for card_id={card_id}")
            return {"intervals": None}

        card_info = cards_info[0]
        deck_name = card_info.get("deckName", "")
        print(f"[Intervals] Card {card_id}: queue={card_info.get('queue')}, interval={card_info.get('interval')}, factor={card_info.get('factor')}, deck={deck_name}")

        # Get deck configuration
        try:
            deck_config = await anki_client.get_deck_config(deck_name)
        except Exception as e:
            print(f"[Intervals] Could not get deck config for {deck_name}: {e}")
            deck_config = {}

        # Calculate intervals based on card state and deck settings
        intervals = calculate_review_intervals(card_info, deck_config)
        print(f"[Intervals] Calculated intervals for card {card_id}: {intervals}")

        return {
            "intervals": intervals,
            "card_state": {
                "queue": card_info.get("queue"),
                "interval": card_info.get("interval"),
                "factor": card_info.get("factor"),
            }
        }
    except Exception as e:
        print(f"[Intervals] Error getting intervals for card {card_id}: {e}")
        return {"intervals": None}


@app.get("/api/debug/vocab/{hanzi}")
async def debug_vocab(hanzi: str):
    """Debug why a word might not be matching"""
    result = {
        "searched": hanzi,
        "in_vocab": hanzi in vocab_manager.vocab,
        "in_basic": hanzi in vocab_manager.BASIC_VOCAB,
        "classification": vocab_manager.classify_word(hanzi).model_dump(),
    }

    # Search for similar words in vocab
    similar = []
    for known in vocab_manager.vocab:
        if hanzi in known or known in hanzi:
            similar.append({
                "word": known,
                "status": vocab_manager.vocab[known].status.value,
                "definition": vocab_manager.vocab[known].definition[:50]
            })
    result["similar_in_vocab"] = similar[:10]

    return result


# Article processing

@app.post("/api/article/process")
async def process_article(request: ArticleRequest) -> ProcessedArticle:
    """Process an article and annotate with vocabulary info"""
    if not article_processor:
        raise HTTPException(status_code=500, detail="Article processor not initialized")

    if not request.url and not request.text:
        raise HTTPException(status_code=400, detail="Either url or text must be provided")

    try:
        # Get remaining daily allowance for new words
        remaining_allowance = vocab_manager.get_remaining_new_allowance()
        # Use the minimum of request limit and remaining daily allowance
        effective_max_new = min(
            request.max_new_words if request.max_new_words else remaining_allowance,
            remaining_allowance
        )
        print(f"Daily new word allowance: {remaining_allowance}, using max: {effective_max_new}")

        result = await article_processor.process_article(
            text=request.text,
            url=request.url,
            rewrite=request.rewrite,
            max_new_words=effective_max_new,
            source_lang=request.source_lang
        )

        # Limit new words to daily allowance, selecting the most frequent ones
        if result.new_words and len(result.new_words) > effective_max_new:
            # Count frequency of each new word in the article
            new_word_freq = {}
            for sentence in result.sentences:
                for word in sentence.words:
                    if word.status == VocabStatus.NEW:
                        new_word_freq[word.hanzi] = new_word_freq.get(word.hanzi, 0) + 1

            # Sort new words by frequency (most frequent first)
            sorted_new_words = sorted(
                result.new_words,
                key=lambda w: new_word_freq.get(w.hanzi, 0),
                reverse=True
            )

            # Keep only the top N most frequent new words
            allowed_new_words = sorted_new_words[:effective_max_new]
            allowed_hanzi = {w.hanzi for w in allowed_new_words}
            excess_hanzi = {w.hanzi for w in sorted_new_words[effective_max_new:]}

            # Update the new_words list
            result.new_words = allowed_new_words

            # Change excess new words to "unknown" status in sentences
            for sentence in result.sentences:
                for word in sentence.words:
                    if word.hanzi in excess_hanzi and word.status == VocabStatus.NEW:
                        word.status = VocabStatus.UNKNOWN

            # Update stats
            result.stats["new_count"] = len(allowed_new_words)
            print(f"Selected top {effective_max_new} new words by frequency from {len(excess_hanzi) + effective_max_new} found")

        # Mark new words as "introduced" for daily tracking
        if result.new_words:
            new_word_hanzi = [w.hanzi for w in result.new_words]
            vocab_manager.mark_words_introduced(new_word_hanzi)

        # Add daily stats to the response
        result.stats["daily_new_remaining"] = vocab_manager.get_remaining_new_allowance()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Recall practice

@app.post("/api/recall/generate")
async def generate_recall_sentences(request: RecallGenerateRequest) -> RecallGenerateResponse:
    """Generate sentences for recall practice using user's vocabulary"""
    try:
        learned = vocab_manager.get_words_by_status(VocabStatus.LEARNED)
        due = vocab_manager.get_words_by_status(VocabStatus.DUE)
        new = vocab_manager.get_words_by_status(VocabStatus.NEW)

        if not learned and not due:
            raise HTTPException(
                status_code=400,
                detail="No vocabulary loaded. Please select decks first."
            )

        result = await llm_service.generate_recall_sentences(
            count=request.count,
            learned_vocab=learned,
            due_vocab=due,
            new_vocab=new,
            topic=request.topic,
            target_word_count=request.target_word_count
        )

        return RecallGenerateResponse(
            sentences=result["sentences"],
            stats=result["stats"]
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate sentences: {e}")


@app.post("/api/recall/generate-passage")
async def generate_recall_passage(request: RecallPassageRequest) -> ProcessedArticle:
    """Generate a passage for extended recall practice, returned as ProcessedArticle for Reader display"""
    try:
        print(f"[Passage] Starting generation with topic={request.topic}, chars={request.target_char_count}")
        learned = vocab_manager.get_words_by_status(VocabStatus.LEARNED)
        due = vocab_manager.get_words_by_status(VocabStatus.DUE)
        new = vocab_manager.get_words_by_status(VocabStatus.NEW)
        print(f"[Passage] Vocab: {len(learned)} learned, {len(due)} due, {len(new)} new")

        if not learned and not due:
            raise HTTPException(
                status_code=400,
                detail="No vocabulary loaded. Please select decks first."
            )

        # Generate the passage with LLM
        print("[Passage] Calling LLM...")
        passage_result = await llm_service.generate_recall_passage(
            learned_vocab=learned,
            due_vocab=due,
            new_vocab=new,
            topic=request.topic,
            target_char_count=request.target_char_count
        )
        print(f"[Passage] LLM returned: {passage_result.keys() if passage_result else 'None'}")

        # Process the Chinese text through ArticleProcessor for word segmentation
        if not article_processor:
            raise HTTPException(status_code=500, detail="Article processor not initialized")

        # Process as Chinese text (no rewriting needed since LLM already used our vocab)
        print("[Passage] Processing article...")
        result = await article_processor.process_article(
            text=passage_result["chinese"],
            rewrite=False,
            source_lang="zh"
        )

        # Set the title from LLM
        result.title = passage_result.get("title", "Practice Passage")

        # Add English translation to each sentence
        # The passage is already one coherent text, but we'll add the full translation
        # to the stats for display purposes
        result.stats["english_translation"] = passage_result.get("english", "")
        result.stats["is_generated_passage"] = True

        print(f"[Passage] Success! Title: {result.title}")
        return result

    except RuntimeError as e:
        print(f"[Passage] RuntimeError: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        print(f"[Passage] Exception: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate passage: {e}")


# Chat operations

@app.post("/api/chat/send")
async def chat_send(request: ChatRequest) -> ChatResponse:
    """Process user message and generate AI response"""
    try:
        if not article_processor:
            raise HTTPException(status_code=500, detail="Article processor not initialized")

        # Get vocabulary lists
        learned = vocab_manager.get_words_by_status(VocabStatus.LEARNED)
        due = vocab_manager.get_words_by_status(VocabStatus.DUE)
        new = vocab_manager.get_words_by_status(VocabStatus.NEW)

        if not learned and not due:
            raise HTTPException(
                status_code=400,
                detail="No vocabulary loaded. Please select decks first."
            )

        # Segment and classify user's message
        user_segments = article_processor.segment_text(request.message)
        user_words = article_processor.classify_segments(user_segments)

        # Generate AI response
        ai_result = await llm_service.generate_chat_response(
            user_message=request.message,
            conversation_history=request.history,
            learned_vocab=learned,
            due_vocab=due,
            new_vocab=new,
            max_new_words=request.max_new_words
        )

        # Segment and classify AI response
        ai_segments = article_processor.segment_text(ai_result["chinese"])
        ai_words = article_processor.classify_segments(ai_segments)

        return ChatResponse(
            user_message=ChatMessageModel(
                role="user",
                text=request.message,
                words=user_words,
                translation=None
            ),
            ai_message=ChatMessageModel(
                role="assistant",
                text=ai_result["chinese"],
                words=ai_words,
                translation=ai_result["translation"]
            )
        )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {e}")


# Review operations

@app.post("/api/review")
async def submit_review(review: ReviewRequest):
    """Submit a review for a card"""
    if review.ease < 1 or review.ease > 4:
        raise HTTPException(status_code=400, detail="Ease must be between 1 and 4")

    try:
        print(f"Submitting review: card_id={review.card_id}, ease={review.ease}")

        # Get card info before review
        card_info_before = await anki_client.get_cards_info([review.card_id])
        print(f"Card before: queue={card_info_before[0].get('queue')}, due={card_info_before[0].get('due')}")

        # Try GUI-based review first (more reliable for syncing)
        gui_success = False
        try:
            gui_success = await anki_client.gui_review_card(review.card_id, review.ease)
            print(f"GUI review result: {gui_success}")
        except Exception as gui_err:
            print(f"GUI review failed, falling back to answerCards: {gui_err}")

        # Fall back to answerCards if GUI method fails
        if not gui_success:
            results = await anki_client.answer_cards([
                {"cardId": review.card_id, "ease": review.ease}
            ])
            print(f"AnkiConnect answerCards result: {results}")
            success = results[0] if results else False
        else:
            success = True

        # Get card info after review
        card_info_after = await anki_client.get_cards_info([review.card_id])
        print(f"Card after: queue={card_info_after[0].get('queue')}, due={card_info_after[0].get('due')}")

        # Refresh the card status in our vocab cache
        await vocab_manager.refresh_card_status(review.card_id)

        # Auto-sync to AnkiWeb so changes propagate to other devices
        try:
            await anki_client.sync()
            print("Auto-synced to AnkiWeb")
        except Exception as sync_err:
            print(f"Auto-sync failed (non-critical): {sync_err}")

        return {"success": success, "method": "gui" if gui_success else "answerCards"}
    except Exception as e:
        print(f"Review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sync operations

@app.post("/api/sync")
async def trigger_sync():
    """Trigger sync with AnkiWeb"""
    try:
        await anki_client.sync()
        return {"status": "sync_complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# News operations

@app.get("/api/news/headlines")
async def get_news_headlines():
    """Fetch BBC news headlines and translate using user's vocabulary"""
    import httpx
    import xml.etree.ElementTree as ET

    try:
        # Fetch BBC World News RSS feed
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                timeout=15.0
            )
            response.raise_for_status()

        # Parse RSS feed
        root = ET.fromstring(response.text)
        headlines = []

        for item in root.findall(".//item")[:10]:  # Get top 10 headlines
            title = item.find("title")
            description = item.find("description")
            link = item.find("link")
            pub_date = item.find("pubDate")

            if title is not None:
                headlines.append({
                    "title": title.text,
                    "description": description.text if description is not None else "",
                    "link": link.text if link is not None else "",
                    "pubDate": pub_date.text if pub_date is not None else ""
                })

        if not headlines:
            raise HTTPException(status_code=500, detail="No headlines found in feed")

        # Get vocabulary for translation
        learned = vocab_manager.get_words_by_status(VocabStatus.LEARNED)
        due = vocab_manager.get_words_by_status(VocabStatus.DUE)
        new = vocab_manager.get_words_by_status(VocabStatus.NEW)

        if not learned and not due:
            raise HTTPException(
                status_code=400,
                detail="No vocabulary loaded. Please select decks first."
            )

        # Translate headlines using LLM with vocabulary constraints
        translated = await llm_service.translate_headlines(
            headlines=headlines,
            learned_vocab=learned,
            due_vocab=due,
            new_vocab=new
        )

        return {
            "headlines": translated,
            "source": "BBC World News",
            "fetch_time": response.headers.get("date", "")
        }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch news: {e}")
    except ET.ParseError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse news feed: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"News error: {e}")


@app.post("/api/news/process-headline")
async def process_news_headline(headline_text: str):
    """Process a single headline into a full article with word breakdown"""
    if not article_processor:
        raise HTTPException(status_code=500, detail="Article processor not initialized")

    try:
        result = await article_processor.process_article(
            text=headline_text,
            rewrite=False,
            source_lang="zh"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")


# New Words operations

from pydantic import BaseModel

class NewWordRequest(BaseModel):
    word: str | None = None  # Specific word to review
    mode: str = "new"  # "new" = next new word, "learning" = learning/due cards

class NewWordContentResponse(BaseModel):
    word: dict  # The target word info
    example_sentences: list[dict]  # 2 example sentences with context
    recall_sentences: list[dict]   # 2 recall sentences
    card_id: int | None = None     # Card ID for review submission


@app.post("/api/new-word/introduce")
async def introduce_new_word(request: NewWordRequest) -> NewWordContentResponse:
    """Get content for introducing a new word to the learner"""
    try:
        # Get vocabulary
        learned = vocab_manager.get_words_by_status(VocabStatus.LEARNED)
        due = vocab_manager.get_words_by_status(VocabStatus.DUE)
        new_words = vocab_manager.get_words_by_status(VocabStatus.NEW)

        if not learned and not due:
            raise HTTPException(
                status_code=400,
                detail="No vocabulary loaded. Please select decks first."
            )

        # Find the target word
        target_word = None
        card_id = None

        if request.word:
            # Look up specific word (could be from any status)
            all_vocab = vocab_manager.get_vocab_list()
            for w in all_vocab:
                if w.hanzi == request.word:
                    target_word = w
                    card_id = w.card_id
                    break

            if not target_word:
                # Word not in vocab - create a basic word object (use already-imported Word)
                target_word = Word(
                    hanzi=request.word,
                    pinyin="",
                    definition="(lookup requested)",
                    status=VocabStatus.UNKNOWN,
                    card_id=None
                )
        elif request.mode == "learning":
            # Get learning cards first (queue 1 or 3), then fall back to due review cards
            learning_words = vocab_manager.get_learning_words()
            if learning_words:
                target_word = learning_words[0]
                card_id = target_word.card_id
            else:
                # Fall back to due review cards
                due_review_words = vocab_manager.get_due_review_words()
                if due_review_words:
                    target_word = due_review_words[0]
                    card_id = target_word.card_id
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="No challenging words available. All cards are up to date!"
                    )
        else:
            # Get next new word from queue (mode == "new")
            if not new_words:
                raise HTTPException(
                    status_code=404,
                    detail="No new words available. All words have been introduced!"
                )
            target_word = new_words[0]
            card_id = target_word.card_id

        # Generate learning content
        content = await llm_service.generate_new_word_content(
            target_word=target_word,
            learned_vocab=learned,
            due_vocab=due
        )

        return NewWordContentResponse(
            word=target_word.model_dump(),
            example_sentences=content.get("example_sentences", []),
            recall_sentences=content.get("recall_sentences", []),
            card_id=card_id
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to introduce word: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
