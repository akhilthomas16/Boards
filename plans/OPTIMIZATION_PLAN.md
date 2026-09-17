# Hash Out — Optimization & Completion Plan

**Renamed** 2026-09-17 from *Boards* — the Django project package is now `hash_out/`; the `boards` app keeps its name (it holds boards, topics and posts).
**Status:** Phase 0 ✅ done on `feat/inital-bug-fix` — installs and imports from a clean clone, all topic endpoints return 200, writes no longer need Elasticsearch, nothing sensitive is tracked. **Next: Phase 1.**
**Audit basis:** 8-dimension review of every tracked source file, 199 findings, each re-verified against the code by a second pass (25 corrected, 0 withdrawn). Spot-checked by hand where the stakes were highest.
**Audited:** 2026-09-16 at `e8b0d45` · **Updated:** 2026-09-17 after Phase 0 (`7616072`). Line numbers cite the audited commit; files touched in Phase 0 have shifted.

---

## 0. Executive summary

| | |
|---|---|
| Python (project) | 3,528 LOC |
| TypeScript/React | 2,694 LOC |
| FastAPI layer | 1,683 LOC, 25 endpoints |
| Django templates + vendored static | 381 LOC + 432 KB |
| Tests | 497 LOC legacy, **all of it testing code this plan deletes** · 7 new DB-free tests since Phase 0 |
| Tracked junk | ~~`.env`, `db.sqlite3` (1 MB), 67 `.pyc` files, no root `.gitignore`~~ ✅ resolved in Phase 0 |
| Services declared | 6 (postgres, redis, elasticsearch, django, fastapi, celery, frontend) |
| Services actually needed | 3 (postgres, redis, + the two app processes) |

**Three findings that matter more than the rest:**

1. ✅ *Fixed in Phase 0 (`9079f33`).* **`slowapi` is imported and not declared.** `api/limiter.py:1` and `api/main.py:15-16` import it; `requirements.txt` never lists it. A clean install or `docker compose up` dies with `ModuleNotFoundError` before serving one request.
2. ✅ *Fixed in Phase 0 (`6f37d32`).* **`Topic.tags` does not exist.** `api/routers/topics.py:31` reads `topic.tags` and `:106` writes it; `boards/models.py:30-49` has no such field and no migration adds one. Every topic endpoint — trending on the home page, topic detail, board topic list, topic creation — raises `AttributeError` → 500.
3. **The project carries three UI stacks and pays for all three.** Django templates + a rumour of HTMX + Next.js. Only Next.js works. The Django forum views are still routed and one of them (`boards/views.py:14-32`) is an **unauthenticated POST that creates topics attributed to `User.objects.first()`** — usually the superuser.

**The target architecture** — all three independently-written roadmaps converged on it:

> Next.js is the only thing that serves HTML. FastAPI is the only thing that serves JSON. Django is a library (ORM + auth hashers + migrations) plus `/admin/` as the moderation console.

Getting there is mostly deletion. Roughly 2,000 lines and 4 services leave; about 400 lines of genuinely new code arrive (moderation endpoints, mention parsing, a settings page, tests).

### Corrections to the alarming-sounding parts

I checked these myself rather than pass them on:

- **The committed `.env` holds placeholders**, not live secrets: `django-insecure-change-me-in-production-503-92o4`, `change-me-jwt-secret-key-in-production`, `your-openai-api-key-here`, dev Postgres creds. 
- **The committed `db.sqlite3` contains 0 users** (`select count(*) from auth_user` → 0), so no password hashes leaked.
- Therefore this is **not a credential emergency**. It is a real defect for two reasons: the tracked `.env` means the *next* real key gets committed automatically, and `hash_out/settings.py:21` hardcodes a **working Fernet key** as its default — which makes the CMS "encrypted secret" feature decryptable by anyone with the repo. That one is a genuine broken control.
- **The venv is one level up**, at `/home/akhil/code/test/myproject/venv` (Python 3.12.5). It already had `slowapi 0.1.9` installed, which is why the missing declaration never showed locally. Bare `python` on this machine resolves to an unrelated project's venv — call the interpreter by full path.
- **The migration graph is clean.** `manage.py makemigrations --check --dry-run` → `No changes detected`, against a `boards_db` with 61 tables and all migrations applied. The `pending migrations` commit message (`d9f6ecf`) is stale — ignore it. (`Topic.tags` is consistently absent from model *and* database, which is exactly why the API 500s.)
- ✅ *Resolved in Phase 0 (`658b21b`).* **Every write used to fail on this machine:** `Board.objects.create(...)` raised `AuthenticationException(401)`. The local Elasticsearch 8.19 requires auth, `settings.py` supplies none, and `django-elasticsearch-dsl`'s default `RealTimeSignalProcessor` bulk-indexed inside every save.
- **`boards_user` has no `CREATEDB` privilege.** Django's test runner and `pytest-django` both need to create `test_boards_db`, so no database-backed test can run until a Postgres superuser runs `ALTER ROLE boards_user CREATEDB;`. This blocks Phase 1's replacement tests.
- **A placeholder `OPENAI_API_KEY` is exported in the editor's process environment** (not in any shell profile — most likely the editor loaded the old `.env` at startup). Real environment variables beat `.env`, so restart the editor after editing `.env` or the AI endpoints keep sending the stale value.

---

## Phase 0 — Make it boot, and stop the bleeding ✅ Done

**Completed 2026-09-17** on `feat/inital-bug-fix`, 13 commits (`0ec17da` … `7616072`).

| Commit | What landed |
|---|---|
| `0ec17da` | Root `.gitignore`; 67 `__pycache__` files untracked |
| `9079f33` | `slowapi` declared in `requirements.txt` |
| `658b21b` | `ELASTICSEARCH_DSL_AUTOSYNC = False` — writes no longer 401 on the local ES; `.env.example` renamed to `env.sample` |
| `6f37d32` | `Topic.tags` field, migration `0005`, `tags` on `TopicCreate` and `TopicResponse` |
| `d439b4e` | Tags normalized on write (lowercased, trimmed, de-duplicated); `similar_topics` ranks by tag overlap, then same-board recency — replaces `ORDER BY RANDOM()` |
| `3e05a4d` | Search falls back to the ORM when Elasticsearch errors **or** returns 0 hits (with autosync off, the index is stale by design) |
| `6843ebf` | `.env` and `db.sqlite3` untracked |
| `b97e10c` | `api/__init__.py` reduced to a docstring; `api/tests/test_tags.py` sets up Django itself |
| `a4cce12` | `content.py`: one undecorated `_generate()` helper. Suggest-reply and summarize-topic now return 503 with no key, 502 on an upstream error, 404 on an unknown topic — instead of 500 on every call. The catch-all that echoed exception text to clients is gone |
| `ffef11f` | `requirements-dev.txt` (`pytest`, `pytest-django`) and `pytest.ini` |
| `bc03d35` | No `FERNET_KEY` default; startup refuses `DEBUG=False` on a dev or placeholder `SECRET_KEY`, `JWT_SECRET_KEY` or `FERNET_KEY`; `SiteSetting` raises on a missing key or bad token instead of returning ciphertext; decrypted secrets are never cached in Redis; `cms/tests.py` (6 tests) |
| `7001691` | Compose: `DATABASE_URL` replaces the dead `DB_HOST` ×3; Postgres, Redis and Elasticsearch no longer published; obsolete `version:` key removed |
| `7616072` | `frontend/.dockerignore`; `frontend/env.sample`; README env copy commands |

### Where it departed from the original plan

- **The startup check guards three secrets, not one.** `SECRET_KEY` and `JWT_SECRET_KEY` sit alongside `FERNET_KEY` — a production deploy on the default JWT secret lets anyone forge login tokens.
- **The Postgres port was removed, not scoped to `127.0.0.1`.** A host Postgres already on `127.0.0.1:5432` makes the scoped publish collide. Reach the compose database with `docker compose exec postgres psql`.
- **No `EMAIL_*` keys in `env.sample`.** The original item was wrong: `settings.py` doesn't read them. They land in Phase 4 with the code that does.
- **The AdSense keys went to `frontend/env.sample`**, not the root file — Next.js only reads `frontend/.env*`.
- **`email-validator` moved to Phase 2**, where `EmailStr` first needs it.
- **Bare `pytest` runs `api/` and `cms/` only** (`testpaths` in `pytest.ini`). The `accounts/` and `boards/` suites need `CREATEDB` and only cover the template views Phase 1 deletes.

### Exit criteria

```
git ls-files | grep -E '^\.env$|sqlite|__pycache__'   ✅ empty
git grep 'RVkCS56'                                    ✅ empty
python -c "import api.main"                           ✅ 44 routes
curl :8001/api/topics/trending                        ✅ 200
pytest                                                ✅ 7 passed
manage.py makemigrations --check --dry-run            ✅ No changes detected
docker compose config                                 ✅ valid · 0 infra ports published
docker compose up --build                             ⏸ not run — pulls and builds images; run before Phase 7
```

**History note:** the placeholder `.env` blobs stay reachable at `8cdc5a1`/`d299596` on the public remote. The values were placeholders, so `git filter-repo` is optional; any real deployment needs freshly generated keys regardless, and the startup check now enforces that.

**Before pulling on another clone:** `6843ebf` removes `.env` from the index, so pulling it **deletes the local `.env`**. Back it up first.

---

## Phase 1 — One UI stack: delete the Django SSR forum and HTMX (1–2 days)

Almost entirely `git rm`. Three prerequisites must land **first**, because deleting the Django UI removes capability that exists nowhere else.

### Prerequisites (blocking)

1. **Password validation.** `accounts/forms.py` (Django's `UserCreationForm`) is today the *only* path that runs `AUTH_PASSWORD_VALIDATORS`. `api/auth.py` signup accepts any string. Add `validate_password()` to `api/auth.py` signup (before `create_user` at `:159`) and to `reset_password` (replacing the ad-hoc `len < 8` at `:236`), converting `ValidationError` → HTTP 400.
2. **`POST /api/auth/change-password`.** The Django templates serve a working password-change page; `api/auth.py` has no such route (only the OTP reset flow). Add it: old + new password, `Depends(get_current_user)`, `validate_password`, `@limiter.limit("5/minute")`.
3. **Replacement tests.** Grant `CREATEDB` to `boards_user` first — these tests need a database. `pytest.ini` already exists (Phase 0); add `api/tests/test_auth.py` before deleting `accounts/tests/`. Port the cases that are still meaningful: duplicate username (`auth.py:154`), duplicate email (`:156`), access+refresh pair shape (`:131-134`), refresh rejects an access token (the type check at `:77-78`), identical forgot-password message for known and unknown emails.

### The deletion commit (these are mutually dependent — one commit)

```
git rm -r templates/ static/ \
          boards/views.py boards/urls.py boards/forms.py boards/templatetags/ \
          accounts/views.py accounts/forms.py \
          accounts/tests/ boards/tests/test_views.py boards/tests/test_templatetags.py \
          notifications/views.py notifications/tests.py \
          accounts/admin.py notifications/admin.py \
          hash_out/asgi.py
```

Plus, in the same commit:

- `hash_out/urls.py:22` — remove `path('', include('boards.urls'))`. Django then serves only `/admin/`, `/cms-admin/`, `/documents/`. (Confirm no proxy or healthcheck hits `/`.)
- `hash_out/settings.py` — delete `STATICFILES_DIRS` (`:234-236`), `widget_tweaks` from `INSTALLED_APPS` (`:54`), and `corsheaders` (`:53`, `:70`, `:175-180`) — Django no longer serves anything cross-origin. Keep `STATIC_URL`/`STATIC_ROOT`: the admin and Wagtail admin still need `collectstatic`.
- `requirements.txt` — drop `django-widget-tweaks`, `django-cors-headers`, `passlib[bcrypt]` (the `CryptContext` at `api/auth.py:11,22` is constructed and never used — Django's hashers do all hashing), `httpx` (zero runtime imports — move it to `requirements-dev.txt`, where FastAPI's `TestClient` needs it).
- **HTMX eradication**, all three layers: delete `api/routers/topics.py:117-153` and `api/routers/posts.py:101-142` (HTML-fragment endpoints in a JSON API, referenced nowhere, interpolating user text into markup unescaped) and the `HTMLResponse` imports at `topics.py:7`/`posts.py:7`; `npm uninstall htmx.org`; fix the three comments that claim an HTMX architecture (`boards/[id]/page.tsx:2,134`, `topics/[id]/page.tsx:2`); strip the HTMX claims from `README.md:9,24,95,96`.
- **Wagtail pages.** `cms/models.py:15-70` defines four `Page` models with **no templates anywhere** — `/pages/...` raises `TemplateDoesNotExist`. Delete them + the `DeleteModel` migration + `hash_out/urls.py:25`. Keep `SiteSetting` (registered as a snippet by `cms/wagtail_hooks.py:32-40`) and keep Wagtail installed only if the settings/snippet console is wanted; otherwise this is the moment to drop `wagtail` from `requirements.txt` and the 13 Wagtail entries from `INSTALLED_APPS`.
- `pytest.ini` — drop the `ponytail:` comment explaining the `testpaths` exclusion; the suites it excluded are gone.
- `boards/admin.py` — register `Topic`, `Post`, `Reaction` and `notifications.Notification`. ~15 lines, and it is the *entire* interim moderation story: `is_pinned`/`is_locked` are writable from nowhere in `api/`.
- Free cleanup: `git rm frontend/public/{next,vercel,file,globe,window}.svg`; `git rm --cached frontend/public/sw.js frontend/public/workbox-*.js` and gitignore them; delete the `icons` array in `manifest.json:9-20` (it advertises two 404s, which blocks the install prompt anyway).

**Exit criteria:** `grep -rn 'render(' --include='*.py' .` returns nothing outside `cms/wagtail_hooks.py`; `git ls-files | grep -E '^templates/|^static/'` is empty; the new `api/tests/` suite is green.

---

## Phase 2 — One auth system, and a ban that actually bans (2–3 days)

`grep -rn is_active api/` returns **zero hits**. A user deactivated in `/admin/` keeps full API access and can still mint fresh tokens forever.

- `api/auth.py:92-102` `get_current_user` — resolve on the immutable claim and enforce activity: `User.objects.filter(pk=payload['user_id'], is_active=True).first()`, 401 on `None`. Fixes two defects at once: the ban bypass, and identity resolution through the **mutable** `username` (`sub`) when `user_id` is already in the token.
- `api/auth.py:119-134` `login` — 401 when `not user.is_active`. `api/auth.py:137-147` `refresh` — re-load the user and 401 if missing or inactive; today it re-mints a pair without ever touching the database.
- `/refresh` has **no rate limit** and no `request: Request` param — add both. Then add a `jti` claim, store `jti → user_id` in Redis for the token TTL, consume-and-rotate on refresh, and revoke the family on reuse; check the denylist in `verify_token`.
- **OTP flow** (`api/auth.py:190-241`) — one shared helper for `verify_otp` and `reset_password`: `secrets.randbelow(900000)+100000` instead of `random.randint` (a 6-digit code from a non-cryptographic PRNG), store `{"otp":…, "attempts":0}`, compare with `hmac.compare_digest`, delete after 5 failures. Note `verify_otp:213-220` does not consume the code, so a successful verify leaves it live for the full 10 minutes.
- **The reset email is never sent.** `api/auth.py:208` calls `send_otp_email.delay(...)`, but `hash_out/celery.py:11` calls `autodiscover_tasks()` with no packages and `api` is not in `INSTALLED_APPS` — the task is unregistered, so the enqueue is a silent drop. Either `app.conf.imports = ('api.tasks',)` or (see Phase 4) call it synchronously.
- `api/limiter.py:4` — `Limiter(key_func=..., storage_uri=settings.REDIS_URL)`. In-memory storage means the `5/minute` login limit resets on restart and does not apply across workers.
- `api/auth.py` — `UserCreate.email` is a bare `str` while `EmailStr` sits imported and unused at `:12`. Use `EmailStr` (add `email-validator` to `requirements.txt` — Pydantic raises at import without it), add `constr(min_length=8)` for the password, normalize the email to lowercase before the uniqueness check.
- **Token custody.** Both JWTs live in `localStorage` (`frontend/src/lib/api.ts:11-27`) on pages that render user-authored markdown and load a third-party AdSense script. Move custody server-side: Next route handlers (`app/api/auth/login|refresh|logout/route.ts`) that proxy FastAPI and set `httpOnly` + `Secure` + `SameSite=Lax` cookies; `apiFetch` switches to `credentials:'include'` against a same-origin proxy. **Prerequisite:** consolidate the nine raw `fetch` calls that bypass `lib/api.ts` today (`auth.tsx:47`, `WebSocketProvider.tsx:36,79`, `PostCard.tsx:38`, `MarkdownEditor.tsx:134`, `profile/[username]/page.tsx`, `forgot-password/page.tsx`, both `layout.tsx` files) — export `API_BASE` and add `postForm(endpoint, URLSearchParams)` / `postMultipart(endpoint, FormData)` helpers first.
- Once cookies land: `api/routers/notifications.py:65` reads the cookie from `websocket.cookies` instead of a query-string token, and `close()` happens **before** `accept()` so an unauthenticated handshake is rejected cleanly. Drop `token=` from `WebSocketProvider.tsx:45`.
- `api/routers/profiles.py` — `get_profile` (`:84`) and `search_users` (`:76`) are **unauthenticated and return every matched user's email**. Add a `PublicProfileResponse` without `email` and use it as their `response_model` (FastAPI filters unknown fields, so this is a two-line fix); keep the email-bearing schema on `/me` only. Add `Query(..., min_length=2)` and a rate limit to the search.

**Exit criteria:** `is_active=False` in `/admin/` → 401 on `/me`, `/token` and `/refresh` and a closed WebSocket; a reused refresh token is rejected and its family revoked; 5 wrong OTPs lock the code; `grep -rn 'localStorage\|Bearer ' frontend/src` returns nothing; anonymous `GET /api/profiles/<username>` contains no `email`.

---

## Phase 3 — Fix what a user hits in the first ten minutes (1–1½ days)

Small local edits. No refactors.

**Upload path**
- `api/routers/upload.py:49` returns `/media/uploads/<uuid>.png` — origin-relative, so `MarkdownEditor.tsx:140` inserts a URL that resolves against **port 3000** and 404s. Every uploaded image in every post is broken. Cleanest single fix: add a `/media/:path*` rewrite to `frontend/next.config.ts` pointing at `NEXT_PUBLIC_API_URL` — then stored markdown stays portable *and* the manual prefix at `profile/[username]/page.tsx:135` can go.
- `upload.py:42` and `profiles.py:137` derive the stored extension from the **client's filename** while validating only the **client's** `content_type`. `evil.html` with a spoofed `image/png` header lands in a directory served by `StaticFiles` (`api/main.py:56-58`). Map the validated content type to an extension via a dict, add `PIL.Image.open(io.BytesIO(contents)).verify()`, and in `profiles.py` stop embedding the client filename at all (`f"{current_user.username}{ext}"`). Serve `/media` with a forced `Content-Type` and `X-Content-Type-Options: nosniff`.
- The 5 MB check runs *after* Starlette has spooled the whole body. Enforce `client_max_body_size 6m` at the edge.

**Data integrity**
- `boards/models.py` — `Topic.last_updated` is never bumped when a reply is posted, so the default ordering (`['-is_pinned','-last_updated']`) is wrong. One `post_save` receiver on `Post` doing `Topic.objects.filter(pk=instance.topic_id).update(last_updated=timezone.now())` beats patching three call sites. (`.update()` is required — `auto_now` won't fire on a queryset update, which is exactly what you want here.)
- Atomic counters: `api/routers/topics.py:84` → `.update(views_count=F('views_count') + 1)`; same for `reputation_score` at `posts.py:227-234`. Read-modify-write loses concurrent increments.
- `posts.py:227-234` — reputation is granted for reacting to **your own** post, one row per distinct emoji, with an unvalidated emoji string. Guard with `if post.created_by_id != current_user.id:` and constrain the emoji to a `Literal`.
- `boards/migrations/0003:30-34` adds `Board.slug` as `SlugField(blank=True, unique=True)` with no default — it fails on any database with more than one existing board. Fix it **now**, while no populated deployment exists: `AddField(null=True)` → `RunPython` that slugifies with a `-{pk}` collision suffix → `AlterField(unique=True)`.

**Frontend bugs**
- `boards/[id]/page.tsx:73` — the effect omits `page` from its deps, so **board pagination is completely dead**. Add `page`, and `setLoading(true)` as the effect's first statement (otherwise `.finally` leaves it false forever).
- `WebSocketProvider.tsx:31` — `if (!tokens) return` is dead code: `getTokens()` always returns an object. Anonymous visitors open a socket with `token=null`; logged-in users never rebuild it on login. Use `if (!tokens.access) return`, put `user` in the dep array, add backoff reconnect guarded by a `cancelled` flag.
- `topics/[id]/page.tsx:166` — `split('\\n')` produces a literal `\n` in quoted blockquotes. Use a real newline.
- `PostCard.tsx:30-46` — the optimistic reaction count never rolls back on failure and fires for anonymous users. Gate on `useAuth().user` and revert in the failure branch.
- `Navbar.tsx:121-123` links to `/settings`, a route that does not exist. Delete the link now; build the page in Phase 5.
- `WebSocketProvider.tsx:54` gates desktop notifications on `Notification.permission === 'granted'` and nothing ever calls `requestPermission()` — the whole branch is unreachable. Either request permission on a user gesture or delete the branch.
- `notifications.py:64-107` — the bare `pubsub.listen()` loop never notices a client disconnect, and `channel_name` is referenced in `finally` while only assigned after `verify_token` succeeds → `NameError` on an invalid token. Use `asyncio.wait` over `pubsub.get_message(timeout=1)` + `websocket.receive_text()`, catch `WebSocketDisconnect` explicitly, initialize `channel_name = None`, and switch `print` → `logging`.
- Accessibility: `id`/`htmlFor` pairs at `boards/[id]/page.tsx:142-162` and `profile/[username]/page.tsx:192-220`, `aria-label` on the message textarea, `aria-expanded`/`aria-haspopup` plus outside-click and Escape handling on the three `Navbar` dropdowns.
- `cms/wagtail_hooks.py:92,96` — `monthly_revenue` and `active_users` go through `mark_safe` unescaped (the escaping precedent is right there at `:112`). Editor-to-admin stored XSS.

**Exit criteria:** a 12-item manual pass — upload an image and see it render; anonymous profile response has no email; board pagination works; a reply bumps the topic to the top; `evil.html` with a spoofed content type gets a 400.

---

## Phase 4 — Six services → three (1–2 days)

Both heavy services are either dead or actively harmful.

**Elasticsearch — delete it.** `boards/documents.py:9,23,40` register three documents with the default `RealTimeSignalProcessor`, which made **every Board/Topic/Post write depend on Elasticsearch being up**. Phase 0 turned autosync off, so the index is now stale by design and search already leans on the ORM fallback (`3e05a4d`) — Elasticsearch carries no weight at all. The search path also has real bugs: `search.py:80` links post hits to `/topics/<post_id>` (the *post's* pk — every post result navigates somewhere unrelated), and `_search_orm`'s `total` is computed from different sets than the ones it slices, with a `|` union that yields duplicates.
- `git rm boards/documents.py`; delete `_search_elasticsearch` and the try/except at `search.py:23-29`; remove `django_elasticsearch_dsl` from `INSTALLED_APPS`, the `ELASTICSEARCH_DSL` block and `ELASTICSEARCH_DSL_AUTOSYNC` (`settings.py:139-149`), and both keys from `env.sample`; drop `elasticsearch`/`django-elasticsearch-dsl` from requirements; remove the service, the `es_data` volume and the three `ELASTICSEARCH_URL` lines from compose; delete `api/tasks.py:7-30` and `:101-107`.
- Rewrite `_search_orm` as the only path: one combined result list, `total` from the same filtered sets that get sliced, `type` as a `Literal['all','board','topic','post']`, correct per-type totals.
- *If you want real search later:* Postgres full-text (`SearchVector` + a GIN index) costs no new service.

**Celery — delete it.** Its single `.delay()` call is already a silent no-op (unregistered task, see Phase 2), and five of the six tasks have no caller at all.
- `api/auth.py:208` → call `send_otp_email(data.email, otp)` directly inside try/except with `logging.exception`, returning the same enumeration-safe message either way. A 6-digit code the user is waiting for should not be queued anyway.
- Delete `hash_out/celery.py`, `hash_out/__init__.py:6-8`, the `CELERY_*` block (`settings.py:147-156`), `celery[redis]`, and the worker service.
- Add the email settings the OTP path has always assumed: `DEFAULT_FROM_EMAIL` (currently unset while `tasks.py` passes `from_email=None`), `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`. Document them in `env.sample` — Phase 0 deliberately left them out because nothing read them yet.
- *Bring Celery back when* a task is genuinely slow and nobody is waiting on it (digest emails, bulk reindex). Not for one OTP.

**Redis stays, and the README should say so.** It is not an optional cache: it holds sessions (`SESSION_ENGINE = cache`), the OTP store, the rate-limit counters (once `storage_uri` is set) and the notification pub/sub. Add a `LocMemCache` branch for when `REDIS_URL` is absent so tests can run without it.

**Delete the dead cache layer.** `api/deps.py:19-32` defines a `cached` decorator that is **never applied to anything** (and is `async`, incompatible with every sync handler in the codebase), so all **ten** `invalidate_cache()` calls — `topics.py:113,142`, `boards.py:66,85,102`, `posts.py:97,132,164,183,236` — clear namespaces nothing ever writes. Delete the decorator, all ten call sites, and the imports they leave behind (`json`, `wraps`, `Optional`, `settings` in `deps.py`; keep `paginate`).

**Exit criteria:** `docker compose up` starts exactly postgres, redis, fastapi, frontend (django on demand); `grep -rin 'elasticsearch\|celery' --include='*.py' --include='*.txt' --include='*.yml' .` is empty; search returns correct totals and post hits link to their topic.

---

## Phase 5 — One rendering model, one API contract (2–3 days)

- **Three route pages are 100% client components** (`boards/[id]`, `topics/[id]`, `profile/[username]`) that ship a spinner as their HTML, double-fetch data their server `layout.tsx` already fetched, and call `useSearchParams()` with no `Suspense` boundary — which bails the whole route out of prerendering. Convert them to async server components reading `params`/`searchParams` with `next: { revalidate: 60 }`, mirroring `app/page.tsx:37-57`, and extract client islands (`<NewTopicForm boardId>`, `<ReplyForm topicId>`, `<ProfileEditForm>`). This conversion is also what fixes the dead pagination and the splice-into-current-page bugs structurally rather than one at a time.
- **SSR-in-Docker:** server components fetch from *inside* the frontend container, where `NEXT_PUBLIC_API_URL=http://localhost:8001` (compose `:131`) points at the container's own loopback. Add a server-side `API_INTERNAL_URL=http://fastapi:8001`.
- **Fix the schemas before generating types**, or you generate the wrong ones: `api/schemas.py` has no `reactions`/`my_reactions` on posts and no `badges` on users, though the routers return all three. Then `npx openapi-typescript http://localhost:8001/openapi.json -o src/types/api.d.ts` into the **currently empty** `frontend/src/types/`, and replace the five hand-written interfaces that disagree with the backend.
- Add `loading.tsx` and `error.tsx` per segment so a failed detail fetch does not escalate to the root `error.tsx` and blow away the whole page.
- **Indexes** — there are none on any model, despite every hot query being filter+sort: `Topic ['board','-is_pinned','-last_updated']` and `['-views_count','-last_updated']`, `Post ['topic','created_at']`, `Notification ['recipient','is_read','-created_at']`.
- **N+1s** (do these before the indexes; they cut more latency): `posts.py:60` → `select_related('created_by__profile','updated_by')` plus an annotated author post count (the profile badge lookup costs 3 queries *per post*); `boards.py:15-35` → one `annotate(Count('topics'), Count('topics__posts'), Max('topics__posts__created_at'))` instead of 3 queries per board; `topics.py:28` → annotate `Count('posts')` instead of a COUNT per row (20+ per list page). (The `ORDER BY RANDOM()` in `similar_topics` is already gone — `d439b4e`.)
- `accounts/models.py:49-53` — the `save_user_profile` receiver writes `UserProfile` on **every** `User.save()`, including every password change. Delete it; `create_user_profile` already handles creation.
- `notifications/models.py:29` opens a **new Redis connection per notification**. Use a module-level client.
- Frontend hygiene while the files are open: `npm uninstall @ducanh2912/next-pwa tailwindcss @tailwindcss/postcss` (next-pwa is a webpack plugin and the build runs Turbopack, so `sw.js` can never regenerate; Tailwind is imported at `globals.css:1` and **not one utility class is used**), delete `postcss.config.mjs` and the `withPWA` wrapper, fix the five lint findings (bare `catch {}` in both layouts, `node` prop and `any` in `MarkdownRenderer`, duplicate `next/navigation` imports).

**Exit criteria:** `npm run build` reports those three routes as server-rendered; `grep -rn "'use client'" frontend/src/app/*/*/page.tsx` is empty; a seeded 50-topic board renders in a constant number of queries (assert with `assertNumQueries`).

---

## Phase 6 — Complete the product (3–5 days)

Every item here is capability that exists on one side of the boundary and nowhere on the other.

| Gap | What exists | What's missing |
|---|---|---|
| **Moderation** | `is_pinned`, `is_locked` fields; `PROTECT` FKs | No endpoint writes them. Add staff-gated `PATCH /api/topics/{id}` + `DELETE` (delete must cascade posts explicitly — FKs are `PROTECT`), plus a staff action row in the UI |
| **Post edit/delete** | `posts.py:145-183`, author-or-staff enforced | Zero UI. Pass `currentUserId`/`isStaff` into `PostCard`, wire `api.patch`/`api.delete` |
| **@mentions** | Full autocomplete in `MarkdownEditor.tsx:37-54` | The write path never parses mentions, so they notify nobody. Also `:83` strips the `@` (off-by-one on `cursor - match[1].length`) |
| **Reactions** | `Reaction` model, POST endpoint, counts | The API never says which reactions are *yours*, forcing a `-2` count hack in `PostCard.tsx:28`. Return `my_reactions: list[str]` (needs a real optional-auth dependency — see below) |
| **Notifications** | Model, list, mark-one-read, WS delivery | No unread-count, no mark-all (the client loops one request per notification at `WebSocketProvider.tsx:86-88`), no delete, no pagination, no `/notifications` page |
| **Search UI** | API supports `type` + pagination | `search/page.tsx:36` sends neither. Add type tabs and `<Pagination>` |
| **Settings page** | `Navbar` links to it | Route does not exist. Build `app/settings/page.tsx` on `/api/profiles/me` + the new change-password endpoint |
| **Email verification** | Nothing | Accounts are live on first POST. Either add it (`is_active=False` + `verify:{email}` code + `POST /api/auth/verify-email`) or decide explicitly not to and document it |
| **Profile display** | `reputation_score`, `badges` returned | Never rendered |
| **AdSense** | `AdBanner` reads 4 env vars, documented in `frontend/env.sample` (Phase 0) | Unset values still render a visible "AdSense Slot: …" placeholder. Real account → set them; no account → delete `AdBanner` |

Note: `api/auth.py:105-112` `get_optional_user` is dead code that **cannot work** — `OAuth2PasswordBearer` defaults to `auto_error=True`, so the token is never `None` and it raises instead of returning `None`. Delete it and add a second scheme with `auto_error=False` where optional auth is genuinely needed (reactions, public profiles).

---

## Phase 7 — Production shape and CI (2–3 days)

**Nothing in this repo can currently be deployed:** compose runs `runserver` and `uvicorn --reload`, the backend `Dockerfile` has no `CMD` and no `collectstatic`, the frontend `Dockerfile` ships `next dev`, both containers run as root, and there is no gunicorn, no whitenoise, and no CI at all.

- `requirements.txt` — add `gunicorn>=22`, `whitenoise>=6.6`. Insert `WhiteNoiseMiddleware` immediately after `SecurityMiddleware` (`settings.py:71`) and set the manifest static storage.
- `settings.py:19` — flip `DEBUG` to `default=False`, and add the hardening settings that **do not exist at all**, guarded by `if not DEBUG`: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS`, `SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE`, `CSRF_COOKIE_SECURE`. Note `hash_out/urls.py:29`'s media branch goes dead with `DEBUG=False` — WhiteNoise or the proxy must serve it.
- `Dockerfile` — delete `:9-11` (`build-essential` + `libpq-dev`; `psycopg2-binary` ships wheels — verify one clean build doesn't fall back to source), add `useradd --uid 10001 app` + `USER app`, add `RUN python manage.py collectstatic --noinput` **after** `COPY . .`, add a `CMD` with gunicorn.
- `frontend/next.config.ts` — `output: 'standalone'`; rewrite `frontend/Dockerfile` as three stages (deps → builder running `npm run build` with `NEXT_PUBLIC_*` as build **ARGs**, since Next inlines them at build time → runner copying `.next/standalone` + `.next/static` + `public`, `USER node`, `CMD ["node","server.js"]`).
- Split compose: shared definitions in `docker-compose.yml`, dev shape (reload servers, `.:/app` bind mounts) in `docker-compose.override.yml`, production in `docker-compose.prod.yml`. **Drop the `.:/app` bind mounts in production** — they re-mount the host tree, including the `.env` that `.dockerignore` deliberately excluded from the image.
- Healthchecks: `/api/health` already exists (`api/main.py:61`) and nothing uses it. Add it to the api service and make the frontend `depends_on: {condition: service_healthy}`.
- **Supply chain:** 19 of 21 requirements float on `>=` with no lockfile. `pip-compile --generate-hashes`, `pip install --require-hashes` in the Dockerfile, bump `cryptography==42.0.5` (pinned old — run `pip-audit` rather than trusting any assertion about it), add `pip-audit` to CI.
- **CI** (`.github/workflows/ci.yml`) with postgres + redis service containers:
  1. `python -c "import api.main"` — the cheap guard against the entire `slowapi` class of breakage
  2. `ruff` (add `[tool.ruff]` to `pyproject.toml`)
  3. `pytest` (the CI Postgres service runs as a superuser, so the local `CREATEDB` problem doesn't apply)
  4. `python manage.py makemigrations --check --dry-run`
  5. `python manage.py check --deploy`
  6. `cd frontend && npm ci && tsc --noEmit && npm run build`
- Rewrite `README.md`: it currently advertises HTMX (deleted), Elasticsearch and Celery (deleted), calls Redis a cache (it is required), never mentions `docker compose`, and omits the seed step. Add a seed fixture with three boards so a fresh deploy is not an empty home page.

---

## Deletion ledger

Everything below is verified unreferenced or superseded. Roughly **2,000 LOC, 432 KB of vendored assets, 4 services, 7 Python packages, 4 npm packages.**

**Delete outright**
- `templates/` (15 files, 381 LOC) · `static/` (jQuery 88 KB + Bootstrap 308 KB + 3 project files) · `boards/views.py` · `boards/urls.py` · `boards/forms.py` · `boards/templatetags/` · `accounts/views.py` · `accounts/forms.py` · `hash_out/asgi.py` (unused — `wsgi` is the entrypoint) · `notifications/views.py` + `notifications/tests.py` + `accounts/admin.py` + `notifications/admin.py` (empty scaffolds)
- ~~`api/__init__.py:5-47` (stale duplicate app)~~ ✅ `b97e10c` · `api/deps.py:19-32` + 10 `invalidate_cache()` calls · `api/auth.py:11,22` (unused `CryptContext`) + `:105-112` (`get_optional_user`) · `api/routers/topics.py:117-153` + `api/routers/posts.py:101-142` (HTMX fragments) · `api/tasks.py:7-30,101-107` (ES tasks)
- `boards/documents.py` + the ES config · `hash_out/celery.py` + the Celery config · `cms/models.py:15-70` (template-less Page models)
- `accounts/tests/` + `boards/tests/test_views.py` + `boards/tests/test_templatetags.py` — 497 LOC testing only deleted code. **Replace before deleting** (Phase 1 prerequisite 3).
- `frontend/public/{next,vercel,file,globe,window}.svg` · dead imports: `api/main.py:18` (`os` twice), ~~`topics.py:4`~~ ✅, `topics.py:12`, `posts.py:12`, `notifications.py:5,11`, `search.py:4`, ~~`content.py:10`~~ ✅, `deps.py:6,10`, `cms/models.py:10`, ~~`docker-compose.yml:2` (obsolete `version:`)~~ ✅

**Untrack (keep on disk)** — ~~`.env`, `db.sqlite3`, 67 `__pycache__` entries~~ ✅ Phase 0 · still to do: `frontend/public/sw.js`, `frontend/public/workbox-*.js`

**Drop from requirements.txt** — `elasticsearch`, `django-elasticsearch-dsl`, `celery[redis]`, `django-widget-tweaks`, `django-cors-headers`, `passlib[bcrypt]`, `httpx` (→ `requirements-dev.txt`), and `wagtail` **only if** the CMS console goes too.

**Drop from package.json** — `htmx.org` (zero imports), `@ducanh2912/next-pwa` (can never regenerate under Turbopack), `tailwindcss` + `@tailwindcss/postcss` (imported, zero classes used)

**Keep despite zero import hits** — `Pillow` (needed by Wagtail images and the upload verify), `psycopg2-binary` (the DB driver, loaded by name), `python-multipart` (FastAPI `UploadFile`), `taggit` + `modelcluster` (Wagtail internals). Add a one-line comment next to each so the next sweep doesn't delete them.

**Deliberately keep**
- `Topic.slug` — currently written and never read, but it is the right URL shape later. If you truly want it gone, also remove `topics.py:22` and `schemas.py:57` or every topic response breaks.
- FastAPI *and* Django as two processes. They share one settings module, one ORM, one migration graph and one `User` table — it is one application with two entrypoints, not a service boundary. Porting 1,683 LOC to DRF buys architectural tidiness and nothing a user can see.

---

## Sequencing summary

```
Phase 0  ½ d   boot + hygiene        ✅ done 2026-09-17
Phase 1  1-2 d one UI stack          ← needs 3 prerequisites first
Phase 2  2-3 d auth + is_active      ← the real security hole
Phase 3  1-2 d visible bug sweep     ← independent of 4-7, can interleave
Phase 4  1-2 d 6 services → 3
Phase 5  2-3 d server components + contract + perf
Phase 6  3-5 d complete the product
Phase 7  2-3 d production + CI
                                     ≈ 3 weeks solo to a deployable, complete v1
```

**Want a v1 deployed this week instead?** Phases 1 → 4 → 7 (skip 2, 3, 5, 6) gets a working, honest forum up in ~3½ days with search, uploads, notifications and `/admin/` moderation. Then 2 and 3 before it is public, and 5–6 after.

**Hard ordering constraints**
1. ~~Phase 0 before anything — the API does not import, so nothing else is verifiable.~~ ✅ Satisfied.
2. Password validation + change-password endpoint + replacement tests **before** deleting the Django UI (Phase 1) — it is currently the only path for all three.
3. ~~`api/__init__.py` truncation before any Celery/tasks work — importing `api.tasks` otherwise drags in a second `django.setup()`.~~ ✅ Satisfied (`b97e10c`).
4. Fix `migration 0003` before any deployment has more than one board.
5. Fix `api/schemas.py` before generating TypeScript types.
6. Fix the N+1 queries before adding indexes — they cut far more latency, and the indexes are easier to pick once the query shapes are final.
7. Client-fetch consolidation before the httpOnly-cookie switch — nine call sites bypass `lib/api.ts` today and would silently keep working with no credentials.
8. `CREATEDB` on `boards_user` before Phase 1's replacement tests — without it no database-backed test can run locally.

---

## Appendix — audit method and confidence

Eight parallel reviewers (api, django, frontend, security, removal, infra, completeness, coherence), each reading every file in its dimension; then one adversarial verifier per dimension re-opened every cited file and re-graded. 199 findings stood, 25 with corrected actions, 0 withdrawn — and 30 additional findings came from the verifiers themselves.

**Treat with care:** a 0-withdrawal rate means the verify pass was better at correcting than at killing. The claims I re-checked by hand and can vouch for directly: the missing `slowapi` declaration, the absent `Topic.tags` (`AttributeError` reproduced on a model instance), the duplicate app in `api/__init__.py`, the broken `content.py` internal call, the `.env`/`db.sqlite3` tracking with no `.gitignore`, the placeholder (not live) secret values, the 0-row committed database, the hardcoded working `FERNET_KEY`, the unauthenticated `boards/views.py` write path, the absent websocket-token guard, and the Elasticsearch 401 that blocks every write (reproduced via `Board.objects.create`).

**Executed against the real environment** (venv at `/home/akhil/code/test/myproject/venv`): `import api.main` (44 routes); `makemigrations --check --dry-run` (clean); after Phase 0, `pytest` (7 passed), the endpoint smoke test (health, trending, topic, similar, boards, search, `/auth/me` — all 200), the AI endpoints (503 with no key, 502 upstream, 404 unknown topic), the startup check in all three cases (`DEBUG=False` on dev keys refuses to start; real keys start; `DEBUG=True` starts), and `docker compose config`. **Not executed:** migration replay from zero (the `0003` slug defect is read from source), any `docker compose up`, and any production build — verify those as you reach them.
