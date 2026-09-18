# Hash Out — Modern Discussion Forum

Full-stack discussion forum built with **Django + FastAPI + Next.js** and a premium dark UI.

## Architecture

| Layer | Technology | Port |
|-------|-----------|------|
| **Frontend** | Next.js (App Router) | `3000` |
| **API** | FastAPI + JWT Auth | `8001` |
| **Admin** | Django admin (moderation, site settings) | `8000` |
| **Database** | PostgreSQL | `5432` |
| **Redis** | Sessions, reset codes, rate limits, notification pub/sub | `6379` |
| **LLM** | OpenAI-compatible API | — |
| **Ads** | Google AdSense | — |

## Features

- 🔐 JWT authentication (login, signup, refresh tokens)
- 📋 Board/topic/post CRUD with FastAPI REST endpoints
- 🔍 Search across boards, topics and posts
- ✨ AI content generation (reply suggestions, topic summaries)
- 🔔 Real-time notifications over a WebSocket
- 💰 Google AdSense integration (banner, sidebar, infeed)
- 🌙 Premium dark theme with glassmorphism and micro-animations

## Quick Start

### 1. Install Dependencies

Everything at once with Docker: `docker compose up` (Postgres, Redis, API, frontend; add
`--profile admin` for the Django admin). To run it directly instead:

```bash
# Python (backend)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Node.js (frontend)
cd frontend
npm install
```

### 2. Configure Environment

```bash
cp env.sample .env
cp frontend/env.sample frontend/.env.local
# Edit .env with your PostgreSQL and Redis URLs, secrets, and API keys
```

### 3. Run Services

```bash
# Start PostgreSQL and Redis (Docker or local) — both are required

# Django migrations
python manage.py migrate
python manage.py createsuperuser

# Start Django admin (port 8000)
python manage.py runserver

# Start FastAPI (port 8001)
uvicorn api.main:app --port 8001 --reload

# Start Next.js frontend (port 3000)
cd frontend && npm run dev
```

### 4. Access

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8001/docs
- **Django Admin**: http://localhost:8000/admin/

## Project Structure

```
hash_out/
├── api/                    # FastAPI REST API
│   ├── main.py             # FastAPI app entry
│   ├── auth.py             # JWT authentication
│   ├── schemas.py          # Pydantic models
│   ├── deps.py             # Pagination helper
│   └── routers/
│       ├── boards.py       # Board CRUD
│       ├── topics.py       # Topic CRUD
│       ├── posts.py        # Post CRUD
│       ├── search.py       # Search over the ORM
│       └── content.py      # LLM content generation
├── accounts/               # Django auth app
├── boards/                 # Django boards app
│   └── models.py           # Board, Topic, Post models
├── cms/                    # Encrypted site settings
├── frontend/               # Next.js frontend
│   └── src/
│       ├── app/            # App Router pages
│       ├── components/     # UI components
│       └── lib/            # API client & auth
├── hash_out/               # Django project config
│   └── settings.py         # All service configuration
└── requirements.txt        # Python dependencies
```

## License

MIT License