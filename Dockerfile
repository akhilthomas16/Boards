# Backend image: runs the Django admin (gunicorn) or the API (gunicorn + uvicorn workers).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# No build toolchain: psycopg2-binary, Pillow and cryptography all ship manylinux wheels.
COPY requirements.txt requirements.lock ./
RUN pip install --require-hashes --no-deps -r requirements.lock

COPY . .

# collectstatic needs a settings module that imports; the values here are only used for this step.
RUN DEBUG=True SECRET_KEY=build-only python manage.py collectstatic --noinput

# The media directory is a named volume: a fresh volume inherits the ownership it has here, so it
# must exist and belong to the app user before the volume is created.
RUN mkdir -p /app/media/uploads /app/media/avatars \
    && useradd --uid 10001 --create-home app \
    && chown -R app:app /app
USER app

EXPOSE 8000 8001

# Django admin by default; the API service overrides this with the uvicorn worker class.
CMD ["gunicorn", "hash_out.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
