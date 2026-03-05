# Boards — Modern Discussion Forum

Full-stack discussion forum built with **Django + FastAPI + Next.js** and a premium dark UI.

## Architecture

| Layer | Technology | Port |
|-------|-----------|------|
| **Frontend** | Next.js (App Router) + HTMX | `3000` |
| **API** | FastAPI + JWT Auth | `8001` |
| **CMS/Admin** | Django + Wagtail | `8000` |
| **Database** | PostgreSQL | `5432` |
| **Cache** | Redis | `6379` |
| **Search** | Elasticsearch | `9200` |
| **Tasks** | Celery (Redis broker) | — |
| **LLM** | OpenAI-compatible API | — |
| **Ads** | Google AdSense | — |

## Features

- 🔐 JWT authentication (login, signup, refresh tokens)
- 📋 Board/topic/post CRUD with FastAPI REST endpoints
- 🔍 Elasticsearch-powered search with ORM fallback
- 💬 HTMX-style inline forms for topic/post creation
- ✨ AI content generation (reply suggestions, topic summaries)
- 📰 Wagtail CMS for static content pages
- ⚡ Redis caching for API responses
- 📅 Celery background tasks (indexing, emails, LLM)
- 💰 Google AdSense integration (banner, sidebar, infeed)
- 🌙 Premium dark theme with glassmorphism and micro-animations

## Quick Start

### 1. Install Dependencies

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
cp .env.example .env
# Edit .env with your PostgreSQL, Redis, Elasticsearch, and API keys
```

### 3. Run Services

```bash
# Start PostgreSQL, Redis, Elasticsearch (Docker or local)

# Django migrations
python manage.py migrate
python manage.py createsuperuser

# Start Django/Wagtail (port 8000)
python manage.py runserver

# Start FastAPI (port 8001)
uvicorn api.main:app --port 8001 --reload

# Start Celery worker
celery -A myproject worker -l info

# Start Next.js frontend (port 3000)
cd frontend && npm run dev
```

### 4. Access

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8001/docs
- **Django Admin**: http://localhost:8000/admin/
- **Wagtail CMS**: http://localhost:8000/cms-admin/

## Project Structure

```
myproject/
├── api/                    # FastAPI REST API
│   ├── main.py             # FastAPI app entry
│   ├── auth.py             # JWT authentication
│   ├── schemas.py          # Pydantic models
│   ├── deps.py             # Redis cache & pagination
│   ├── tasks.py            # Celery background tasks
│   └── routers/
│       ├── boards.py       # Board CRUD
│       ├── topics.py       # Topic CRUD + HTMX
│       ├── posts.py        # Post CRUD + HTMX
│       ├── search.py       # Elasticsearch search
│       └── content.py      # LLM content generation
├── accounts/               # Django auth app
├── boards/                 # Django boards app
│   ├── models.py           # Board, Topic, Post models
│   └── documents.py        # Elasticsearch DSL documents
├── cms/                    # Wagtail CMS pages
├── frontend/               # Next.js frontend
│   └── src/
│       ├── app/            # App Router pages
│       ├── components/     # UI components
│       └── lib/            # API client & auth
├── myproject/              # Django project config
│   ├── settings.py         # All service configuration
│   └── celery.py           # Celery app
├── templates/              # Django templates (legacy)
└── requirements.txt        # Python dependencies
```

## License

MIT License