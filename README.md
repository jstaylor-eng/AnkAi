# AnkAi

Learn Chinese using your Anki vocabulary. Process articles and see words highlighted by their review status.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Anthropic API key (for LLM features)

### Setup

1. **Clone and configure:**
   ```bash
   cd AnkAi
   cp .env.example .env
   # Edit .env with your ANTHROPIC_API_KEY
   ```

2. **Start services:**
   ```bash
   docker-compose up -d
   ```

3. **Initial Anki setup (one-time):**
   - Open http://localhost:3000 (VNC web interface)
   - Log into your AnkiWeb account in Anki
   - Install AnkiConnect addon (code: 2055492159) if not already present
   - Sync your decks

4. **Use AnkAi:**
   - Open http://localhost (web app)
   - Select your vocabulary decks
   - Paste Chinese text to analyze

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Docker Compose                      │
│                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ Frontend│  │ Backend │  │ Anki Desktop    │ │
│  │ :80     │→ │ :8000   │→ │ + AnkiConnect   │ │
│  │ (nginx) │  │(FastAPI)│  │ :8765           │ │
│  └─────────┘  └─────────┘  └────────┬────────┘ │
│                                      │          │
└──────────────────────────────────────┼──────────┘
                                       ↓
                                   AnkiWeb
                                       ↑
                                   AnkiDroid
```

## Features

- **Vocabulary-aware text processing**: Words are classified as learned, due, new, or unknown
- **Interactive reader**: Tap words to see definitions and submit reviews
- **Anki sync**: Reviews sync back to Anki, keeping all devices updated
- **Pinyin display**: Toggle pinyin above characters

## Development

### Backend only:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend only:
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

- `GET /api/health` - Check Anki connection
- `GET /api/decks` - List available decks
- `POST /api/decks/select` - Select decks to load vocabulary
- `POST /api/article/process` - Process article text
- `POST /api/review` - Submit card review
- `POST /api/sync` - Trigger AnkiWeb sync

## License

MIT
