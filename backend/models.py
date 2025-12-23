from enum import Enum
from typing import Optional
from pydantic import BaseModel


class VocabStatus(str, Enum):
    NEW = "new"           # Never seen - target for introduction
    DUE = "due"           # Up for review - primary conversation focus
    LEARNED = "learned"   # Seen before & not due - safe to use freely
    UNKNOWN = "unknown"   # Not in any selected deck - avoid


class Word(BaseModel):
    hanzi: str
    pinyin: str
    definition: str
    status: VocabStatus
    card_id: Optional[int] = None
    deck_name: Optional[str] = None


class Sentence(BaseModel):
    original: str
    simplified: str  # Rewritten version using known vocab
    words: list[Word]
    translation: str


class ProcessedArticle(BaseModel):
    title: str
    sentences: list[Sentence]
    due_words: list[Word]
    new_words: list[Word]
    stats: dict


class ReviewRequest(BaseModel):
    card_id: int
    ease: int  # 1=Again, 2=Hard, 3=Good, 4=Easy


class DeckSelection(BaseModel):
    deck_names: list[str]


class ArticleRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None
    rewrite: bool = False  # Use LLM to rewrite/translate using known vocab
    max_new_words: int = 3  # Max new words to introduce
    source_lang: str = "auto"  # "auto", "en", or "zh" - auto-detects


class CardInfo(BaseModel):
    card_id: int
    note_id: int
    deck_name: str
    fields: dict[str, str]
    interval: int
    due: int
    queue: int  # -1=suspended, 0=new, 1=learning, 2=review, 3=relearning
    status: VocabStatus


class RecallSentence(BaseModel):
    english: str              # English sentence to translate
    chinese: str              # Chinese answer
    pinyin: str               # Pinyin pronunciation
    word_order_english: str   # Word-by-word gloss


class RecallGenerateRequest(BaseModel):
    count: int = 5                          # Number of sentences to generate
    topic: Optional[str] = None             # Optional topic/notes for focused practice
    target_word_count: Optional[int] = None # Target Chinese character count per sentence


class RecallGenerateResponse(BaseModel):
    sentences: list[RecallSentence]
    stats: dict


class RecallPassageRequest(BaseModel):
    topic: Optional[str] = None             # Optional topic/notes for focused practice
    target_char_count: int = 50             # Target total Chinese characters for passage


class ChatMessageModel(BaseModel):
    role: str                               # "user" or "assistant"
    text: str                               # Original text
    words: list[Word]                       # Segmented words with status
    translation: Optional[str] = None       # English translation (AI messages only)


class ChatRequest(BaseModel):
    message: str                            # User's message
    history: list[dict] = []                # Previous messages for context [{role, text}]
    max_new_words: int = 2                  # Max new words to introduce per response


class ChatResponse(BaseModel):
    user_message: ChatMessageModel          # Processed user message
    ai_message: ChatMessageModel            # AI response with words
