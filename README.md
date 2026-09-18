# Hash Out — Modern Discussion Forum

A discussion forum built with **Next.js + FastAPI + Django**, with a premium dark UI.

## Architecture

| Layer | Technology | Port |
|-------|-----------|------|
| **Frontend** | Next.js (App Router), server-rendered | `3000` |
| **API** | FastAPI, JWT in httpOnly cookies | `8001` |
| **Admin** | Django admin (moderation, site settings) | `8000` |
| **Database** | PostgreSQL | `5432` |
| **Redis** | Sessions, verification and reset codes, rate limits, notification pub/sub | `6379` |
| **LLM** | OpenAI-compatible API (optional) | — |

Three services run the app: Postgres, Redis and the two app processes. The Django admin starts on
demand. **The frontend and API must be same-site** (`localhost:3000` → `localhost:8001`, or
`app.example.com` → `api.example.com`), or the browser won't send the auth cookies.

## Features

- 🔐 Signup with emailed verification, login, password reset, and sessions that survive a restart
- 📋 Boards, topics and posts, with editing, deletion and staff moderation (pin, lock, delete)
- 💬 @mentions, emoji reactions and real-time notifications over a WebSocket
- 🔍 Search across boards, topics and posts, with type filters
- 🖼️ Image uploads validated by content, served with `nosniff`
- ✨ AI reply suggestions and topic summaries (optional)
- 🌙 Premium dark theme with glassmorphism and micro-animations

## Quick start (Docker)

```bash
cp env.sample .env                       # then edit: secrets, and SMTP if signups must work
cp frontend/env.sample frontend/.env.local
docker compose up --build                # postgres, redis, api, frontend

docker compose exec fastapi python manage.py migrate
docker compose exec fastapi python manage.py loaddata seed_boards   # three starter boards
docker compose exec fastapi python manage.py createsuperuser
docker compose --profile admin up -d django                          # /admin/ on :8000
```

## Quick start (without Docker)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cd frontend && npm install && cd ..

cp env.sample .env && cp frontend/env.sample frontend/.env.local
# Start PostgreSQL and Redis — both are required

python manage.py migrate
python manage.py loaddata seed_boards
python manage.py createsuperuser

python manage.py runserver                       # admin, :8000
uvicorn api.main:app --port 8001 --reload        # API, :8001
cd frontend && npm run dev                       # frontend, :3000
```

- **Frontend**: http://localhost:3000 · **API docs**: http://localhost:8001/docs · **Admin**: http://localhost:8000/admin/
- With the console email backend (the default), verification and reset codes are printed in the API
  log instead of being sent. Set `EMAIL_HOST` and friends before anyone else signs up.

## Tests and checks

```bash
pytest                                  # 86 tests; needs Postgres (CREATEDB) and Redis
ruff check .
python manage.py check --deploy         # with DEBUG=False and real secrets
pip-audit -r requirements.lock --require-hashes
cd frontend && npx tsc --noEmit && npx eslint src && npm run build
```

CI runs all of the above on every push and pull request (`.github/workflows/ci.yml`).

## Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm fastapi python manage.py migrate
```

The production overlay drops the bind mounts and runs gunicorn (uvicorn workers for the API).
Before deploying:

- **Set real secrets** in `.env`: `SECRET_KEY`, `JWT_SECRET_KEY`, `FERNET_KEY`. The app refuses to
  start with `DEBUG=False` on the sample values.
- **`DEBUG` defaults to `False`.** Set `DEBUG=True` only in development.
- **Put a TLS proxy in front.** Set `client_max_body_size 6m` (uploads are spooled before the 5 MB
  check), forward `X-Forwarded-Proto`, and set `TRUSTED_PROXY_IPS` so rate limits see real client IPs.
- **Set `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`** to your domains.
- **Rebuild the frontend when `NEXT_PUBLIC_API_URL` changes** — Next inlines it at build time.
- **Dependencies are locked with hashes** in `requirements.lock`. Regenerate after editing
  `requirements.txt`: `uv pip compile requirements.txt --generate-hashes -o requirements.lock`.

## Project Structure

```
hash_out/
├── api/                    # FastAPI REST API
│   ├── main.py             # App entry, CORS, /media
│   ├── auth.py             # Cookie sessions, verification, password flows
│   ├── mentions.py         # @username notifications
│   ├── schemas.py          # Pydantic models (the source for the frontend's types)
│   ├── deps.py             # Pagination helper
│   ├── routers/            # boards, topics, posts, search, profiles, notifications, upload, content
│   └── tests/              # pytest suite
├── accounts/               # UserProfile (bio, avatar, reputation, email_verified)
├── boards/                 # Board, Topic, Post, Reaction + admin
├── cms/                    # Encrypted site settings
├── notifications/          # Notification model and Redis pub/sub
├── frontend/               # Next.js app
│   └── src/
│       ├── app/            # Routes (server components + client islands)
│       ├── components/     # UI components
│       ├── lib/            # API clients, auth and WebSocket context
│       └── types/          # Generated from the OpenAPI schema
├── hash_out/               # Django project config
├── plans/                  # The optimization plan and its phase records
├── docker-compose.yml      # Shared; override = development, prod = production
└── requirements.lock       # Hashed dependency lock
```

## License

MIT License
