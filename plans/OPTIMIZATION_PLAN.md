# Hash Out — Optimization & Completion Plan

**Renamed** 2026-09-17 from *Boards* — the Django project package is now `hash_out/`; the `boards` app keeps its name (it holds boards, topics and posts).
**Status:** Phases 0–2 ✅ merged (PR #5, #6, #7). Phase 3 ✅ done on `feat/phase-3-bug-sweep` — uploads are validated by content, pagination/replies/reactions behave, the notification socket survives restarts and notices disconnects. **Next: Phase 4.**
**Audit basis:** 8-dimension review of every tracked source file, 199 findings, each re-verified against the code by a second pass (25 corrected, 0 withdrawn). Spot-checked by hand where the stakes were highest.
**Audited:** 2026-09-16 at `e8b0d45` · **Updated:** 2026-09-17 after Phase 3. Line numbers cite the audited commit; files touched in Phase 0 have shifted.

---

## 0. Executive summary

| | |
|---|---|
| Python (project) | 3,528 LOC |
| TypeScript/React | 2,694 LOC |
| FastAPI layer | 1,683 LOC, 25 endpoints |
| Django templates + vendored static | 381 LOC + 432 KB |
| Tests | ~~497 LOC legacy, all of it testing code this plan deletes~~ ✅ deleted in Phase 1 · 21 tests now (7 DB-free, 14 HTTP auth tests against Postgres) |
| Tracked junk | ~~`.env`, `db.sqlite3` (1 MB), 67 `.pyc` files, no root `.gitignore`~~ ✅ resolved in Phase 0 |
| Services declared | 6 (postgres, redis, elasticsearch, django, fastapi, celery, frontend) |
| Services actually needed | 3 (postgres, redis, + the two app processes) |

**Three findings that matter more than the rest:**

1. ✅ *Fixed in Phase 0 (`9079f33`).* **`slowapi` is imported and not declared.** `api/limiter.py:1` and `api/main.py:15-16` import it; `requirements.txt` never lists it. A clean install or `docker compose up` dies with `ModuleNotFoundError` before serving one request.
2. ✅ *Fixed in Phase 0 (`6f37d32`).* **`Topic.tags` does not exist.** `api/routers/topics.py:31` reads `topic.tags` and `:106` writes it; `boards/models.py:30-49` has no such field and no migration adds one. Every topic endpoint — trending on the home page, topic detail, board topic list, topic creation — raises `AttributeError` → 500.
3. ✅ *Fixed in Phase 1.* **The project carries three UI stacks and pays for all three.** Django templates + a rumour of HTMX + Next.js. Only Next.js works. The Django forum views are still routed and one of them (`boards/views.py:14-32`) is an **unauthenticated POST that creates topics attributed to `User.objects.first()`** — usually the superuser.

**The target architecture** — all three independently-written roadmaps converged on it:

> Next.js is the only thing that serves HTML. FastAPI is the only thing that serves JSON. Django is a library (ORM + auth hashers + migrations) plus `/admin/` as the moderation console.

Getting there is mostly deletion. Roughly 2,000 lines and 4 services leave; about 400 lines of genuinely new code arrive (moderation endpoints, mention parsing, a settings page, tests).

### Corrections to the alarming-sounding parts

I checked these myself rather than pass them on:

- **The committed `.env` holds placeholders**, not live secrets: `django-insecure-change-me-in-production-503-92o4`, `change-me-jwt-secret-key-in-production`, `your-openai-api-key-here`, dev Postgres creds. 
- **The committed `db.sqlite3` contains 0 users** (`select count(*) from auth_user` → 0), so no password hashes leaked.
- Therefore this is **not a credential emergency**. It is a real defect for two reasons: the tracked `.env` means the *next* real key gets committed automatically, and `hash_out/settings.py:21` hardcodes a **working Fernet key** as its default — which makes the CMS "encrypted secret" feature decryptable by anyone with the repo. That one is a genuine broken control.
- **The venv is one level up**, at `/home/akhil/code/test/hash_out/venv` (Python 3.12.5). It already had `slowapi 0.1.9` installed, which is why the missing declaration never showed locally. Bare `python` on this machine resolves to an unrelated project's venv — call the interpreter by full path.
- **The migration graph is clean.** `manage.py makemigrations --check --dry-run` → `No changes detected`, against a `boards_db` with 61 tables and all migrations applied. The `pending migrations` commit message (`d9f6ecf`) is stale — ignore it. (`Topic.tags` is consistently absent from model *and* database, which is exactly why the API 500s.)
- ✅ *Resolved in Phase 0 (`658b21b`).* **Every write used to fail on this machine:** `Board.objects.create(...)` raised `AuthenticationException(401)`. The local Elasticsearch 8.19 requires auth, `settings.py` supplies none, and `django-elasticsearch-dsl`'s default `RealTimeSignalProcessor` bulk-indexed inside every save.
- ✅ *Granted 2026-09-17.* **`boards_user` had no `CREATEDB` privilege.** Django's test runner and `pytest-django` both need to create `test_boards_db`, so no database-backed test can run until a Postgres superuser runs `ALTER ROLE boards_user CREATEDB;`. This blocks Phase 1's replacement tests.
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

## Phase 1 — One UI stack: delete the Django SSR forum, HTMX and Wagtail ✅ Done

**Completed 2026-09-17** on `feat/phase-1-one-ui-stack`. 1,564 lines deleted, 265 added, across 72 files.

| Commit | What landed |
|---|---|
| `feat(api): enforce password validators, add change-password endpoint and auth tests` | `check_password_strength()` runs `AUTH_PASSWORD_VALIDATORS` on signup and reset-password (replaces the ad-hoc `len < 8`), 400 with every failed rule joined into `detail`. `POST /api/auth/change-password` (old + new, `get_current_user`, `5/minute`). Unused passlib `CryptContext` removed. `api/tests/test_auth.py`: 14 tests over `TestClient` — signup, duplicate username/email, 4 weak passwords, token pair shape, wrong password, refresh rejects an access token, `/me` rejects a refresh token and an unknown user, identical forgot-password message, reset and change-password run the validators |
| `refactor(api): remove HTMX fragment endpoints` | `POST /api/topics/board/{id}/htmx` and `POST /api/posts/topic/{id}/htmx` gone with their `HTMLResponse` imports. 43 routes |
| `refactor: delete Django template UI and Wagtail, make /admin/ the moderation console` | `templates/`, `static/`, board/account views, forms, urls, template tags and their test suites, `hash_out/asgi.py`, `cms/wagtail_hooks.py`. Django routes only `/admin/`. Settings lose Wagtail (13 apps, middleware, config), `corsheaders`, `widget_tweaks`, `STATICFILES_DIRS`, `LOGIN_*`. `cms` keeps only `SiteSetting`, registered in `/admin/` with the secret-masking form; `cms/migrations/0001` rewritten without the page models or the `wagtailcore` dependency. `/admin/` registers `Topic` (pin/lock editable in the list), `Post`, `Reaction`, `Notification`. Requirements drop `wagtail`, `django-cors-headers`, `django-widget-tweaks`, `passlib`; `httpx` → `requirements-dev.txt` |
| `chore(frontend): drop htmx.org, starter svgs, generated service worker and missing icons` | `npm uninstall htmx.org`; 5 starter SVGs deleted; `sw.js`/`workbox-*.js` untracked and gitignored; the `icons` array (two 404s) removed from `manifest.json`; HTMX comments fixed |

### Where it departed from the original plan

- **Wagtail went entirely**, not just the page models (decided 2026-09-17). Nothing outside the Wagtail dashboard read `SiteSetting`, the table had 0 rows, and the 4 pages rendered nowhere. Dropping it also removed the `mark_safe` XSS in `wagtail_hooks.py` (Phase 3) and ~20 transitive packages.
- **`cms/migrations/0001_initial.py` was rewritten, not followed by a `DeleteModel` migration.** A `DeleteModel` still needs `wagtailcore` installed to load `0001`. Safe because no populated deployment exists. The recorded migration name is unchanged, so existing databases need no `--fake`.
- **`Notification` is registered in `notifications/admin.py`**, which was filled in rather than deleted. `accounts/admin.py` was deleted as planned; `UserProfile` is not registered.
- **`TEMPLATES['DIRS']` emptied and `LOGIN_URL`/`LOGIN_REDIRECT_URL`/`LOGOUT_REDIRECT_URL` removed** — they named templates and URL names that no longer exist. `TEMPLATES` itself stays for the admin.
- **The auth tests use `django_db(transaction=True)`.** `TestClient` runs sync endpoints in worker threads with their own connections, which can't see rows inside a test-wrapping transaction. They also swap in `LocMemCache` and disable the rate limiter.
- **Change-password does not revoke existing JWTs** — tokens stay valid until they expire. Filed under Phase 2's `jti` work.

### Local environment changes (not in git)

- **Database:** 44 tables dropped (`wagtail*`, `taggit*`, the 4 `cms_*page` tables), 198 `django_migrations` rows and the stale content types removed. Backed up first with `pg_dump -Fc` (session scratchpad, `wagtail-tables-backup.dump`). **Other clones:** run the same cleanup, or recreate the database and `migrate`.
- **venv:** `wagtail`, `django-taggit`, `django-modelcluster`, `django-cors-headers`, `django-widget-tweaks`, `passlib` and their now-orphaned dependencies uninstalled; `pip install --dry-run -r requirements-dev.txt` installs nothing and `pip check` is clean.
- **`.env`:** `WAGTAIL_SITE_NAME` is now unused; delete it.

### Exit criteria

```
grep -rn 'render(' --include='*.py' .                  ✅ empty (wagtail_hooks.py deleted too)
git ls-files | grep -E '^templates/|^static/'           ✅ empty
git grep -i 'wagtail|htmx|corsheaders|passlib'          ✅ empty outside plans/
pytest                                                  ✅ 21 passed
manage.py check · makemigrations --check · migrate --check   ✅ clean
python -c "import api.main"                             ✅ 43 routes
/admin/ as superuser: index, Topic, Post, Reaction, Notification, SiteSetting   ✅ 200
SiteSetting secret via /admin/: encrypted at rest, masked in form, untouched mask keeps value   ✅
/ · /login/ · /signup/ · /cms-admin/ · /pages/          ✅ 404
API smoke: health, boards, trending, topic, board topics, search   ✅ 200
tsc --noEmit · manifest.json · docker compose config    ✅
```

---

## Phase 2 — One auth system, and a ban that actually bans ✅ Done

**Completed 2026-09-17** on `feat/phase-2-auth`. 508 lines added, 405 deleted, across 19 files.

| Commit | What landed |
|---|---|
| `feat(api): back rate limits with redis` | `Limiter(storage_uri=settings.REDIS_URL)` — limits survive restarts and apply across workers |
| `feat(auth): httpOnly cookie sessions with rotation, revocation and is_active checks` | **Cookies:** `/token` sets `access_token` (`Path=/api`) and `refresh_token` (`Path=/api/auth`), both `HttpOnly`, `SameSite=Lax`, `Secure` unless `DEBUG`; no token ever appears in a response body. New `POST /api/auth/logout`. **Identity:** tokens resolve by `user_id` with `is_active=True`; login uses `authenticate()` (rejects inactive users, constant-time for unknown usernames). **Revocation:** a `pwd` claim (first 16 chars of `get_session_auth_hash()`) kills every token on password change or reset; `fam`/`jti` claims + Redis give single-use refresh tokens, and a replay after a 30 s grace window revokes the family. **OTP:** `secrets`, `{otp, user_id}` in Redis, atomic `cache.incr` attempt counter, `hmac.compare_digest`, burned after 5 wrong guesses, email sent via `BackgroundTasks` calling the task function directly. **Signup:** `EmailStr` (`email-validator`), lowercased, case-insensitive uniqueness. **Profiles:** `PublicProfileResponse` (no `email`) on `GET /{username}` and search; search needs `q` ≥ 2 chars, `30/minute`. **WebSocket:** cookie auth and an `Origin` allowlist, both checked before `accept()`. **Frontend:** `lib/api.ts` exports `API_BASE`, `postForm`, `postMultipart`, sends `credentials: 'include'`, and de-duplicates refresh; all nine raw `fetch`/`getTokens` call sites moved onto it; `WebSocketProvider` connects only when logged in and reconnects on login/logout. 36 tests |

### Where it departed from the original plan

- **No Next.js route handlers or same-origin proxy.** FastAPI sets the cookies itself and the browser calls it directly with `credentials: 'include'`. Tested first: a Next rewrite proxies HTTP and even WebSocket upgrades fine, but it **does not add `X-Forwarded-For`** — it only passes through whatever the client sent. Behind it, FastAPI sees one IP for every user (every rate limit becomes global) or trusts a spoofable header. Calling the API directly keeps real client IPs and needs no proxy code. **Constraint this creates:** the frontend and API must be **same-site** (`localhost:3000` → `localhost:8001`, or `app.example.com` → `api.example.com`), or `SameSite=Lax` cookies are never sent. Documented in `env.sample` and `lib/api.ts`.
- **Password-change revocation uses a fingerprint claim, not a per-user generation counter in Redis.** Stateless, and it covers reset-password too. Change-password re-issues cookies for the current session.
- **Refresh reuse has a 30-second grace window.** Without it, two tabs refreshing together would read as token theft and log the user out everywhere. The client also de-duplicates refreshes within a tab.
- **The OTP email is sent from a `BackgroundTasks` job**, not synchronously, so a known email isn't measurably slower than an unknown one (the plan's synchronous call would have been a timing oracle for account enumeration). Celery's config is untouched until Phase 4.
- **`constr(min_length=8)` skipped:** `MinimumLengthValidator` already enforces it through `check_password_strength`.
- **WebSocket `Origin` check added** (not in the plan) — cookie-authenticated sockets are otherwise open to cross-site WebSocket hijacking from same-site origins. `CORS_ALLOWED_ORIGINS` moved back into `settings.py` as the one source for CORS and this check.
- **`get_optional_user` deleted now** (planned for Phase 6) — it depended on the removed `OAuth2PasswordBearer`.
- **`/verify-otp` counts as a guess** toward the 5-attempt limit.
- **Also done early from Phase 3:** `PostCard` reactions gated on `useAuth().user` (rollback still open); `WebSocketProvider` depends on `user` and skips anonymous visitors (backoff reconnect still open); `notifications.py` no longer has the `channel_name` `NameError` (disconnect detection and `print` → `logging` still open).

### Known ceilings

- **Anonymous visitors cost two requests per page load** (`/me` 401, then `/refresh` 401) — JS can't see whether a refresh cookie exists. A non-httpOnly `logged_in` hint cookie would skip the second one.
- **Auth is checked when the WebSocket connects**, not during the connection. A user deactivated mid-connection keeps receiving their own notifications until it reconnects.
- **Swagger's "Authorize" button no longer applies.** Use "Try it out" on `POST /api/auth/token` at `:8001/docs`; the cookie then rides along on later calls.
- **Rate limits key on the socket peer.** Behind a reverse proxy (Phase 7), run uvicorn with `--forwarded-allow-ips` set to the proxy.

### Exit criteria

```
is_active=False → 401 on /me, /token, /refresh; WebSocket rejected     ✅ tests + real browser
reused refresh token rejected, family revoked (and grace-window race not)  ✅ tests
5 wrong OTPs burn the code                                              ✅ tests
grep -rn 'localStorage\|Bearer ' frontend/src                           ✅ empty
anonymous GET /api/profiles/<username> has no email                     ✅ tests
pytest                                                                  ✅ 36 passed
mutation check: removing is_active, family revocation, Origin check, public schema,
  OTP attempt limit or pwd fingerprint each fails a test                ✅ 6/6 caught
headless Chrome against next dev + uvicorn: login sets httpOnly cookies, nothing in
  localStorage/document.cookie, socket opens without ?token= and receives a notification,
  reload keeps the session, deleted access cookie → silent refresh with rotation,
  UI logout clears cookies, deactivated user shown logged out and refused login   ✅
manage.py check · makemigrations --check · tsc --noEmit · docker compose config · pip check   ✅
```

---

## Phase 3 — Fix what a user hits in the first ten minutes ✅ Done

**Completed 2026-09-17** on `feat/phase-3-bug-sweep`.

| Commit | What landed |
|---|---|
| `fix(api): validate uploads by image content and harden /media` | `read_image()` in `upload.py`, shared by post images and avatars: size cap, `Image.open().verify()`, extension from **Pillow's detected format** — client filename and Content-Type are ignored. Avatars get a UUID name (no client filename, no stale browser cache). `/media` is a `StaticFiles` subclass adding `X-Content-Type-Options: nosniff` and `Content-Security-Policy: default-src 'none'; sandbox`, and serving anything that isn't JPEG/PNG/GIF/WEBP as `application/octet-stream`. Profile `website` must be `http(s)://`. Shared API test fixtures in `api/tests/conftest.py` |
| `fix(boards): bump topics on reply, atomic counters, safe slug migration` | `post_save` receiver on new `Post` → `Topic…update(last_updated=now)`. `views_count` and `reputation_score` via `F()` (`Greatest(…, 0)` on removal). No reputation for reacting to your own post; `emoji: Literal["👍", "❤️"]`. Migration `0003` adds `Board.slug` nullable and unindexed → `RunPython` backfill with `-<pk>` on collision → `AlterField(unique=True)`. `boards/tests.py` joins `testpaths` |
| `fix(api): release notification subscriptions when the socket closes` | `asyncio.wait` over the Redis forwarder and a `receive()` loop — whichever ends first cancels the other, then unsubscribe and close. Failures logged, not printed. Redis URL from `settings.REDIS_URL` (router and `notifications/models.py`) |
| `fix(frontend): pagination, quotes, reactions, socket reconnect, media rewrite, a11y` | Board page effect depends on `page` (pagination was dead); board and topic pages ignore stale responses. Quote reply splits on a real newline. Failed reactions roll back. `WebSocketProvider` reconnects with 1 s → 30 s backoff and stops on logout; the unreachable desktop-notification branch is deleted. `/media/:path*` rewrite to the API (`API_INTERNAL_URL`, set to `http://fastapi:8001` in compose) — uploaded images and avatars load from the app origin. Navbar: `/settings` link removed, `aria-expanded`/`aria-haspopup`, Escape and outside click close every menu. `id`/`htmlFor` on the new-topic and profile forms, `aria-label` on the reply editor |

### Where it departed from the original plan

- **Uploads trust Pillow, not the client.** The plan mapped the (client-sent) Content-Type to an extension and added `verify()`; the format Pillow detects is the one fact the client can't spoof, so that alone picks the extension.
- **`/media` also gets a sandboxing CSP and an octet-stream fallback**, so a non-image that already sits in `media/` (from before this phase) downloads instead of rendering.
- **The edge body-size limit is not done** — there is no reverse proxy in the repo yet. Filed under Phase 7.
- **Migration `0003`'s interim column is also `db_index=False`.** Otherwise a fresh database creates the `_like` index twice and `migrate` fails. Existing databases keep the unique constraint name `boards_board_slug_key`; fresh ones get `boards_board_slug_f5548cf1_uniq`. Django finds constraints by introspection, so later migrations work on both.
- **Only a new post bumps its topic**, not an edit.
- **The emoji whitelist is exactly what `PostCard` offers** (👍 ❤️); the database had no other reactions. Widen both together.
- **The board page doesn't `setLoading(true)` on page change** (React's `set-state-in-effect` lint rule forbids it); it keeps showing the previous page until the next one arrives, and a stale-response guard stops out-of-order responses.
- **Desktop notifications were deleted**, not wired to `requestPermission()`.
- **Added:** profile `website` must be an `http(s)` URL. It renders as a link, so `javascript:` there was stored XSS (React 19 happens to block it at render; now the API refuses it).
- **The socket disconnect test runs a real uvicorn server.** Starlette's `TestClient` cancels the handler when the test closes the socket, which hid the bug (checked: the old loop passes under `TestClient`).
- **The manual pass is an automated headless-Chrome run** (below), not a checklist.
- **Environment note:** a stale `frontend/.next` made Turbopack fail with `Can't resolve 'tailwindcss' in '…/hash_out/hash_out'` and hang every page. `rm -rf frontend/.next` fixes it.

### Exit criteria

```
pytest                                                              ✅ 55 passed
mutation check — each fix removed in turn fails a test:
  Pillow format check, nosniff, octet-stream fallback, self-reaction guard,
  reputation floor, F() view counter (40 concurrent GETs), reply bump,
  website validation, migration 0003 backfill, socket disconnect      ✅ 10/10 caught
fresh-DB migrate vs existing DB: boards_board indexes                ✅ same (constraint name differs, see above)
headless Chrome against next dev + uvicorn, seeded 25-topic board:
  page 2 shows 5 different topics                                    ✅
  labels find Subject/Tags/Message                                   ✅
  menus: aria-expanded, Escape, outside click; no Settings link      ✅
  quote keeps "> line one\n> line two"                               ✅
  evil.html with image/png refused; real PNG renders from :3000/media, nosniff   ✅
  reply moves the oldest topic to the top of page 1                  ✅
  reaction: forced 500 rolls back, real one persists, author +1 reputation       ✅
  avatar renders from /media/avatars/<uuid>.png                      ✅
  API killed and restarted: socket reconnects and receives a notification        ✅
  no uncaught page errors                                            ✅
manage.py check · makemigrations --check · tsc --noEmit · docker compose config · pip check   ✅
```

---

## Phase 4 — Six services → three (1–2 days)

Both heavy services are either dead or actively harmful.

**Elasticsearch — delete it.** `boards/documents.py:9,23,40` register three documents with the default `RealTimeSignalProcessor`, which made **every Board/Topic/Post write depend on Elasticsearch being up**. Phase 0 turned autosync off, so the index is now stale by design and search already leans on the ORM fallback (`3e05a4d`) — Elasticsearch carries no weight at all. The search path also has real bugs: `search.py:80` links post hits to `/topics/<post_id>` (the *post's* pk — every post result navigates somewhere unrelated), and `_search_orm`'s `total` is computed from different sets than the ones it slices, with a `|` union that yields duplicates.
- `git rm boards/documents.py`; delete `_search_elasticsearch` and the try/except at `search.py:23-29`; remove `django_elasticsearch_dsl` from `INSTALLED_APPS`, the `ELASTICSEARCH_DSL` block and `ELASTICSEARCH_DSL_AUTOSYNC` (`settings.py:139-149`), and both keys from `env.sample`; drop `elasticsearch`/`django-elasticsearch-dsl` from requirements; remove the service, the `es_data` volume and the three `ELASTICSEARCH_URL` lines from compose; delete `api/tasks.py:7-30` and `:101-107`.
- Rewrite `_search_orm` as the only path: one combined result list, `total` from the same filtered sets that get sliced, `type` as a `Literal['all','board','topic','post']`, correct per-type totals.
- *If you want real search later:* Postgres full-text (`SearchVector` + a GIN index) costs no new service.

**Celery — delete it.** Nothing enqueues a task any more: Phase 2 replaced the one `.delay()` call (a silent no-op — the task was never registered) with a direct call.
- ~~`api/auth.py:208` → call `send_otp_email` directly~~ ✅ Phase 2 (from `BackgroundTasks`). Move `send_otp_email` out of `api/tasks.py` into a plain function when the rest of that file goes.
- Delete `hash_out/celery.py`, `hash_out/__init__.py:6-8`, the `CELERY_*` block (`settings.py:147-156`), `celery[redis]`, and the worker service.
- Add the email settings the OTP path has always assumed: `DEFAULT_FROM_EMAIL` (currently unset while `tasks.py` passes `from_email=None`), `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`. Document them in `env.sample` — Phase 0 deliberately left them out because nothing read them yet.
- *Bring Celery back when* a task is genuinely slow and nobody is waiting on it (digest emails, bulk reindex). Not for one OTP.

**Redis stays, and the README should say so.** It is not an optional cache: it holds sessions (`SESSION_ENGINE = cache`), the OTP store, the rate-limit counters (once `storage_uri` is set) and the notification pub/sub. Add a `LocMemCache` branch for when `REDIS_URL` is absent so tests can run without it.

**Delete the dead cache layer.** `api/deps.py:19-32` defines a `cached` decorator that is **never applied to anything** (and is `async`, incompatible with every sync handler in the codebase), so all **ten** `invalidate_cache()` calls — `topics.py:113,142`, `boards.py:66,85,102`, `posts.py:97,132,164,183,236` — clear namespaces nothing ever writes. Delete the decorator, all ten call sites, and the imports they leave behind (`json`, `wraps`, `Optional`, `settings` in `deps.py`; keep `paginate`).

**Exit criteria:** `docker compose up` starts exactly postgres, redis, fastapi, frontend (django on demand); `grep -rin 'elasticsearch\|celery' --include='*.py' --include='*.txt' --include='*.yml' .` is empty; search returns correct totals and post hits link to their topic.

---

## Phase 5 — One rendering model, one API contract (2–3 days)

- **Three route pages are 100% client components** (`boards/[id]`, `topics/[id]`, `profile/[username]`) that ship a spinner as their HTML, double-fetch data their server `layout.tsx` already fetched, and call `useSearchParams()` with no `Suspense` boundary — which bails the whole route out of prerendering. Convert them to async server components reading `params`/`searchParams` with `next: { revalidate: 60 }`, mirroring `app/page.tsx:37-57`, and extract client islands (`<NewTopicForm boardId>`, `<ReplyForm topicId>`, `<ProfileEditForm>`). This conversion is also what fixes the dead pagination and the splice-into-current-page bugs structurally rather than one at a time.
- **SSR-in-Docker:** server components fetch from *inside* the frontend container, where `NEXT_PUBLIC_API_URL=http://localhost:8001` (compose `:131`) points at the container's own loopback. Use the server-side `API_INTERNAL_URL` (added to compose in Phase 3 for the `/media` rewrite) for those fetches too.
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
| **Settings page** | `/api/profiles/me` and `POST /api/auth/change-password` | No page (the dead Navbar link was removed in Phase 3). Build `app/settings/page.tsx` and link it from the user menu again |
| **Email verification** | Nothing | Accounts are live on first POST. Either add it (`is_active=False` + `verify:{email}` code + `POST /api/auth/verify-email`) or decide explicitly not to and document it |
| **Profile display** | `reputation_score`, `badges` returned | Never rendered |
| **AdSense** | `AdBanner` reads 4 env vars, documented in `frontend/env.sample` (Phase 0) | Unset values still render a visible "AdSense Slot: …" placeholder. Real account → set them; no account → delete `AdBanner` |

Note: ~~`get_optional_user`~~ ✅ deleted in Phase 2. Where optional auth is genuinely needed (reactions, public profiles), depend on `access_cookie` (already `auto_error=False`) and return `None` instead of raising.

---

## Phase 7 — Production shape and CI (2–3 days)

**Nothing in this repo can currently be deployed:** compose runs `runserver` and `uvicorn --reload`, the backend `Dockerfile` has no `CMD` and no `collectstatic`, the frontend `Dockerfile` ships `next dev`, both containers run as root, and there is no gunicorn, no whitenoise, and no CI at all.

- **Reverse proxy:** cap request bodies (`client_max_body_size 6m`) — uploads are spooled in full before the 5 MB check (from Phase 3). Run uvicorn with `--forwarded-allow-ips` set to the proxy so rate limits see client IPs (from Phase 2).
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
- ✅ *Phase 1:* ~~`templates/` · `static/` · `boards/views.py` · `boards/urls.py` · `boards/forms.py` · `boards/templatetags/` · `accounts/views.py` · `accounts/forms.py` · `hash_out/asgi.py` · `notifications/views.py` + `notifications/tests.py` + `accounts/admin.py`~~ (`notifications/admin.py` now registers `Notification`)
- ~~`api/__init__.py:5-47` (stale duplicate app)~~ ✅ `b97e10c` · `api/deps.py:19-32` + 10 `invalidate_cache()` calls · ~~`api/auth.py:11,22` (unused `CryptContext`)~~ ✅ + ~~`:105-112` (`get_optional_user`)~~ ✅ Phase 2 · ~~`api/routers/topics.py:117-153` + `api/routers/posts.py:101-142` (HTMX fragments)~~ ✅ · `api/tasks.py:7-30,101-107` (ES tasks)
- `boards/documents.py` + the ES config · `hash_out/celery.py` + the Celery config · ~~`cms/models.py:15-70` (template-less Page models)~~ ✅ with all of Wagtail
- ~~`accounts/tests/` + `boards/tests/` — 497 LOC testing only deleted code~~ ✅ replaced by `api/tests/test_auth.py`
- ~~`frontend/public/{next,vercel,file,globe,window}.svg`~~ ✅ · dead imports: `api/main.py:18` (`os` twice), ~~`topics.py:4`~~ ✅, `topics.py:12`, `posts.py:12`, `notifications.py:5,11`, `search.py:4`, ~~`content.py:10`~~ ✅, `deps.py:6,10`, ~~`cms/models.py:10`~~ ✅, ~~`docker-compose.yml:2` (obsolete `version:`)~~ ✅

**Untrack (keep on disk)** — ~~`.env`, `db.sqlite3`, 67 `__pycache__` entries~~ ✅ Phase 0 · ~~`frontend/public/sw.js`, `frontend/public/workbox-*.js`~~ ✅ Phase 1

**Drop from requirements.txt** — `elasticsearch`, `django-elasticsearch-dsl`, `celery[redis]` · ✅ Phase 1: ~~`django-widget-tweaks`, `django-cors-headers`, `passlib[bcrypt]`, `httpx` (→ `requirements-dev.txt`), `wagtail`~~

**Drop from package.json** — ~~`htmx.org`~~ ✅, `@ducanh2912/next-pwa` (can never regenerate under Turbopack), `tailwindcss` + `@tailwindcss/postcss` (imported, zero classes used)

**Keep despite zero import hits** — `Pillow` (`UserProfile.avatar` and the upload verify; commented in `requirements.txt`), `psycopg2-binary` (the DB driver, loaded by name), `python-multipart` (FastAPI `UploadFile`).

**Deliberately keep**
- `Topic.slug` — currently written and never read, but it is the right URL shape later. If you truly want it gone, also remove `topics.py:22` and `schemas.py:57` or every topic response breaks.
- FastAPI *and* Django as two processes. They share one settings module, one ORM, one migration graph and one `User` table — it is one application with two entrypoints, not a service boundary. Porting 1,683 LOC to DRF buys architectural tidiness and nothing a user can see.

---

## Sequencing summary

```
Phase 0  ½ d   boot + hygiene        ✅ done 2026-09-17
Phase 1  1-2 d one UI stack          ✅ done 2026-09-17
Phase 2  2-3 d auth + is_active      ✅ done 2026-09-17
Phase 3  1-2 d visible bug sweep     ✅ done 2026-09-17
Phase 4  1-2 d 6 services → 3
Phase 5  2-3 d server components + contract + perf
Phase 6  3-5 d complete the product
Phase 7  2-3 d production + CI
                                     ≈ 3 weeks solo to a deployable, complete v1
```

**Want a v1 deployed this week instead?** Phases 4 → 7 (skip 5, 6) gets a working, honest forum up in ~2½ days with search, uploads, notifications and `/admin/` moderation. Then 5–6 after.

**Hard ordering constraints**
1. ~~Phase 0 before anything — the API does not import, so nothing else is verifiable.~~ ✅ Satisfied.
2. ~~Password validation + change-password endpoint + replacement tests before deleting the Django UI.~~ ✅ Satisfied in Phase 1.
3. ~~`api/__init__.py` truncation before any Celery/tasks work — importing `api.tasks` otherwise drags in a second `django.setup()`.~~ ✅ Satisfied (`b97e10c`).
4. ~~Fix `migration 0003` before any deployment has more than one board.~~ ✅ Satisfied in Phase 3.
5. Fix `api/schemas.py` before generating TypeScript types.
6. Fix the N+1 queries before adding indexes — they cut far more latency, and the indexes are easier to pick once the query shapes are final.
7. ~~Client-fetch consolidation before the httpOnly-cookie switch.~~ ✅ Satisfied in Phase 2.
8. ~~`CREATEDB` on `boards_user` before Phase 1's replacement tests.~~ ✅ Satisfied.

---

## Appendix — audit method and confidence

Eight parallel reviewers (api, django, frontend, security, removal, infra, completeness, coherence), each reading every file in its dimension; then one adversarial verifier per dimension re-opened every cited file and re-graded. 199 findings stood, 25 with corrected actions, 0 withdrawn — and 30 additional findings came from the verifiers themselves.

**Treat with care:** a 0-withdrawal rate means the verify pass was better at correcting than at killing. The claims I re-checked by hand and can vouch for directly: the missing `slowapi` declaration, the absent `Topic.tags` (`AttributeError` reproduced on a model instance), the duplicate app in `api/__init__.py`, the broken `content.py` internal call, the `.env`/`db.sqlite3` tracking with no `.gitignore`, the placeholder (not live) secret values, the 0-row committed database, the hardcoded working `FERNET_KEY`, the unauthenticated `boards/views.py` write path, the absent websocket-token guard, and the Elasticsearch 401 that blocks every write (reproduced via `Board.objects.create`).

**Executed against the real environment** (venv at `/home/akhil/code/test/hash_out/venv`): `import api.main` (44 routes); `makemigrations --check --dry-run` (clean); after Phase 0, `pytest` (7 passed), the endpoint smoke test (health, trending, topic, similar, boards, search, `/auth/me` — all 200), the AI endpoints (503 with no key, 502 upstream, 404 unknown topic), the startup check in all three cases (`DEBUG=False` on dev keys refuses to start; real keys start; `DEBUG=True` starts), and `docker compose config`. **Not executed:** migration replay from zero (the `0003` slug defect is read from source), any `docker compose up`, and any production build — verify those as you reach them.
