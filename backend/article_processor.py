import jieba
import httpx
import re
import unicodedata
from typing import Optional
from models import Word, Sentence, ProcessedArticle, VocabStatus
from vocab_manager import VocabManager
from llm_service import llm_service


def detect_language(text: str) -> str:
    """Detect if text is primarily Chinese or English"""
    chinese_chars = 0
    latin_chars = 0

    for char in text:
        if '\u4e00' <= char <= '\u9fff':  # CJK Unified Ideographs
            chinese_chars += 1
        elif char.isalpha() and unicodedata.name(char, '').startswith('LATIN'):
            latin_chars += 1

    if chinese_chars > latin_chars:
        return "zh"
    return "en"


class ArticleProcessor:
    """Processes articles by segmenting and classifying vocabulary"""

    def __init__(self, vocab_manager: VocabManager):
        self.vocab_manager = vocab_manager
        # Add known vocabulary to jieba's dictionary for better segmentation
        self._update_jieba_dict()

    def _update_jieba_dict(self):
        """Add known vocabulary to jieba for better segmentation"""
        for word in self.vocab_manager.vocab.values():
            if len(word.hanzi) > 1:  # Only add multi-character words
                jieba.add_word(word.hanzi)

    async def fetch_article(self, url: str) -> str:
        """Fetch article text from URL"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, follow_redirects=True, timeout=30.0)
                response.raise_for_status()
                # Basic HTML text extraction
                text = response.text
                # Remove script and style elements
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', text)
                # Clean up whitespace
                text = ' '.join(text.split())
                return text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ValueError(f"This website blocks automated access. Please copy and paste the article text instead.")
            raise

    def segment_text(self, text: str) -> list[str]:
        """Segment Chinese text into words using jieba"""
        segments = list(jieba.cut(text))
        # Post-process to split number+unit compounds (e.g., 十五分钟 -> 十五, 分钟)
        return self._split_numeric_compounds(segments)

    def _split_numeric_compounds(self, segments: list[str]) -> list[str]:
        """Split numeric compounds like 十五分钟 into number + unit"""
        result = []
        # Pattern for Chinese numbers
        num_chars = set("零一二两三四五六七八九十百千万亿")
        # Common units that follow numbers
        units = {"分钟", "小时", "天", "年", "月", "日", "号", "周", "星期", "秒", "点", "块", "元", "个", "位", "岁"}

        for seg in segments:
            if len(seg) > 2:
                # Check if segment is number + unit
                split_pos = 0
                for i, char in enumerate(seg):
                    if char in num_chars:
                        split_pos = i + 1
                    else:
                        break
                # Check if remaining part is a unit
                if split_pos > 0 and split_pos < len(seg):
                    remaining = seg[split_pos:]
                    if remaining in units or remaining in self.vocab_manager.vocab:
                        result.append(seg[:split_pos])
                        result.append(remaining)
                        continue
            result.append(seg)
        return result

    def classify_segments(self, segments: list[str]) -> list[Word]:
        """Classify each segment as known/unknown vocabulary"""
        words = []
        # Punctuation pattern (Chinese and Western)
        punct_pattern = r'^[\s\u3000-\u303F\uFF00-\uFFEF\u0000-\u002F\u003A-\u0040\u005B-\u0060\u007B-\u007F]+$'
        for segment in segments:
            # Skip punctuation and whitespace
            if not segment.strip() or re.match(punct_pattern, segment):
                # Still include for display purposes
                words.append(Word(
                    hanzi=segment,
                    pinyin="",
                    definition="",
                    status=VocabStatus.LEARNED,  # Treat punctuation as "known"
                    card_id=None
                ))
            else:
                word = self.vocab_manager.classify_word(segment)
                words.append(word)
        return words

    def split_sentences(self, text: str) -> list[str]:
        """Split text into sentences"""
        # Split on Chinese and Western punctuation
        sentences = re.split(r'([。！？.!?]+)', text)
        # Rejoin punctuation with preceding sentence
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            if sentence.strip():
                result.append(sentence + punct)
        # Handle last part if no trailing punctuation
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1])
        return result

    async def process_article(
        self,
        text: Optional[str] = None,
        url: Optional[str] = None,
        rewrite: bool = False,
        max_new_words: int = 3,
        source_lang: str = "auto"
    ) -> ProcessedArticle:
        """Process an article and return annotated text"""
        if url and not text:
            text = await self.fetch_article(url)

        if not text:
            raise ValueError("Either text or url must be provided")

        # Detect or use specified language
        if source_lang == "auto":
            source_lang = detect_language(text)
            print(f"Detected language: {source_lang}")

        # If English, translate to Chinese first
        if source_lang == "en":
            if llm_service.is_available():
                print("Processing English article with LLM translation...")
                return await self._process_english_article(text, max_new_words)
            else:
                print("LLM not available - cannot translate English to Chinese")
                # Return error message as a sentence
                from models import Sentence
                return ProcessedArticle(
                    title="",
                    sentences=[Sentence(
                        original="LLM not available",
                        simplified="需要 Ollama 或 Anthropic API 来翻译英文",
                        words=[],
                        translation="Ollama or Anthropic API required to translate English"
                    )],
                    due_words=[],
                    new_words=[],
                    stats={"total_words": 0, "known_words": 0, "comprehension_percent": 0,
                           "due_count": 0, "new_count": 0, "unknown_count": 0, "source_lang": "en"}
                )

        # Update jieba with latest vocab
        self._update_jieba_dict()

        # Split into sentences
        raw_sentences = self.split_sentences(text)

        sentences = []
        all_due_words: dict[str, Word] = {}
        all_new_words: dict[str, Word] = {}
        total_words = 0
        known_words = 0

        for raw_sentence in raw_sentences:
            # Segment the sentence
            segments = self.segment_text(raw_sentence)
            words = self.classify_segments(segments)

            # Track statistics
            for word in words:
                if word.hanzi.strip() and not re.match(r'^[\s\W]+$', word.hanzi):
                    total_words += 1
                    if word.status in (VocabStatus.LEARNED, VocabStatus.DUE):
                        known_words += 1
                    if word.status == VocabStatus.DUE and word.hanzi not in all_due_words:
                        all_due_words[word.hanzi] = word
                    if word.status == VocabStatus.NEW and word.hanzi not in all_new_words:
                        all_new_words[word.hanzi] = word

            sentences.append(Sentence(
                original=raw_sentence,
                simplified=raw_sentence,  # Will be rewritten by LLM later
                words=words,
                translation=""  # Will be filled by LLM later
            ))

        # Calculate comprehension percentage
        comprehension = (known_words / total_words * 100) if total_words > 0 else 0

        # Optionally rewrite using LLM
        if rewrite and llm_service.is_available():
            learned_vocab = [
                w.hanzi for w in self.vocab_manager.get_words_by_status(VocabStatus.LEARNED)
            ]
            sentences = await llm_service.rewrite_article(
                sentences=sentences,
                learned_vocab=learned_vocab,
                due_vocab=list(all_due_words.values()),
                new_vocab=list(all_new_words.values()),
                max_new_words=max_new_words
            )
            # Re-segment the simplified sentences to get word classifications
            for sentence in sentences:
                if sentence.simplified != sentence.original:
                    segments = self.segment_text(sentence.simplified)
                    sentence.words = self.classify_segments(segments)

        return ProcessedArticle(
            title="",  # Could extract from URL/text
            sentences=sentences,
            due_words=list(all_due_words.values()),
            new_words=list(all_new_words.values()),
            stats={
                "total_words": total_words,
                "known_words": known_words,
                "comprehension_percent": round(comprehension, 1),
                "due_count": len(all_due_words),
                "new_count": len(all_new_words),
                "unknown_count": total_words - known_words,
                "source_lang": "zh"
            }
        )

    async def _process_english_article(
        self,
        text: str,
        max_new_words: int = 3
    ) -> ProcessedArticle:
        """Process English text by translating to Chinese at user's vocab level"""
        # Get vocabulary lists
        learned_vocab = [
            w.hanzi for w in self.vocab_manager.get_words_by_status(VocabStatus.LEARNED)
        ]
        due_words = self.vocab_manager.get_words_by_status(VocabStatus.DUE)
        new_words = self.vocab_manager.get_words_by_status(VocabStatus.NEW)

        # Translate English to Chinese
        print(f"Calling LLM to translate {len(text)} chars of English...")
        print(f"Using {len(learned_vocab)} learned words, {len(due_words)} due, {len(new_words)} new")

        translations = await llm_service.translate_english_to_chinese(
            text=text,
            learned_vocab=learned_vocab,
            due_vocab=due_words,
            new_vocab=new_words,
            max_new_words=max_new_words
        )

        print(f"LLM returned {len(translations) if translations else 0} translated sentences")

        if not translations:
            # Fallback: return empty result
            return ProcessedArticle(
                title="",
                sentences=[],
                due_words=[],
                new_words=[],
                stats={
                    "total_words": 0,
                    "known_words": 0,
                    "comprehension_percent": 0,
                    "due_count": 0,
                    "new_count": 0,
                    "unknown_count": 0,
                    "source_lang": "en"
                }
            )

        # Update jieba with vocab
        self._update_jieba_dict()

        sentences = []
        all_due_words: dict[str, Word] = {}
        all_new_words: dict[str, Word] = {}
        total_words = 0
        known_words = 0

        for item in translations:
            chinese = item.get("chinese", "")
            english = item.get("english", "")
            # Use back_translation if available, otherwise fall back to original
            back_translation = item.get("back_translation", english)

            # Segment the Chinese
            segments = self.segment_text(chinese)
            words = self.classify_segments(segments)

            # Track statistics
            for word in words:
                if word.hanzi.strip() and not re.match(r'^[\s\W]+$', word.hanzi):
                    total_words += 1
                    if word.status in (VocabStatus.LEARNED, VocabStatus.DUE):
                        known_words += 1
                    if word.status == VocabStatus.DUE and word.hanzi not in all_due_words:
                        all_due_words[word.hanzi] = word
                    if word.status == VocabStatus.NEW and word.hanzi not in all_new_words:
                        all_new_words[word.hanzi] = word

            sentences.append(Sentence(
                original=english,  # Original English source
                simplified=chinese,  # Simplified Chinese translation
                words=words,
                translation=back_translation  # What the simplified Chinese actually means
            ))

        comprehension = (known_words / total_words * 100) if total_words > 0 else 100

        return ProcessedArticle(
            title="",
            sentences=sentences,
            due_words=list(all_due_words.values()),
            new_words=list(all_new_words.values()),
            stats={
                "total_words": total_words,
                "known_words": known_words,
                "comprehension_percent": round(comprehension, 1),
                "due_count": len(all_due_words),
                "new_count": len(all_new_words),
                "unknown_count": total_words - known_words,
                "source_lang": "en"
            }
        )
