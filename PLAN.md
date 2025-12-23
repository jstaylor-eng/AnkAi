# AnkAi - Anki-Powered Language Learning Agent

## Overview

A language learning web application that uses Anki flashcard decks as a vocabulary knowledge base (RAG) to help users practice Chinese through reading, conversation, and recall exercises - all using vocabulary they're actually learning.

The interface draws inspiration from Du Chinese's clean reading layout with tappable words, pinyin annotations, and adjustable speech rate.

---

## Current Status (December 2025)

### Production Deployment

**Live at**: http://130.162.167.220 (Oracle Cloud Free Tier)
- **Server**: Oracle Cloud VM.Standard.A1.Flex (x86_64), UK South (London), AD-3
- **Domain**: ainki.duckdns.org (HTTPS currently failing due to DuckDNS CAA record issues with Let's Encrypt)
- **VNC Access**: http://130.162.167.220:3000 (for Anki management)
- **SSH**: `ssh opc@130.162.167.220`

### Server Details

- **OS**: Oracle Linux 9
- **Docker**: Docker 29.1.3, Docker Compose v5.0.0
- **Data locations**:
  - Anki data: `/home/opc/anki-data/`
  - AnkiConnect addon: `/home/opc/AnkAi/anki/addons21/2055492159/`
  - App code: `/home/opc/AnkAi/`

### Deployment Commands

```bash
# SSH into server
ssh opc@130.162.167.220

# Update and redeploy
cd ~/AnkAi
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# View logs
docker logs ankai-backend
docker logs ankai-anki
docker logs ankai-caddy

# Test AnkiConnect
docker exec ankai-anki curl -s http://localhost:8765 -X POST -d '{"action": "version", "version": 6}'

# Restart Anki (if needed)
docker restart ankai-anki
```

### Completed Features

**Phase 1 - Article Reading:**
- **Article Translation**: Paste text or URL, AI rewrites using user's known vocabulary
- **English → Chinese Translation**: Automatically detects English articles and translates to learner-appropriate Chinese
- **Clean Article Extraction**: Uses trafilatura to extract main article content, filters boilerplate text
- **Vocabulary Integration**: Loads vocabulary from selected Anki decks, classifies as NEW/DUE/LEARNED/UNKNOWN
- **Reader Interface**: Du Chinese-inspired layout with tappable words, pinyin, color-coded vocab status
- **TTS Playback**: Browser Speech API with adjustable speed (0.5x-1.0x)
- **Anki Review**: Tap words to review, submit ease ratings directly to Anki

**Phase 2 - Landing Page & Recall:**
- **Landing Page Hub**: Central mode selection after deck selection with expandable card grid
- **Recall Practice**: English → Chinese translation drills
  - LLM generates sentences using user's vocabulary (10-20 characters)
  - Reveal toggles: Chinese, Pinyin, Word Order (word-by-word English gloss)
  - TTS audio playback with speed control
  - Progress navigation with dots
- **Extended Recall**: Generate longer passages with custom topic
  - Optional topic/notes input for focused practice
  - Target character count slider (30-150 characters for full passage)
  - Displays using Reader component (word-by-word breakdown, pinyin, TTS)
  - Collapsible English translation at bottom

**Infrastructure:**
- Cloud Deployment on Oracle Cloud Free Tier with Docker Compose
- Anki Desktop in Docker with AnkiConnect
- Caddy reverse proxy

### Tech Stack (Implemented)

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, TailwindCSS, Vite |
| Backend | Python 3.11, FastAPI, Pydantic |
| Article Extraction | trafilatura (clean main content extraction) |
| Chinese NLP | jieba, pypinyin |
| LLM | Groq API (llama-3.3-70b-versatile) - free tier |
| TTS | edge-tts |
| Anki | anki-desktop-docker + AnkiConnect API |
| Deployment | Docker Compose, Caddy, Oracle Cloud Free Tier |

### Known Issues

1. **HTTPS not working**: DuckDNS has intermittent CAA record issues that prevent Let's Encrypt from issuing certificates. Currently using HTTP only.
2. **AnkiConnect addon location**: The addon must be in `~/AnkAi/anki/addons21/2055492159/` (NOT in the anki_data volume) due to volume mount order in docker-compose

---

## Feature Backlog

### Extended Recall RAG Enhancement
**Goal**: Make generated passages more interesting with real-world context

When user provides a topic, search the web for recent relevant information and include it as context for the LLM to generate more engaging, topical passages.

**Implementation options**:
- DuckDuckGo search (free, rate limited)
- Tavily API (paid, reliable)
- SerpAPI / Serper (paid)

**Backend changes**:
- Add web search helper in `llm_service.py`
- Include search snippets in passage generation prompt
- LLM weaves real information into vocabulary-constrained Chinese

---

### Next Priority: Conversation Mode
**Goal**: AI chat that uses the user's vocabulary

Features:
- Chat interface for conversational practice
- AI uses LEARNED vocabulary, introduces DUE/NEW words naturally
- Each AI message shows Chinese with pinyin (tappable words)
- User can respond in Chinese or English
- Words can be reviewed mid-conversation

**Backend**:
- New `/api/chat` endpoint
- Maintains conversation context
- LLM prompt includes vocabulary constraints

**Frontend**:
- `ChatView.tsx` component
- Message bubbles with word highlighting
- Input field with send button
- Same word popup/review mechanism as Reader

### Completed Features (moved from backlog)

~~**Landing Page Redesign**~~ ✅ Implemented
- Central hub with expandable card grid
- 4 modes: Read Articles, Recall Practice, Extended Recall, Chat (coming soon)
- Vocab stats footer with deck info

~~**Recall Practice Mode**~~ ✅ Implemented
- English → Chinese translation practice
- Reveal options: Chinese characters
  - Pinyin
  - English in Chinese word order (even if grammatically odd)
- TTS to hear the Chinese
- Mark words as reviewed

**Example UI**:
```
┌────────────────────────────────────────────────┐
│ Translate to Chinese:                          │
│                                                │
│ "I want to eat dumplings today."               │
│                                                │
│ [Show Chinese] [Show Pinyin] [Show Word Order] │
│                                                │
│ ☐ 我今天想吃饺子。                              │
│ ☐ wǒ jīntiān xiǎng chī jiǎozi                 │
│ ☐ I today want eat dumplings                   │
│                                                │
│ 🔊 [Play Audio]                                │
│                                                │
│ [Next Sentence]                                │
└────────────────────────────────────────────────┘
```

**Backend**:
- New `/api/recall/generate` endpoint
- LLM generates sentences using constrained vocabulary
- Returns: english, chinese, pinyin, word_order_english

**Frontend**:
- `RecallView.tsx` component
- Toggle checkboxes for each reveal option
- Audio playback button

---

## System Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              Cloud Server                                  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      Web Frontend (React)                            │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐        │  │
│  │  │  Reader   │  │   Deck    │  │  Speech   │  │  Review   │        │  │
│  │  │   View    │  │  Selector │  │  Controls │  │  Feedback │        │  │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                  │                                        │
│                                  ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      Backend API (FastAPI)                           │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐        │  │
│  │  │ Article   │  │  Vocab    │  │   TTS     │  │   Anki    │        │  │
│  │  │ Processor │  │   RAG     │  │  Service  │  │  Bridge   │        │  │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                  │                                        │
│                    ┌─────────────┼─────────────┐                          │
│                    ▼             ▼             ▼                          │
│  ┌──────────────────────┐  ┌──────────┐  ┌──────────┐                    │
│  │  Anki Desktop Docker │  │   LLM    │  │   TTS    │                    │
│  │  ┌────────────────┐  │  │ (Claude) │  │  Engine  │                    │
│  │  │  AnkiConnect   │  │  └──────────┘  └──────────┘                    │
│  │  │   API :8765    │  │                                                │
│  │  └────────────────┘  │                                                │
│  │          ↕           │                                                │
│  │     AnkiWeb Sync     │                                                │
│  └──────────┬───────────┘                                                │
│             │                                                             │
└─────────────┼─────────────────────────────────────────────────────────────┘
              │
              ▼
       ┌─────────────┐         ┌─────────────┐
       │   AnkiWeb   │ ←─────→ │  AnkiDroid  │
       │   (cloud)   │  sync   │  (phone)    │
       └─────────────┘         └─────────────┘
```

---

## Component Details

### 1. Anki Integration Layer

**Connection**: [AnkiConnect](https://github.com/FooSoft/anki-connect) REST API on port 8765, running inside [anki-desktop-docker](https://github.com/mlcivilengineer/anki-desktop-docker) container. Anki syncs with AnkiWeb automatically, keeping all devices in sync.

**Key API Actions**:
| Action | Purpose |
|--------|---------|
| `deckNames` | List available decks for user selection |
| `findCards` | Query cards by deck, due status, new status |
| `cardsInfo` | Get card content (front/back, fields, intervals) |
| `areDue` | Check which cards are due for review |
| `guiAnswerCard` | Submit review response (ease 1-4) |
| `answerCards` | Batch answer cards programmatically |
| `getIntervals` | Get scheduling data for cards |

**Vocabulary Categories**:
```python
class VocabStatus(Enum):
    NEW = "new"           # Never seen - target for introduction
    DUE = "due"           # Up for review - primary conversation focus
    LEARNED = "learned"   # Seen before & not due - safe to use freely
    UNKNOWN = "unknown"   # Not in any selected deck - avoid
```

**Card Query Examples**:
```python
# Get new cards from deck
{"action": "findCards", "params": {"query": "deck:HSK4 is:new"}}

# Get cards due today
{"action": "findCards", "params": {"query": "deck:HSK4 is:due"}}

# Get learned cards (seen before, not due today)
{"action": "findCards", "params": {"query": "deck:HSK4 -is:new -is:due"}}
```

---

### 2. Vocabulary RAG System

**Text Segmentation**: [jieba](https://github.com/fxsjy/jieba) for Chinese word tokenization

**Pipeline**:
```
Input Article
     │
     ▼
┌─────────────────┐
│  Fetch & Clean  │  (newspaper3k or trafilatura)
│  Article Text   │
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  Segment with   │  jieba.cut() with custom dict from Anki
│  jieba          │
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  Classify Each  │  Match against Anki vocab database
│  Word           │  → LEARNED / DUE / NEW / UNKNOWN
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  LLM Rewrite    │  Prompt: rewrite using only LEARNED vocab,
│  (Claude API)   │  introduce DUE/NEW words with context
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  Annotated      │  Each word tagged with status, pinyin,
│  Output         │  definition, audio reference
└─────────────────┘
```

**LLM Prompt Strategy for Article Translation**:
```
You are a Chinese language tutor. Rewrite the following article for a student.

RULES:
1. Use ONLY words from the LEARNED list for general text
2. You MUST include these DUE/NEW words naturally: [list]
3. For any concept requiring UNKNOWN vocabulary, paraphrase using LEARNED words
4. Proper nouns (names, places) may be used sparingly with pinyin
5. Keep the core meaning and information of the original article
6. Mark each DUE/NEW word with [[word]] brackets for highlighting

LEARNED VOCABULARY: [词汇列表...]
DUE FOR REVIEW: [复习词汇...]
NEW TO INTRODUCE: [新词汇...]

ORIGINAL ARTICLE:
[article text]
```

---

### 3. Web App Interface (Du Chinese-inspired)

**Reader View Layout**:
```
┌────────────────────────────────────────────────┐
│  ⚙️ Settings    📚 Deck: HSK4, HSK5           │
├────────────────────────────────────────────────┤
│                                                │
│     yuán xiāo jié                              │
│     元 宵 节                                    │  ← Tappable words
│                                                │
│     yuán xiāo jié shì zhōng guó de chuán...   │
│     元宵节是[[中国]]的传统节日。                 │  ← [[]] = review word
│                                                │
│     ─────────────────────────────────          │
│     Translation: The Lantern Festival is...    │  ← Toggle visibility
│                                                │
├────────────────────────────────────────────────┤
│  🔊 ◀️ ●────────────○ ▶️   0.7x [0.5x-1.0x]    │  ← Speed control
├────────────────────────────────────────────────┤
│  Tap word for definition • Long-press for card │
└────────────────────────────────────────────────┘
```

**Word Popup (on tap)**:
```
┌─────────────────────────┐
│  中国  zhōng guó        │
│  China; Chinese         │
│                         │
│  Status: 📖 Due Today   │
│  ────────────────────── │
│  How well did you know? │
│  [Again] [Hard] [Good] [Easy]
└─────────────────────────┘
```

**Tech Stack**:
- **Frontend**: React + TypeScript + TailwindCSS
- **State**: Zustand or React Query
- **Audio**: Web Audio API for playback control
- **Pinyin**: `pinyin` npm package or backend service

---

### 4. Speech Synthesis

**Options Evaluated**:

| Option | Pros | Cons | Speed Control |
|--------|------|------|---------------|
| Azure TTS | High quality, SSML support | Paid, requires API key | Via SSML `<prosody rate>` |
| Edge TTS | Free, good quality | Unofficial API | Via SSML |
| gTTS | Simple, free | No speed control | Post-process only |
| pyttsx3 | Offline, free | Lower quality | Native `rate` property |
| Browser SpeechSynthesis | No backend needed | Quality varies | `rate` property |

**Recommended**: **Edge TTS** (via `edge-tts` Python package) or **Browser SpeechSynthesis** for MVP

**SSML Speed Control Example**:
```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
  <prosody rate="0.7">
    元宵节是中国的传统节日。
  </prosody>
</speak>
```

**Speed Levels**:
- 0.5x - Very Slow (beginner)
- 0.7x - Slow (learning)
- 0.85x - Moderate
- 1.0x - Native speed

---

### 5. Review Feedback Loop

**Flow**:
```
User taps DUE/NEW word
         │
         ▼
    Shows definition +
    review buttons
         │
         ▼
User selects ease (1-4)
         │
         ▼
┌─────────────────────────┐
│  Backend calls Anki:    │
│  guiAnswerCard or       │
│  answerCards            │
└─────────────────────────┘
         │
         ▼
    Anki updates SRS
    scheduling internally
         │
         ▼
    Next review date
    reflected in app
```

**Ease Mapping**:
| Button | Anki Ease | Effect |
|--------|-----------|--------|
| Again | 1 | Card goes back to learning |
| Hard | 2 | Interval slightly increased |
| Good | 3 | Normal interval increase |
| Easy | 4 | Larger interval increase |

**AnkiConnect Call**:
```python
# Answer current card in review
{
    "action": "guiAnswerCard",
    "params": {"ease": 3}  # 1-4
}

# Or batch answer without GUI
{
    "action": "answerCards",
    "params": {
        "answers": [
            {"cardId": 1498938915662, "ease": 3},
            {"cardId": 1502098034048, "ease": 2}
        ]
    }
}
```

---

## Phase 1: Article Translator MVP

### Features
1. Paste URL or text of Chinese article
2. Select which Anki decks to use as vocabulary source
3. AI rewrites article using known vocabulary
4. Display with pinyin, word highlighting, tap-for-definition
5. Audio playback with speed control
6. Review feedback for highlighted words syncs to Anki

### API Endpoints

```
POST /api/decks/select
  Body: { "deck_names": ["HSK4", "HSK5"] }
  → Loads vocabulary from selected decks

GET /api/decks
  → Returns available Anki decks

POST /api/article/process
  Body: { "url": "..." } or { "text": "..." }
  → Returns processed article with annotations

GET /api/word/{word}
  → Returns definition, pinyin, status, card_id

POST /api/review
  Body: { "card_id": 123, "ease": 3 }
  → Submits review to Anki

GET /api/tts?text=...&rate=0.7
  → Returns audio stream
```

### Data Models

```python
class Word(BaseModel):
    hanzi: str
    pinyin: str
    definition: str
    status: VocabStatus  # NEW, DUE, LEARNED, UNKNOWN
    card_id: Optional[int]

class Sentence(BaseModel):
    original: str
    simplified: str  # Rewritten version
    words: List[Word]
    translation: str

class ProcessedArticle(BaseModel):
    title: str
    sentences: List[Sentence]
    due_words: List[Word]      # Words to review in this article
    new_words: List[Word]      # New words introduced
    stats: dict                # Comprehension %, word counts
```

---

## Phase 2: Conversation Mode (Future)

### Concept
- AI generates conversational scenarios using DUE words
- User responds via text or speech
- AI continues conversation, naturally reinforcing vocabulary
- Comprehension checks built into dialogue

### Example Flow
```
AI: 你今天想吃什么？[[饺子]]还是[[面条]]？
    (What do you want to eat today? Dumplings or noodles?)

User: 我想吃饺子。
      (I want to eat dumplings.)

AI: 好的！你喜欢什么[[馅儿]]的饺子？
    (Great! What filling do you like in dumplings?)
    [馅儿 = filling - DUE word introduced]
```

---

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, TailwindCSS, Vite |
| Backend | Python 3.11+, FastAPI, Pydantic |
| Chinese NLP | jieba, pypinyin |
| LLM | Claude API (claude-3-sonnet or haiku) |
| TTS | edge-tts or Browser SpeechSynthesis |
| Anki | anki-desktop-docker + AnkiConnect API |
| Deployment | Docker Compose (Anki + Backend + Frontend) |
| Database | SQLite (vocab cache) |

---

## File Structure (Proposed)

```
AnkAi/
├── docker-compose.yml        # Orchestrates all services
├── backend/
│   ├── Dockerfile
│   ├── main.py               # FastAPI app
│   ├── anki_client.py        # AnkiConnect wrapper
│   ├── vocab_manager.py      # Vocabulary RAG logic
│   ├── article_processor.py  # Fetch, segment, rewrite
│   ├── tts_service.py        # Text-to-speech
│   ├── models.py             # Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── components/
│   │   │   ├── Reader.tsx        # Main reading view
│   │   │   ├── WordPopup.tsx     # Definition popup
│   │   │   ├── DeckSelector.tsx  # Deck picker
│   │   │   ├── SpeedSlider.tsx   # TTS speed control
│   │   │   └── ReviewButtons.tsx
│   │   ├── hooks/
│   │   │   ├── useAnki.ts
│   │   │   └── useTTS.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── anki/
│   └── config.json           # AnkiConnect config
├── PLAN.md
└── README.md
```

**Docker Compose Services**:
- `anki`: anki-desktop-docker with AnkiConnect (port 8765 internal)
- `backend`: FastAPI server (port 8000)
- `frontend`: React app via nginx (port 80)

---

## Implementation Order

### Sprint 1: Foundation
- [ ] Set up FastAPI backend with AnkiConnect client
- [ ] Implement deck listing and vocabulary extraction
- [ ] Create vocabulary status classification (NEW/DUE/LEARNED)
- [ ] Basic React frontend with deck selector

### Sprint 2: Article Processing
- [ ] Article fetcher (URL → clean text)
- [ ] jieba segmentation with Anki vocab as custom dict
- [ ] LLM rewriting with vocabulary constraints
- [ ] Annotated output with word classifications

### Sprint 3: Reader Interface
- [ ] Du Chinese-style reader component
- [ ] Pinyin display above characters
- [ ] Tappable words with popup definitions
- [ ] Sentence-by-sentence layout

### Sprint 4: Audio & Review
- [ ] TTS integration with speed control
- [ ] Review buttons in word popup
- [ ] AnkiConnect review submission
- [ ] Review status sync/refresh

### Sprint 5: Polish
- [ ] Error handling and loading states
- [ ] Settings persistence
- [ ] Mobile-responsive design
- [ ] Performance optimization

---

## Design Decisions

1. **Anki field mapping**: Config UI to map fields per deck, with auto-detect for common patterns (e.g., "Hanzi", "Chinese", "Front", "Simplified")

2. **Mobile-first / Anki dependency**:
   - Target: Usable on Android phone via web app
   - MVP: Can require Anki desktop running on computer (same network), but minimize this dependency
   - Goal: Cache vocabulary locally so reading works offline, only need Anki connection for syncing reviews
   - *See "Anki Sync Strategy" below*

3. **Relationship to Anki apps**: This is a standalone web app, separate from AnkiDroid/AnkiMobile. Those apps are too fixed to support these features.

4. **Language support**: Mandarin Chinese only for now, but make extensible decisions when they arise (modular segmentation/TTS)

---

## Anki Sync Strategy

AnkAi implements the Anki sync protocol, becoming a first-class sync client alongside AnkiDroid and Anki Desktop.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Anki Desktop│     │  AnkiDroid  │     │   AnkAi     │
│   (home)    │     │  (mobile)   │     │ (web app)   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │    Anki Sync Protocol (HTTPS)         │
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   AnkiWeb   │
                    │  (cloud)    │
                    └─────────────┘
```

**Benefits**:
- All devices stay in sync automatically
- No changes to existing Anki setup
- Works on any device with a browser
- AnkiWeb remains the single source of truth

### Sync Protocol Implementation

Based on [reverse-engineered protocol docs](https://github.com/Catchouli/learny/wiki/Anki-sync-protocol):

**Authentication**:
```
POST /sync/hostKey
Body: {username, password}
Returns: {key: "session_key"}
```

**Sync Flow**:
```
1. /sync/meta         → Get server metadata, check if sync needed
2. /sync/start        → Initialize sync session
3. /sync/applyChanges → Send local changes (reviews, edits)
4. /sync/chunk        → Receive server changes in chunks
5. /sync/applyChunk   → Acknowledge received chunks
6. /sync/sanityCheck2 → Validate sync integrity
7. /sync/finish       → Complete sync
```

**Key Data** (from Anki's SQLite schema):
- `cards` - Card state, due date, interval, ease factor, queue
- `revlog` - Review history (timestamp, card_id, ease, interval)
- `notes` - Note content (fields, tags)
- `decks` - Deck hierarchy and settings

### What AnkAi Needs from Sync

**Pull (read)**:
- Cards with vocabulary fields (hanzi, pinyin, definition)
- Card scheduling state (new, due, learned)
- Deck membership

**Push (write)**:
- Review log entries when user reviews in AnkAi
- Updated card scheduling (new interval, ease, due date)

### Reference Implementations

- [AnkiDroid sync](https://github.com/ankidroid/Anki-Android) (Kotlin)
- [anki-sync-server](https://github.com/ankicommunity/ankicommunity-sync-server) (Python)
- [Anki desktop](https://github.com/ankitects/anki) (Rust/Python)

### Deployment Options

**Option A: Implement Sync Protocol** (complex, full control)
- Build sync client from scratch using reverse-engineered protocol
- Direct integration with AnkiWeb
- Significant development effort

**Option B: Anki Desktop in Docker** (simpler, recommended for MVP)
- Use [anki-desktop-docker](https://github.com/mlcivilengineer/anki-desktop-docker)
- Run Anki desktop headlessly on cloud server
- Anki handles AnkiWeb sync normally
- AnkAi uses AnkiConnect API (port 8765)

```
┌─────────────┐     ┌─────────────┐
│  AnkiDroid  │     │ Anki Desktop│ (Docker, cloud-hosted)
│  (phone)    │     │ + AnkiConnect API
└──────┬──────┘     └──────┬──────┘
       │                   │
       └───────┬───────────┘
               ▼
        ┌─────────────┐
        │   AnkiWeb   │
        └─────────────┘
               ▲
               │ AnkiConnect API (localhost:8765)
               │
        ┌──────┴──────┐
        │   AnkAi     │
        │  Backend    │
        └─────────────┘
```

**Option B Benefits**:
- AnkiConnect API is well-documented (no reverse engineering)
- Anki handles all sync complexity with AnkiWeb
- Proven, stable approach
- Can trigger sync via API before/after AnkAi sessions

**Setup**:
1. Deploy anki-desktop-docker to cloud server
2. Configure AnkiConnect addon with `"webBindAddress": "0.0.0.0"`
3. Log into AnkiWeb via VNC (port 3000) once to authenticate
4. AnkAi backend connects to AnkiConnect on same server
5. Cron job triggers periodic sync with AnkiWeb

---

## Cloud Deployment (Oracle Cloud Free Tier)

Oracle Cloud offers an always-free tier that's perfect for this application:
- **4 ARM CPUs, 24GB RAM** (Ampere A1) - FREE forever
- **200GB block storage** - FREE
- No credit card required in many regions

### Architecture on Oracle Cloud

```
┌──────────────────────────────────────────────────────────────┐
│                    Oracle Cloud VM (ARM)                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Docker Compose                        │ │
│  │                                                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │   Frontend   │  │   Backend    │  │    Anki      │   │ │
│  │  │   (nginx)    │  │  (FastAPI)   │  │   Desktop    │   │ │
│  │  │   :80/:443   │  │    :8000     │  │  + Connect   │   │ │
│  │  └──────────────┘  └──────────────┘  │    :8765     │   │ │
│  │         │                 │          │    :3000     │   │ │
│  │         │                 │          │   (VNC)      │   │ │
│  │         │                 │          └──────────────┘   │ │
│  │         │                 │                 │           │ │
│  │         └────────┬────────┴─────────────────┘           │ │
│  │                  │                                       │ │
│  └──────────────────┼───────────────────────────────────────┘ │
│                     │                                        │
│              Caddy Reverse Proxy                             │
│              (auto HTTPS via Let's Encrypt)                  │
│                     │                                        │
└─────────────────────┼────────────────────────────────────────┘
                      │
                   Internet
                      │
              ┌───────┴───────┐
              │  Your Phone   │
              │   Browser     │
              └───────────────┘
```

### Setup Steps

#### 1. Create Oracle Cloud Account
1. Go to https://cloud.oracle.com
2. Sign up for free tier (no credit card in many regions)
3. Choose a region close to you

#### 2. Create VM Instance
```bash
# In Oracle Cloud Console:
# Compute → Instances → Create Instance

# Settings:
# - Image: Ubuntu 22.04 (ARM compatible)
# - Shape: VM.Standard.A1.Flex
# - OCPUs: 4 (free), Memory: 24GB (free)
# - Add SSH key for access
# - Boot volume: 100GB (free up to 200GB)
```

#### 3. Configure Security Rules
```bash
# In Oracle Cloud Console:
# Networking → Virtual Cloud Networks → Your VCN → Security Lists

# Add Ingress Rules:
# - Port 80 (HTTP)
# - Port 443 (HTTPS)
# - Port 3000 (VNC for Anki setup - temporary)
```

#### 4. SSH into VM and Install Docker
```bash
ssh ubuntu@<your-vm-ip>

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin
```

#### 5. Clone and Configure AnkAi
```bash
git clone https://github.com/yourusername/AnkAi.git
cd AnkAi

# Create .env file
cat > .env << 'EOF'
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
LLM_PROVIDER=groq
ANKIWEB_USER=your_ankiweb_email
ANKIWEB_PASS=your_ankiweb_password
EOF
```

#### 6. Create Production Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  anki:
    image: mlcivilengineer/anki-desktop:latest
    platform: linux/amd64  # Needs emulation on ARM
    environment:
      - DISPLAY=:99
    volumes:
      - anki_data:/root/.local/share/Anki2
    ports:
      - "3000:3000"  # VNC (remove after setup)
      - "8765:8765"  # AnkiConnect
    restart: unless-stopped

  backend:
    build: ./backend
    environment:
      - ANKI_CONNECT_URL=http://anki:8765
      - GROQ_API_KEY=${GROQ_API_KEY}
      - GROQ_MODEL=${GROQ_MODEL}
      - LLM_PROVIDER=${LLM_PROVIDER}
    depends_on:
      - anki
    restart: unless-stopped

  frontend:
    build: ./frontend
    depends_on:
      - backend
    restart: unless-stopped

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  anki_data:
  caddy_data:
```

#### 7. Create Caddyfile (Auto-HTTPS)
```
# Caddyfile
your-domain.com {
    # Frontend
    handle /* {
        reverse_proxy frontend:80
    }

    # API
    handle /api/* {
        reverse_proxy backend:8000
    }
}
```

If you don't have a domain, use the VM's public IP with HTTP only:
```
:80 {
    handle /* {
        reverse_proxy frontend:80
    }
    handle /api/* {
        reverse_proxy backend:8000
    }
}
```

#### 8. Build and Run
```bash
# Build containers
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

#### 9. Initial Anki Setup (one-time)
```bash
# Access VNC in browser
# Go to http://<your-vm-ip>:3000

# In Anki (via VNC):
# 1. Click Sync
# 2. Log in with AnkiWeb credentials
# 3. Download your decks
# 4. Close VNC

# After setup, remove VNC port from security rules for safety
```

#### 10. Set Up Auto-Sync (cron)
```bash
# Create sync script
cat > /home/ubuntu/AnkAi/sync-anki.sh << 'EOF'
#!/bin/bash
curl -s http://localhost:8765 -X POST -d '{"action": "sync", "version": 6}'
EOF
chmod +x /home/ubuntu/AnkAi/sync-anki.sh

# Add to crontab (sync every hour)
(crontab -l 2>/dev/null; echo "0 * * * * /home/ubuntu/AnkAi/sync-anki.sh") | crontab -
```

### Free Domain Options

If you don't have a domain:
1. **DuckDNS** (free): https://www.duckdns.org - Get a subdomain like `ankai.duckdns.org`
2. **FreeDNS**: https://freedns.afraid.org
3. **No domain**: Just use `http://<vm-ip>` (no HTTPS)

### Maintenance

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Restart services
docker compose -f docker-compose.prod.yml restart

# Update code
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Manual Anki sync
curl http://localhost:8765 -X POST -d '{"action": "sync", "version": 6}'
```

### Cost Summary

| Resource | Oracle Free Tier |
|----------|-----------------|
| Compute (4 ARM cores, 24GB) | FREE |
| Storage (200GB) | FREE |
| Bandwidth (10TB/month) | FREE |
| Public IP | FREE |
| **Total** | **$0/month** |

---

## References

- [AnkiConnect API](https://git.sr.ht/~foosoft/anki-connect) - REST API for Anki
- [anki-desktop-docker](https://github.com/mlcivilengineer/anki-desktop-docker) - Containerized Anki with AnkiConnect
- [Anki sync protocol](https://github.com/Catchouli/learny/wiki/Anki-sync-protocol) - Reverse-engineered protocol docs
- [jieba Chinese segmentation](https://github.com/fxsjy/jieba)
- [Du Chinese app](https://www.duchinese.net/) - UI inspiration
- [edge-tts](https://pypi.org/project/edge-tts/) - Free TTS option
- [pypinyin](https://pypi.org/project/pypinyin/) - Pinyin conversion
