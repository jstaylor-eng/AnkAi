import re
import os
from pypinyin import pinyin, Style
from models import VocabStatus, Word, CardInfo
import anki_client


def load_cedict() -> dict[str, str]:
    """Load CC-CEDICT dictionary file"""
    dictionary = {}
    cedict_path = os.path.join(os.path.dirname(__file__), "cedict.txt")

    if not os.path.exists(cedict_path):
        print("CC-CEDICT not found, dictionary lookups disabled")
        return dictionary

    with open(cedict_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            # Format: Traditional Simplified [pinyin] /def1/def2/
            match = re.match(r'^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$', line.strip())
            if match:
                traditional, simplified, pinyin_text, definitions = match.groups()
                # Use first definition, clean it up
                first_def = definitions.split("/")[0].strip()
                # Store by simplified (more common in mainland Chinese)
                if simplified not in dictionary:
                    dictionary[simplified] = first_def
                # Also store traditional
                if traditional not in dictionary:
                    dictionary[traditional] = first_def

    print(f"Loaded {len(dictionary)} dictionary entries")
    return dictionary


# Global dictionary instance
CEDICT = load_cedict()


class VocabManager:
    """Manages vocabulary from Anki decks"""

    # Track new words introduced today (across all articles)
    _introduced_today: set[str] = set()
    _introduced_date: str = ""  # ISO date string for reset check
    _daily_new_limit: int = 5   # Default, will be updated from deck config

    # Basic vocabulary assumed known by any learner (HSK1-3 level essentials)
    BASIC_VOCAB = {
        # Numbers
        "零", "一", "二", "两", "三", "四", "五", "六", "七", "八", "九", "十",
        "百", "千", "万", "亿", "第", "半", "几",
        # Pronouns
        "我", "你", "您", "他", "她", "它", "我们", "你们", "他们", "她们", "它们",
        "这", "那", "这个", "那个", "这些", "那些", "这样", "那样",
        "什么", "谁", "哪", "哪个", "哪里", "哪儿", "哪些",
        "自己", "大家", "别人", "每", "每个", "所有", "一些", "有些", "某",
        # Particles & conjunctions
        "的", "地", "得", "了", "着", "过", "吗", "呢", "吧", "啊", "呀", "嘛", "啦",
        "和", "与", "或", "或者", "但", "但是", "因为", "所以", "如果", "虽然", "不过",
        "而", "而且", "然后", "就是", "只是", "可是", "于是", "因此", "另外",
        # Basic verbs
        "是", "有", "在", "要", "会", "能", "可以", "想", "去", "来", "做", "说", "看", "听",
        "知道", "觉得", "喜欢", "给", "让", "把", "被", "到", "从", "用", "找", "买", "卖",
        "吃", "喝", "睡", "走", "跑", "站", "坐", "开", "关", "开始", "结束", "完", "完成",
        "变", "变化", "变成", "成为", "成", "叫", "请", "问", "回答", "帮", "帮助",
        "等", "等待", "需要", "应该", "必须", "得", "可能", "希望", "相信", "认为",
        "发现", "感觉", "记得", "忘记", "学", "学习", "工作", "生活", "住", "离开",
        # Basic adjectives & adverbs
        "好", "大", "小", "多", "少", "新", "旧", "老", "长", "短", "高", "低", "快", "慢",
        "早", "晚", "远", "近", "难", "容易", "重要", "简单", "复杂", "一样", "不同",
        "清楚", "明白", "正确", "错误", "安全", "危险", "特别", "一般", "正常",
        "真", "假", "对", "错", "全", "满", "空", "忙", "累", "舒服",
        # Time words
        "年", "月", "日", "号", "天", "星期", "周", "时", "分", "秒", "点", "刻",
        "今天", "明天", "昨天", "后天", "前天", "今年", "明年", "去年",
        "现在", "以前", "以后", "之前", "之后", "时候", "时间", "最近", "将来", "过去",
        "上午", "下午", "晚上", "早上", "中午", "夜里", "白天",
        "经常", "常常", "总是", "有时", "有时候", "偶尔", "从来", "已经", "刚", "刚才", "马上", "立刻",
        # Days & months
        "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期天", "星期日",
        "周一", "周二", "周三", "周四", "周五", "周六", "周日", "周末",
        "一月", "二月", "三月", "四月", "五月", "六月",
        "七月", "八月", "九月", "十月", "十一月", "十二月",
        # Measure words
        "个", "位", "只", "条", "张", "本", "件", "块", "杯", "瓶", "次", "遍", "些",
        "种", "双", "对", "套", "群", "家", "所", "座", "层", "排", "节", "份",
        # Locations/directions
        "上", "下", "左", "右", "前", "后", "里", "外", "中", "内", "东", "西", "南", "北",
        "这里", "那里", "里面", "外面", "上面", "下面", "前面", "后面", "旁边", "中间",
        "附近", "周围", "对面", "边", "处", "地", "方",
        # Common nouns
        "人", "家", "国", "中国", "东西", "事", "事情", "问题", "地方", "话", "字", "词",
        "路", "车", "火车", "汽车", "飞机", "公交", "地铁", "站",
        "钱", "元", "块", "毛", "分", "价格", "数", "数字", "号码",
        "名字", "年龄", "身体", "头", "手", "脚", "眼睛", "耳朵",
        "水", "饭", "菜", "肉", "鱼", "米", "面", "茶", "酒", "咖啡",
        "书", "报", "纸", "笔", "电话", "手机", "电脑", "电视", "网", "网络",
        "门", "窗", "桌子", "椅子", "床", "房间", "厨房", "厕所", "卫生间",
        "公司", "学校", "医院", "商店", "超市", "银行", "酒店", "餐厅", "机场",
        "朋友", "同学", "老师", "学生", "医生", "先生", "女士", "小姐", "孩子", "男", "女",
        "爸爸", "妈妈", "父亲", "母亲", "儿子", "女儿", "哥哥", "姐姐", "弟弟", "妹妹",
        # Question words
        "怎么", "怎么样", "怎样", "为什么", "为何", "多少", "几", "多", "多长", "多久", "多远",
        # Negation & degree
        "不", "没", "没有", "别", "很", "太", "非常", "最", "更", "比较", "真", "挺", "相当",
        "都", "也", "还", "就", "才", "只", "只有", "又", "再", "越", "越来越",
        # Prepositions
        "在", "从", "到", "往", "向", "对", "给", "跟", "和", "比", "按", "按照", "根据", "关于",
        # Other common
        "好的", "可以", "谢谢", "不客气", "对不起", "没关系", "再见", "你好",
        "当然", "一定", "肯定", "确实", "其实", "原来", "终于", "居然", "竟然",
        "首先", "然后", "最后", "同时", "另外", "例如", "比如",
    }

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

        # Check if it's basic vocabulary (assumed known)
        if hanzi in self.BASIC_VOCAB:
            return Word(
                hanzi=hanzi,
                pinyin=self._generate_pinyin(hanzi),
                definition="(basic)",
                status=VocabStatus.LEARNED,
                card_id=None,
                deck_name="basic"
            )

        # Check for partial matches - word is part of a known word
        # e.g., 火车 matches if we know 火车站
        partial_match = self._find_partial_match(hanzi)
        if partial_match:
            return Word(
                hanzi=hanzi,
                pinyin=self._generate_pinyin(hanzi),
                definition=f"→ {partial_match.hanzi}: {partial_match.definition}",
                status=partial_match.status,  # Inherit status from full word
                card_id=partial_match.card_id,
                deck_name=partial_match.deck_name
            )

        # Unknown word - try dictionary lookup for definition
        definition = self._lookup_definition(hanzi)
        return Word(
            hanzi=hanzi,
            pinyin=self._generate_pinyin(hanzi),
            definition=definition,
            status=VocabStatus.UNKNOWN,
            card_id=None,
            deck_name=None
        )

    def _lookup_definition(self, hanzi: str) -> str:
        """Look up definition in CC-CEDICT dictionary"""
        return CEDICT.get(hanzi, "")

    def _find_partial_match(self, hanzi: str) -> Word | None:
        """Find a known word that contains this word as a component"""
        if len(hanzi) < 1:
            return None

        # Look for known words that start with or contain this word
        for known_hanzi, word in self.vocab.items():
            # Skip if same length (would be exact match, already checked)
            if len(known_hanzi) <= len(hanzi):
                continue
            # Check if known word starts with this word (e.g., 火车 in 火车站)
            if known_hanzi.startswith(hanzi):
                return word
            # Check if known word ends with this word (e.g., 车站 in 火车站)
            if known_hanzi.endswith(hanzi):
                return word

        return None

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

    # --- Daily new word limit management ---

    def _check_date_reset(self) -> None:
        """Reset introduced words if it's a new day"""
        from datetime import date
        today = date.today().isoformat()
        if today != VocabManager._introduced_date:
            VocabManager._introduced_today = set()
            VocabManager._introduced_date = today
            print(f"New day detected, reset introduced words tracker")

    async def update_daily_limit_from_deck(self) -> int:
        """Get the new cards per day limit from the first selected deck"""
        if not self.selected_decks:
            return VocabManager._daily_new_limit

        try:
            deck_config = await anki_client.get_deck_config(self.selected_decks[0])
            new_per_day = deck_config.get("new", {}).get("perDay", 5)
            VocabManager._daily_new_limit = new_per_day
            print(f"Updated daily new card limit from deck config: {new_per_day}")
            return new_per_day
        except Exception as e:
            print(f"Could not get deck config for daily limit: {e}")
            return VocabManager._daily_new_limit

    def get_remaining_new_allowance(self) -> int:
        """Get how many more new words can be introduced today"""
        self._check_date_reset()
        remaining = VocabManager._daily_new_limit - len(VocabManager._introduced_today)
        return max(0, remaining)

    def get_introduced_today(self) -> set[str]:
        """Get the set of new words introduced today"""
        self._check_date_reset()
        return VocabManager._introduced_today.copy()

    def mark_words_introduced(self, words: list[str]) -> None:
        """Mark words as introduced today"""
        self._check_date_reset()
        for word in words:
            VocabManager._introduced_today.add(word)
        print(f"Marked {len(words)} new words as introduced. Total today: {len(VocabManager._introduced_today)}")

    def get_daily_stats(self) -> dict:
        """Get stats about daily new word usage"""
        self._check_date_reset()
        return {
            "daily_limit": VocabManager._daily_new_limit,
            "introduced_today": len(VocabManager._introduced_today),
            "remaining": self.get_remaining_new_allowance(),
            "words": list(VocabManager._introduced_today)
        }
