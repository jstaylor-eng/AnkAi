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
        """Parse JSON from LLM response, handling markdown code blocks"""
        content = content.strip()
        # Remove markdown code blocks if present
        if "```" in content:
            # Find content between code blocks
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("[") or part.startswith("{"):
                    content = part
                    break
        return json.loads(content)

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
        new_list = ", ".join([w.hanzi for w in new_vocab[:max_new_words]])

        # Combine original sentences
        original_text = "\n".join([s.original for s in sentences])

        prompt = f"""You are a Chinese language tutor helping a student read an article.

TASK: Rewrite the following Chinese text so the student can understand it.

RULES:
1. Use ONLY words from the LEARNED VOCABULARY list for general text
2. You MUST naturally include these REVIEW WORDS (the student has seen these before): {due_list}
3. You may introduce up to {max_new_words} words from NEW WORDS if they fit naturally: {new_list}
4. For concepts requiring unknown vocabulary, paraphrase using learned words
5. Keep the core meaning and information of the original
6. Proper nouns (names, places) may be kept with context clues
7. Each sentence should be natural and grammatically correct

LEARNED VOCABULARY (use freely):
{learned_list}

REVIEW WORDS (must include):
{due_list}

NEW WORDS (may introduce):
{new_list}

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
        sentences = re.split(r'(?<=[.!?])\s+', text[:3000])
        sentences = [s.strip() for s in sentences if s.strip() and len(s) > 10][:8]

        if not sentences:
            print("No sentences found to translate")
            return []

        # Full vocabulary as a dictionary reference
        learned_list = ", ".join(learned_vocab)
        # All due words - model chooses which fit naturally
        due_list = ", ".join([w.hanzi for w in due_vocab])

        sentences_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(sentences)])

        prompt = f"""Translate English to Chinese for a language learner.

KNOWN VOCABULARY (use words from this list):
{learned_list}

REVIEW WORDS (try to include some of these naturally):
{due_list}

SENTENCES TO TRANSLATE:
{sentences_text}

Rules:
- Use simple, natural Chinese
- Prefer words from the known vocabulary list
- Include review words where they fit naturally
- If needed, use common words not in the list

Return ONLY a JSON array:
[{{"english": "original", "chinese": "translation", "pinyin": "pin yin"}}]"""

        try:
            print(f"Sending {len(sentences)} sentences to LLM with {len(learned_vocab)} vocab words...")
            content = await self._call_llm(prompt)
            print(f"LLM raw response (first 500 chars): {content[:500]}")
            result = self._parse_json_response(content)
            print(f"Parsed {len(result)} sentences")
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


# Global instance
llm_service = LLMService()
