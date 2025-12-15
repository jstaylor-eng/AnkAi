from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()  # Load .env before other imports

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import anki_client
from models import (
    DeckSelection, ArticleRequest, ReviewRequest,
    ProcessedArticle, Word, VocabStatus
)
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
    """Check if API and Anki are available"""
    try:
        version = await anki_client.version()
        return {"status": "ok", "anki_connect_version": version}
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
        # Reinitialize article processor with updated vocab
        global article_processor
        article_processor = ArticleProcessor(vocab_manager)
        return {
            "selected": selection.deck_names,
            "stats": stats
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


@app.get("/api/word/{hanzi}")
async def get_word(hanzi: str):
    """Get info for a specific word"""
    word = vocab_manager.classify_word(hanzi)
    return word.model_dump()


# Article processing

@app.post("/api/article/process")
async def process_article(request: ArticleRequest) -> ProcessedArticle:
    """Process an article and annotate with vocabulary info"""
    if not article_processor:
        raise HTTPException(status_code=500, detail="Article processor not initialized")

    if not request.url and not request.text:
        raise HTTPException(status_code=400, detail="Either url or text must be provided")

    try:
        result = await article_processor.process_article(
            text=request.text,
            url=request.url,
            rewrite=request.rewrite,
            max_new_words=request.max_new_words,
            source_lang=request.source_lang
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Review operations

@app.post("/api/review")
async def submit_review(review: ReviewRequest):
    """Submit a review for a card"""
    if review.ease < 1 or review.ease > 4:
        raise HTTPException(status_code=400, detail="Ease must be between 1 and 4")

    try:
        results = await anki_client.answer_cards([
            {"cardId": review.card_id, "ease": review.ease}
        ])
        # Refresh the card status in our vocab cache
        await vocab_manager.refresh_card_status(review.card_id)
        return {"success": results[0] if results else False}
    except Exception as e:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
