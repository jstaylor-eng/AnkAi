import re
from pypinyin import pinyin, Style
from models import VocabStatus, Word, CardInfo
import anki_client


class VocabManager:
    """Manages vocabulary from Anki decks"""

    def __init__(self):
        self.selected_decks: list[str] = []
        self.vocab: dict[str, Word] = {}  # hanzi -> Word
        self.field_mappings: dict[str, dict] = {}  # deck -> field mappings

    async def select_decks(self, deck_names: list[str]) -> dict:
        """Select decks and load their vocabulary"""
        self.selected_decks = deck_names
        self.vocab.clear()

        stats = {"total": 0, "new": 0, "due": 0, "learned": 0}

        for deck_name in deck_names:
            deck_stats = await self._load_deck_vocab(deck_name)
            stats["total"] += deck_stats["total"]
            stats["new"] += deck_stats["new"]
            stats["due"] += deck_stats["due"]
            stats["learned"] += deck_stats["learned"]

        return stats

    async def _load_deck_vocab(self, deck_name: str) -> dict:
        """Load vocabulary from a single deck"""
        stats = {"total": 0, "new": 0, "due": 0, "learned": 0}

        # Get all cards in deck
        card_ids = await anki_client.get_all_cards(deck_name)
        if not card_ids:
            return stats

        # Get card info in batches
        batch_size = 100
        for i in range(0, len(card_ids), batch_size):
            batch = card_ids[i:i + batch_size]
            cards_info = await anki_client.get_cards_info(batch)

            for card_info in cards_info:
                word = self._extract_word_from_card(card_info, deck_name)
                if word and word.hanzi:
                    # Don't overwrite if we already have this word with better status
                    if word.hanzi not in self.vocab:
                        self.vocab[word.hanzi] = word
                        stats["total"] += 1
                        if word.status == VocabStatus.NEW:
                            stats["new"] += 1
                        elif word.status == VocabStatus.DUE:
                            stats["due"] += 1
                        else:
                            stats["learned"] += 1

        return stats

    def _extract_word_from_card(self, card_info: dict, deck_name: str) -> Word | None:
        """Extract a Word from card info, detecting field mappings"""
        fields = card_info.get("fields", {})

        # Try to find hanzi field
        hanzi = self._find_field(fields, [
            "Hanzi", "Chinese", "Simplified", "Character", "Characters",
            "Word", "Vocab", "Front", "Expression", "Headword"
        ])

        if not hanzi:
            return None

        # Clean the hanzi (remove HTML, etc.)
        hanzi = self._clean_text(hanzi)
        if not hanzi:
            return None

        # Try to find pinyin field, or generate it
        pinyin_text = self._find_field(fields, [
            "Pinyin", "Reading", "Pronunciation"
        ])
        if not pinyin_text:
            pinyin_text = self._generate_pinyin(hanzi)
        else:
            pinyin_text = self._clean_text(pinyin_text)

        # Try to find definition field
        definition = self._find_field(fields, [
            "Definition", "Meaning", "English", "Translation", "Back", "Gloss"
        ])
        definition = self._clean_text(definition) if definition else ""

        # Determine status from card queue
        queue = card_info.get("queue", 0)
        due = card_info.get("due", 0)
        interval = card_info.get("interval", 0)

        if queue == 0:  # New
            status = VocabStatus.NEW
        elif queue in (1, 3) or (queue == 2 and due <= 0):  # Learning, relearning, or due
            status = VocabStatus.DUE
        else:  # Review queue with future due date
            status = VocabStatus.LEARNED

        return Word(
            hanzi=hanzi,
            pinyin=pinyin_text,
            definition=definition,
            status=status,
            card_id=card_info.get("cardId"),
            deck_name=deck_name
        )

    def _find_field(self, fields: dict, possible_names: list[str]) -> str | None:
        """Find a field by trying multiple possible names (case-insensitive)"""
        fields_lower = {k.lower(): v for k, v in fields.items()}
        for name in possible_names:
            if name.lower() in fields_lower:
                field_data = fields_lower[name.lower()]
                # Handle both string and dict formats
                if isinstance(field_data, dict):
                    return field_data.get("value", "")
                return field_data
        return None

    def _clean_text(self, text: str) -> str:
        """Remove HTML tags and clean up text"""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()

    def _generate_pinyin(self, hanzi: str) -> str:
        """Generate pinyin for Chinese text"""
        result = pinyin(hanzi, style=Style.TONE)
        return ' '.join([p[0] for p in result])

    def classify_word(self, hanzi: str) -> Word:
        """Classify a word based on loaded vocabulary"""
        if hanzi in self.vocab:
            return self.vocab[hanzi]

        # Unknown word - not in any selected deck
        return Word(
            hanzi=hanzi,
            pinyin=self._generate_pinyin(hanzi),
            definition="",
            status=VocabStatus.UNKNOWN,
            card_id=None,
            deck_name=None
        )

    def get_words_by_status(self, status: VocabStatus) -> list[Word]:
        """Get all words with a specific status"""
        return [w for w in self.vocab.values() if w.status == status]

    def get_vocab_list(self) -> list[Word]:
        """Get all loaded vocabulary"""
        return list(self.vocab.values())

    async def refresh_card_status(self, card_id: int) -> None:
        """Refresh the status of a specific card after review"""
        cards_info = await anki_client.get_cards_info([card_id])
        if cards_info:
            card_info = cards_info[0]
            # Find and update the word
            for word in self.vocab.values():
                if word.card_id == card_id:
                    # Update status based on new queue
                    queue = card_info.get("queue", 0)
                    due = card_info.get("due", 0)
                    if queue == 0:
                        word.status = VocabStatus.NEW
                    elif queue in (1, 3) or (queue == 2 and due <= 0):
                        word.status = VocabStatus.DUE
                    else:
                        word.status = VocabStatus.LEARNED
                    break
