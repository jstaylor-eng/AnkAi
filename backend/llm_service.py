import os
import json
import httpx
from models import Word, Sentence, VocabStatus

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # "anthropic", "groq", "ollama", or "auto"


class LLMService:
    """Handles LLM-based article rewriting and translation"""

    def __init__(self):
        self.provider = self._detect_provider()
        self.anthropic_client = None

        if self.provider == "anthropic":
            from anthropic import Anthropic
            self.anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
            print(f"LLM Provider: Anthropic")
        elif self.provider == "groq":
            print(f"LLM Provider: Groq ({GROQ_MODEL})")
        elif self.provider == "ollama":
            print(f"LLM Provider: Ollama ({OLLAMA_MODEL})")
        else:
            print("LLM Provider: None (rewriting disabled)")

    def _detect_provider(self) -> str | None:
        """Detect which LLM provider to use"""
        if LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
            return "anthropic"
        elif LLM_PROVIDER == "groq" and GROQ_API_KEY:
            return "groq"
        elif LLM_PROVIDER == "ollama":
            return "ollama"
        elif LLM_PROVIDER == "auto":
            # Prefer Groq (free), then Anthropic, then Ollama
            if GROQ_API_KEY:
                return "groq"
            if ANTHROPIC_API_KEY:
                return "anthropic"
            # Check if Ollama is running
            try:
                response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
                if response.status_code == 200:
                    return "ollama"
            except:
                pass
        return None

    def is_available(self) -> bool:
        return self.provider is not None

    async def _call_ollama(self, prompt: str, max_tokens: int = 4096) -> str:
        """Call Ollama API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                    }
                },
                timeout=300.0  # 5 minutes for large vocab prompts
            )
            response.raise_for_status()
            return response.json()["response"]

    async def _call_groq(self, prompt: str, max_tokens: int = 4096) -> str:
        """Call Groq API (free, fast inference)"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
                timeout=60.0
            )
            if response.status_code != 200:
                print(f"Groq API error: {response.status_code} - {response.text}")
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def _call_anthropic(self, prompt: str, max_tokens: int = 4096) -> str:
        """Call Anthropic API"""
        response = self.anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    async def _call_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        """Call the configured LLM provider"""
        if self.provider == "anthropic":
            return await self._call_anthropic(prompt, max_tokens)
        elif self.provider == "groq":
            return await self._call_groq(prompt, max_tokens)
        elif self.provider == "ollama":
            return await self._call_ollama(prompt, max_tokens)
        else:
            raise RuntimeError("No LLM provider available")

    def _parse_json_response(self, content: str) -> any:
        """Parse JSON from LLM response, handling markdown code blocks and extra text"""
        content = content.strip()
        # Remove markdown code blocks if present
        if "```" in content:
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("[") or part.startswith("{"):
                    content = part
                    break

        # Find the first JSON array or object
        if not content.startswith("[") and not content.startswith("{"):
            bracket_pos = content.find("[")
            brace_pos = content.find("{")
            if bracket_pos >= 0 and (brace_pos < 0 or bracket_pos < brace_pos):
                content = content[bracket_pos:]
            elif brace_pos >= 0:
                content = content[brace_pos:]

        # Try to parse, handling extra data after JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            if "Extra data" in str(e):
                # Find the matching closing bracket/brace
                if content.startswith("["):
                    end_pos = self._find_json_end(content, "[", "]")
                else:
                    end_pos = self._find_json_end(content, "{", "}")
                if end_pos > 0:
                    return json.loads(content[:end_pos])
            raise

    def _find_json_end(self, content: str, open_char: str, close_char: str) -> int:
        """Find the position of the matching closing bracket/brace"""
        depth = 0
        in_string = False
        escape = False
        for i, char in enumerate(content):
            if escape:
                escape = False
                continue
            if char == '\\' and in_string:
                escape = True
                continue
            if char == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
                if depth == 0:
                    return i + 1
        return -1

    async def rewrite_article(
        self,
        sentences: list[Sentence],
        learned_vocab: list[str],
        due_vocab: list[Word],
        new_vocab: list[Word],
        max_new_words: int = 3
    ) -> list[Sentence]:
        """
        Rewrite sentences using only known vocabulary.
        Introduces due/new words naturally with context.
        """
        if not self.is_available():
            return sentences

        # Prepare vocabulary lists for the prompt
        learned_list = ", ".join(learned_vocab[:500])  # Limit size
        due_list = ", ".join([w.hanzi for w in due_vocab[:20]])
        # NOTE: New words temporarily disabled - will be introduced via dedicated New Words feature
        # new_list = ", ".join([w.hanzi for w in new_vocab[:max_new_words]])

        # Combine original sentences
        original_text = "\n".join([s.original for s in sentences])

        prompt = f"""You are a Chinese language tutor helping a student read an article.

TASK: Rewrite the following Chinese text so the student can understand it.

RULES:
1. Use ONLY words from the LEARNED VOCABULARY list for general text
2. You MUST naturally include these REVIEW WORDS (the student has seen these before): {due_list}
3. For concepts requiring unknown vocabulary, paraphrase using learned words
4. Keep the core meaning and information of the original
5. Proper nouns (names, places) may be kept with context clues
6. Each sentence should be natural and grammatically correct

LEARNED VOCABULARY (use freely):
{learned_list}

REVIEW WORDS (must include):
{due_list}

ORIGINAL TEXT:
{original_text}

Respond with a JSON array where each element has:
- "original": the original sentence
- "simplified": your rewritten version
- "translation": English translation of your rewritten version

Only output the JSON array, no other text."""

        try:
            content = await self._call_llm(prompt)
            result = self._parse_json_response(content)

            # Update sentences with rewritten versions
            rewritten_sentences = []
            for i, sentence in enumerate(sentences):
                if i < len(result):
                    sentence.simplified = result[i].get("simplified", sentence.original)
                    sentence.translation = result[i].get("translation", "")
                rewritten_sentences.append(sentence)

            return rewritten_sentences

        except Exception as e:
            print(f"LLM rewrite error: {e}")
            return sentences

    async def translate_sentence(self, sentence: str) -> str:
        """Translate a single Chinese sentence to English"""
        if not self.is_available():
            return ""

        prompt = f"Translate this Chinese sentence to English. Only output the translation, nothing else.\n\n{sentence}"

        try:
            return (await self._call_llm(prompt, max_tokens=256)).strip()
        except Exception as e:
            print(f"Translation error: {e}")
            return ""

    async def translate_english_to_chinese(
        self,
        text: str,
        learned_vocab: list[str],
        due_vocab: list["Word"],
        new_vocab: list["Word"],
        max_new_words: int = 3
    ) -> list[dict]:
        """
        Translate English text to Chinese using only known vocabulary.
        Returns list of {chinese, pinyin, english} sentences.
        """
        if not self.is_available():
            return []

        # Split text into sentences first
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text[:10000])
        sentences = [s.strip() for s in sentences if s.strip() and len(s) > 10][:25]

        if not sentences:
            print("No sentences found to translate")
            return []

        # Full vocabulary as a dictionary reference
        learned_list = ", ".join(learned_vocab)
        # All due words - model chooses which fit naturally
        due_list = ", ".join([w.hanzi for w in due_vocab])

        sentences_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(sentences)])

        # Basic vocab the LLM can always use
        basic_vocab = "一二三四五六七八九十百千万, 我你他她它我们你们他们, 的地得了着过吗呢吧, 是有在要会能可以想去来, 和但因为所以如果, 好大小多少, 年月日天时分秒点, 星期一/二/三/四/五/六/天, 一月到十二月, 个只条张本件, 上下左右前后里外中, 不没很太最更都也还就, 这那什么谁哪怎么为什么"

        prompt = f"""You are helping a Chinese learner read content from their native language or Chinese beyond their level. Translate to Chinese using ONLY their known vocabulary.

CRITICAL: The student can ONLY read words from these lists. Using other words means they cannot understand.

BASIC VOCABULARY (always available - numbers, pronouns, particles, etc.):
{basic_vocab}

KNOWN VOCABULARY (the student knows these - use freely):
{learned_list}

REVIEW WORDS (student has seen before - TRY to include these wherever possible):
{due_list}

SENTENCES TO TRANSLATE:
{sentences_text}

STRICT RULES:
1. Use ONLY words from BASIC, KNOWN, and REVIEW vocabulary lists
2. If a concept cannot be expressed with known words, rephrase it using known words
3. PRIORITIZE including REVIEW WORDS - rephrase or add context to fit them in naturally
4. Proper nouns (names, places) are OK to keep
5. Short, simple sentences are better than complex ones with unknown words
6. Numbers, dates, times should use the basic vocabulary
7. PRESERVE the person (first/third) and perspective of the original - if someone says "I feel...", translate as 我觉得, not 她觉得

Return ONLY a JSON array:
[{{"english": "original", "chinese": "translation", "pinyin": "pin yin"}}]"""

        try:
            print(f"Sending {len(sentences)} sentences to LLM with {len(learned_vocab)} vocab words...")
            content = await self._call_llm(prompt)
            print(f"LLM raw response (first 500 chars): {content[:500]}")
            result = self._parse_json_response(content)
            print(f"Parsed {len(result)} sentences")

            # Replace LLM's "english" with actual original sentences
            # (LLM often paraphrases to match the simplified Chinese)
            for i, item in enumerate(result):
                if i < len(sentences):
                    item["english"] = sentences[i]

            # Second pass: get back-translations
            if result:
                chinese_sentences = [r.get("chinese", "") for r in result]
                back_translations = await self._get_back_translations(chinese_sentences)
                for i, item in enumerate(result):
                    if i < len(back_translations):
                        item["back_translation"] = back_translations[i]

            return result
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Raw content: {content[:1000]}")
            return self._fallback_parse(content, sentences)
        except Exception as e:
            print(f"English to Chinese translation error: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _get_back_translations(self, chinese_sentences: list[str]) -> list[str]:
        """Translate Chinese sentences back to English"""
        if not chinese_sentences:
            return []

        numbered = "\n".join([f"{i+1}. {s}" for i, s in enumerate(chinese_sentences)])
        prompt = f"""Translate these Chinese sentences to English. Give literal translations showing exactly what each sentence means.

{numbered}

Return a JSON array of English translations in the same order:
["translation 1", "translation 2", ...]"""

        try:
            print(f"Getting back-translations for {len(chinese_sentences)} sentences...")
            content = await self._call_llm(prompt, max_tokens=1024)
            print(f"Back-translation response: {content[:300]}")
            result = self._parse_json_response(content)
            if isinstance(result, list):
                print(f"Got {len(result)} back-translations")
                return [str(r) for r in result]
        except Exception as e:
            print(f"Back-translation error: {e}")
            import traceback
            traceback.print_exc()

        return [""] * len(chinese_sentences)

    def _fallback_parse(self, content: str, original_sentences: list[str]) -> list[dict]:
        """Try to salvage partial results from malformed LLM output"""
        results = []
        try:
            # Look for individual JSON objects
            import re
            pattern = r'\{[^}]*"chinese"\s*:\s*"([^"]+)"[^}]*\}'
            matches = re.findall(pattern, content)
            for i, chinese in enumerate(matches):
                if i < len(original_sentences):
                    results.append({
                        "english": original_sentences[i],
                        "chinese": chinese,
                        "pinyin": ""
                    })
        except:
            pass
        print(f"Fallback parse found {len(results)} sentences")
        return results

    async def explain_word(self, word: str, context: str = "") -> dict:
        """Get detailed explanation of a word, optionally in context"""
        if not self.is_available():
            return {"explanation": "", "examples": []}

        prompt = f"""Explain this Chinese word for a learner:

Word: {word}
{"Context: " + context if context else ""}

Provide:
1. Brief explanation (1-2 sentences)
2. 2 simple example sentences using this word

Respond in JSON format:
{{"explanation": "...", "examples": ["...", "..."]}}"""

        try:
            content = await self._call_llm(prompt, max_tokens=512)
            return self._parse_json_response(content)
        except Exception as e:
            print(f"Word explanation error: {e}")
            return {"explanation": "", "examples": []}

    async def generate_recall_sentences(
        self,
        count: int,
        learned_vocab: list["Word"],
        due_vocab: list["Word"],
        new_vocab: list["Word"],
        topic: str | None = None,
        target_word_count: int | None = None
    ) -> dict:
        """
        Generate sentences for recall practice using the user's vocabulary.
        Returns sentences with English, Chinese, pinyin, and word-order English.

        Args:
            topic: Optional topic/notes for focused practice
            target_word_count: Optional target Chinese character count per sentence (+/- 15%)
        """
        import random

        if not self.is_available():
            raise RuntimeError("LLM not available")

        # Shuffle and sample vocabulary for variety
        learned_shuffled = learned_vocab.copy()
        random.shuffle(learned_shuffled)
        due_shuffled = due_vocab.copy()
        random.shuffle(due_shuffled)
        # NOTE: New words temporarily disabled - will be introduced via dedicated New Words feature
        # new_shuffled = new_vocab.copy()
        # random.shuffle(new_shuffled)

        # Take a diverse sample of learned vocab
        learned_list = ", ".join([w.hanzi for w in learned_shuffled[:300]])
        # Prioritize ALL due words - these are the ones to practice
        due_list = ", ".join([w.hanzi for w in due_shuffled[:50]])
        # new_list = ", ".join([w.hanzi for w in new_shuffled[:10]])

        # Basic vocab always available
        basic_vocab = "一二三四五六七八九十百千万, 我你他她它我们你们他们, 的地得了着过吗呢吧, 是有在要会能可以想去来, 和但因为所以如果, 好大小多少, 年月日天时分秒点, 上下左右前后里外中, 不没很太最更都也还就, 这那什么谁哪怎么为什么, 吃喝做说看听读写, 家人朋友老师学生"

        # Determine sentence length guidance
        if target_word_count:
            min_chars = int(target_word_count * 0.85)
            max_chars = int(target_word_count * 1.15)
            length_guidance = f"Each sentence should be {min_chars}-{max_chars} Chinese characters long (targeting ~{target_word_count} characters)"
        else:
            length_guidance = "Each sentence should be 10-20 Chinese characters long"

        # Topic guidance with variety
        if topic:
            topic_guidance = f"TOPIC FOCUS: All sentences should relate to: {topic}"
        else:
            # Randomize default topics for variety
            all_topics = ["daily life", "food and cooking", "travel", "hobbies", "weather",
                         "family", "work", "study", "shopping", "health", "entertainment",
                         "sports", "technology", "nature", "emotions", "time and schedules"]
            selected_topics = random.sample(all_topics, min(5, len(all_topics)))
            topic_guidance = f"Topics (use variety): {', '.join(selected_topics)}"

        prompt = f"""Generate {count} DIVERSE Chinese sentences for language practice. Each sentence should be unique and different from the others.

CRITICAL REQUIREMENTS:
1. VARIETY: Each sentence must use different vocabulary and sentence structures. NO repetitive patterns!
2. DUE WORDS: You MUST include words from the REVIEW WORDS list - these are the priority words the student needs to practice. Try to use DIFFERENT review words in each sentence.
3. Use vocabulary from BASIC + LEARNED lists for other words
4. {length_guidance}
5. {topic_guidance}

VOCABULARY LISTS:

BASIC VOCABULARY (grammar words, always available):
{basic_vocab}

LEARNED VOCABULARY (student knows these - use variety from this list):
{learned_list}

★ REVIEW WORDS - PRIORITY ★ (MUST include these - spread across sentences):
{due_list}

IMPORTANT:
- Use DIFFERENT review words in each sentence
- Vary sentence structures (questions, statements, commands, etc.)
- Vary topics across sentences
- Avoid repeating the same vocabulary patterns

For each sentence, provide:
- "english": Natural English sentence
- "chinese": Chinese translation using allowed vocabulary
- "pinyin": Pinyin with tone marks (e.g., "Wǒ xiǎng chī fàn")
- "word_order_english": Word-by-word English gloss in Chinese word order

Return ONLY a JSON array:
[{{"english": "...", "chinese": "...", "pinyin": "...", "word_order_english": "..."}}]"""

        try:
            print(f"Generating {count} recall sentences with {len(learned_vocab)} learned words, {len(due_vocab)} due words...")
            content = await self._call_llm(prompt, max_tokens=2048)
            result = self._parse_json_response(content)

            if not isinstance(result, list):
                raise ValueError("Expected JSON array")

            # Validate and clean results
            sentences = []
            for item in result[:count]:
                sentences.append({
                    "english": item.get("english", ""),
                    "chinese": item.get("chinese", ""),
                    "pinyin": item.get("pinyin", ""),
                    "word_order_english": item.get("word_order_english", "")
                })

            print(f"Generated {len(sentences)} recall sentences")
            return {
                "sentences": sentences,
                "stats": {
                    "total_generated": len(sentences),
                    "due_words_available": len(due_vocab),
                    "new_words_available": len(new_vocab)
                }
            }

        except Exception as e:
            print(f"Recall sentence generation error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate sentences: {e}")


    async def generate_chat_response(
        self,
        user_message: str,
        conversation_history: list[dict],
        learned_vocab: list["Word"],
        due_vocab: list["Word"],
        new_vocab: list["Word"],
        max_new_words: int = 2
    ) -> dict:
        """
        Generate conversational response using user's vocabulary.
        Returns: { chinese, translation }
        """
        if not self.is_available():
            raise RuntimeError("LLM not available")

        # Prepare vocabulary lists
        learned_list = ", ".join([w.hanzi for w in learned_vocab[:400]])
        due_list = ", ".join([w.hanzi for w in due_vocab[:30]])
        # NOTE: New words temporarily disabled - will be introduced via dedicated New Words feature
        # new_list = ", ".join([w.hanzi for w in new_vocab[:max_new_words * 2]])

        # Basic vocab always available
        basic_vocab = "一二三四五六七八九十百千万, 我你他她它我们你们他们, 的地得了着过吗呢吧, 是有在要会能可以想去来, 和但因为所以如果, 好大小多少, 年月日天时分秒点, 上下左右前后里外中, 不没很太最更都也还就, 这那什么谁哪怎么为什么, 吃喝做说看听读写, 家人朋友老师学生, 知道觉得喜欢希望"

        # Format conversation history
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                role_label = "User" if msg.get("role") == "user" else "Assistant"
                history_text += f"{role_label}: {msg.get('text', '')}\n"

        prompt = f"""You are a friendly Chinese language tutor having a conversation with a learner.

VOCABULARY RULES (STRICT - FOLLOW EXACTLY):
1. Use ONLY words from BASIC VOCABULARY and LEARNED VOCABULARY for all grammar and common words
2. TRY to naturally include 1-2 REVIEW WORDS in your response - these are words the student needs to practice
3. Proper nouns (names, places, brands) may be used when the conversation requires them
4. Keep responses conversational and natural (1-3 sentences)
5. Respond in a helpful, encouraging way

BASIC VOCABULARY (always safe to use):
{basic_vocab}

LEARNED VOCABULARY (student knows these - use freely):
{learned_list}

REVIEW WORDS (prioritize including these naturally):
{due_list}

CONVERSATION HISTORY:
{history_text if history_text else "(This is the start of the conversation)"}

USER MESSAGE: {user_message}

Respond naturally as a tutor would. Return ONLY a JSON object:
{{"chinese": "你的中文回复", "translation": "English translation of your response"}}"""

        try:
            print(f"Generating chat response with {len(learned_vocab)} learned words, {len(due_vocab)} due words...")
            content = await self._call_llm(prompt, max_tokens=512)
            result = self._parse_json_response(content)

            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")

            chinese = result.get("chinese", "")
            translation = result.get("translation", "")

            print(f"Generated chat response: {chinese[:50]}...")

            return {
                "chinese": chinese,
                "translation": translation
            }

        except Exception as e:
            print(f"Chat response generation error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate response: {e}")

    async def _fetch_wikipedia_context(self, topic: str) -> str:
        """Fetch relevant context from Wikipedia for the given topic."""
        try:
            # Search Wikipedia for the topic
            search_url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": topic,
                "srlimit": 3,
                "format": "json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, params=search_params, timeout=10.0)
                data = response.json()

                if not data.get("query", {}).get("search"):
                    return ""

                # Get the first result's page content
                page_title = data["query"]["search"][0]["title"]

                # Fetch page extract
                extract_params = {
                    "action": "query",
                    "titles": page_title,
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True,
                    "exsentences": 5,
                    "format": "json"
                }

                response = await client.get(search_url, params=extract_params, timeout=10.0)
                data = response.json()

                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    extract = page_data.get("extract", "")
                    if extract:
                        print(f"[RAG] Retrieved Wikipedia context for '{topic}': {len(extract)} chars")
                        return extract[:1500]  # Limit context size

                return ""
        except Exception as e:
            print(f"[RAG] Wikipedia fetch error: {e}")
            return ""

    async def _web_search_context(self, topic: str) -> str:
        """Fetch relevant context from DuckDuckGo search."""
        try:
            # Use DuckDuckGo instant answer API
            search_url = "https://api.duckduckgo.com/"
            params = {
                "q": topic,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, params=params, timeout=10.0)
                data = response.json()

                # Get abstract text
                abstract = data.get("AbstractText", "")
                if abstract:
                    print(f"[RAG] Retrieved DuckDuckGo context for '{topic}': {len(abstract)} chars")
                    return abstract[:1000]

                # Try related topics
                related = data.get("RelatedTopics", [])
                if related:
                    texts = []
                    for item in related[:3]:
                        if isinstance(item, dict) and "Text" in item:
                            texts.append(item["Text"])
                    if texts:
                        result = " ".join(texts)[:1000]
                        print(f"[RAG] Retrieved DuckDuckGo related topics: {len(result)} chars")
                        return result

                return ""
        except Exception as e:
            print(f"[RAG] DuckDuckGo fetch error: {e}")
            return ""

    async def generate_recall_passage(
        self,
        learned_vocab: list["Word"],
        due_vocab: list["Word"],
        new_vocab: list["Word"],
        topic: str | None = None,
        target_char_count: int = 50
    ) -> dict:
        """
        Generate a Chinese passage for extended recall practice.
        Uses RAG to fetch real information about the topic from Wikipedia/web.
        Returns passage text with English translation for display in Reader.

        Args:
            topic: Optional topic/notes for focused practice
            target_char_count: Target total Chinese characters for the passage
        """
        import random

        if not self.is_available():
            raise RuntimeError("LLM not available")

        # Shuffle vocabulary for variety
        learned_shuffled = learned_vocab.copy()
        random.shuffle(learned_shuffled)
        due_shuffled = due_vocab.copy()
        random.shuffle(due_shuffled)

        # Prepare vocabulary lists
        learned_list = ", ".join([w.hanzi for w in learned_shuffled[:400]])
        due_list = ", ".join([w.hanzi for w in due_shuffled[:40]])
        # NOTE: New words temporarily disabled - will be introduced via dedicated New Words feature
        # new_list = ", ".join([w.hanzi for w in new_vocab[:8]])

        # Basic vocab always available
        basic_vocab = "一二三四五六七八九十百千万, 我你他她它我们你们他们, 的地得了着过吗呢吧, 是有在要会能可以想去来, 和但因为所以如果, 好大小多少, 年月日天时分秒点, 上下左右前后里外中, 不没很太最更都也还就, 这那什么谁哪怎么为什么, 吃喝做说看听读写, 家人朋友老师学生, 知道觉得喜欢希望"

        # Calculate target range
        min_chars = int(target_char_count * 0.85)
        max_chars = int(target_char_count * 1.15)

        # RAG: Fetch context from Wikipedia/web if topic provided
        rag_context = ""
        if topic:
            print(f"[RAG] Fetching context for topic: {topic}")
            # Try Wikipedia first, then DuckDuckGo
            rag_context = await self._fetch_wikipedia_context(topic)
            if not rag_context:
                rag_context = await self._web_search_context(topic)

            if rag_context:
                rag_context = f"""
REFERENCE INFORMATION (use this to create factual, interesting content):
{rag_context}

Based on this information, create an engaging Chinese passage about {topic}."""
            else:
                print(f"[RAG] No context found, generating without RAG")

        # Content styles for variety
        content_styles = [
            "a first-person narrative/story",
            "a descriptive scene with sensory details",
            "a mini dialogue between people",
            "an opinion piece with reasons",
            "a how-to or process description",
            "a comparison between two things",
            "a personal memory or experience",
            "a factual description with specific details"
        ]
        chosen_style = random.choice(content_styles)

        # Topic guidance
        if topic:
            if rag_context:
                topic_guidance = f"TOPIC: {topic}\n{rag_context}"
            else:
                topic_guidance = f"TOPIC: {topic}"
        else:
            # Random specific scenarios when no topic provided
            scenarios = [
                "buying coffee at a new cafe and the barista recommends something",
                "waiting for a bus in the rain and meeting someone interesting",
                "cooking a dish for the first time and what happened",
                "finding something unexpected while cleaning",
                "a phone call that changed plans for the day",
                "trying a new restaurant and the surprising menu",
                "getting lost and asking for directions",
                "a birthday gift that was perfect (or terrible)",
                "the first day at a new place (job, school, city)",
                "watching the sunrise or sunset somewhere special"
            ]
            topic_guidance = f"SCENARIO: {random.choice(scenarios)}"

        prompt = f"""Write a short Chinese passage as {chosen_style}.

{topic_guidance}

LENGTH: {min_chars}-{max_chars} Chinese characters.

CRITICAL - AVOID THESE PATTERNS:
- NO generic statements like "X is interesting/important"
- NO "students/people like to discuss X"
- NO "X is very popular" without specific details
- NO vague summaries - be SPECIFIC and CONCRETE

INSTEAD:
- Include specific details, names, numbers, or sensory descriptions
- Show don't tell - describe actions, not just opinions
- If it's a story, have something HAPPEN
- If it's about a topic, include a specific fact or example

VOCABULARY CONSTRAINTS:
- Use BASIC + LEARNED vocabulary for grammar and common words
- Include REVIEW WORDS naturally (these are priority)
- Proper nouns (names, places) are allowed freely

BASIC VOCABULARY:
{basic_vocab}

LEARNED VOCABULARY:
{learned_list}

★ REVIEW WORDS (include these):
{due_list}

Return ONLY JSON:
{{
  "chinese": "The passage",
  "english": "Translation",
  "title": "2-4 word title"
}}"""

        try:
            print(f"Generating recall passage (~{target_char_count} chars) with {len(learned_vocab)} learned words...")
            content = await self._call_llm(prompt, max_tokens=1024)
            result = self._parse_json_response(content)

            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")

            chinese = result.get("chinese", "")
            english = result.get("english", "")
            title = result.get("title", "Practice Passage")

            print(f"Generated passage: {len(chinese)} Chinese chars, title: {title}")

            return {
                "chinese": chinese,
                "english": english,
                "title": title
            }

        except Exception as e:
            print(f"Recall passage generation error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate passage: {e}")

    async def translate_headlines(
        self,
        headlines: list[dict],
        learned_vocab: list["Word"],
        due_vocab: list["Word"],
        new_vocab: list["Word"]
    ) -> list[dict]:
        """
        Translate news headlines to Chinese using the user's vocabulary.
        Returns headlines with Chinese translations and pinyin.
        """
        if not self.is_available():
            raise RuntimeError("LLM not available")

        # Prepare vocabulary lists
        learned_list = ", ".join([w.hanzi for w in learned_vocab[:500]])
        due_list = ", ".join([w.hanzi for w in due_vocab[:50]])

        # Basic vocab always available
        basic_vocab = "一二三四五六七八九十百千万亿, 我你他她它我们你们他们, 的地得了着过吗呢吧, 是有在要会能可以想去来, 和但因为所以如果, 好大小多少, 年月日天时分秒点, 上下左右前后里外中, 不没很太最更都也还就, 这那什么谁哪怎么为什么, 说看听读写做想知道, 人国家世界政府"

        # Format headlines for translation
        headlines_text = "\n".join([
            f"{i+1}. {h['title']}"
            for i, h in enumerate(headlines)
        ])

        prompt = f"""Translate these news headlines to Chinese using the student's vocabulary.

HEADLINES:
{headlines_text}

VOCABULARY RULES:
1. Use BASIC + LEARNED vocabulary for most words
2. Include REVIEW WORDS where they fit naturally
3. Proper nouns (names, places, countries, organizations) keep their standard Chinese names
4. Keep headlines concise and news-like
5. Use news vocabulary style (shorter, punchy sentences)

BASIC VOCABULARY:
{basic_vocab}

LEARNED VOCABULARY:
{learned_list}

REVIEW WORDS (prioritize):
{due_list}

For each headline, provide:
- "original": the English headline
- "chinese": Chinese translation
- "pinyin": pinyin with tones

Return ONLY a JSON array:
[{{"original": "...", "chinese": "...", "pinyin": "..."}}]"""

        try:
            print(f"Translating {len(headlines)} headlines with {len(learned_vocab)} learned words...")
            content = await self._call_llm(prompt, max_tokens=2048)
            result = self._parse_json_response(content)

            if not isinstance(result, list):
                raise ValueError("Expected JSON array")

            # Merge translations with original headline data
            translated = []
            for i, h in enumerate(headlines):
                if i < len(result):
                    translated.append({
                        "original": h["title"],
                        "description": h.get("description", ""),
                        "link": h.get("link", ""),
                        "pubDate": h.get("pubDate", ""),
                        "chinese": result[i].get("chinese", ""),
                        "pinyin": result[i].get("pinyin", "")
                    })

            print(f"Translated {len(translated)} headlines")
            return translated

        except Exception as e:
            print(f"Headline translation error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to translate headlines: {e}")


    async def generate_new_word_content(
        self,
        target_word: "Word",
        learned_vocab: list["Word"],
        due_vocab: list["Word"]
    ) -> dict:
        """
        Generate content for introducing a new word:
        - 2 example sentences showing the word in context (different meanings if applicable)
        - 2 recall sentences (English prompt for Chinese recall)
        All sentences use only known vocabulary + the new word + proper nouns
        """
        if not self.is_available():
            raise RuntimeError("LLM not available")

        # Prepare vocabulary lists
        learned_list = ", ".join([w.hanzi for w in learned_vocab[:400]])
        due_list = ", ".join([w.hanzi for w in due_vocab[:30]])

        # Basic vocab always available
        basic_vocab = "一二三四五六七八九十百千万, 我你他她它我们你们他们, 的地得了着过吗呢吧, 是有在要会能可以想去来, 和但因为所以如果, 好大小多少, 年月日天时分秒点, 上下左右前后里外中, 不没很太最更都也还就, 这那什么谁哪怎么为什么, 吃喝做说看听读写, 家人朋友老师学生, 知道觉得喜欢希望"

        prompt = f"""You are helping a student learn a new Chinese word.

TARGET WORD TO TEACH:
- Chinese: {target_word.hanzi}
- Pinyin: {target_word.pinyin}
- Definition: {target_word.definition}

TASK: Create learning content for this word using ONLY the student's known vocabulary + the target word + proper nouns.

VOCABULARY AVAILABLE:
BASIC (always safe): {basic_vocab}
LEARNED: {learned_list}
REVIEW (include if natural): {due_list}
TARGET WORD: {target_word.hanzi}

Generate:
1. TWO example sentences showing the target word in context
   - If the word has multiple meanings, show different meanings
   - Each sentence should be 8-15 characters
   - Chinese text should highlight how the word is used

2. TWO recall sentences for practice
   - Provide English that the student will translate to Chinese
   - The Chinese translation MUST use the target word
   - Keep sentences simple (8-15 characters in Chinese)

Return ONLY JSON:
{{
  "example_sentences": [
    {{
      "chinese": "...",
      "pinyin": "...",
      "english": "...",
      "word_highlight": "meaning or usage note for this context"
    }},
    {{
      "chinese": "...",
      "pinyin": "...",
      "english": "...",
      "word_highlight": "meaning or usage note for this context"
    }}
  ],
  "recall_sentences": [
    {{
      "english": "...",
      "chinese": "...",
      "pinyin": "..."
    }},
    {{
      "english": "...",
      "chinese": "...",
      "pinyin": "..."
    }}
  ]
}}"""

        try:
            print(f"Generating content for new word: {target_word.hanzi}")
            content = await self._call_llm(prompt, max_tokens=1024)
            result = self._parse_json_response(content)

            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")

            print(f"Generated {len(result.get('example_sentences', []))} examples, {len(result.get('recall_sentences', []))} recall sentences")
            return result

        except Exception as e:
            print(f"New word content generation error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate content: {e}")


# Global instance
llm_service = LLMService()
