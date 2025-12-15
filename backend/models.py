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
