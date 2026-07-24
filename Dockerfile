# Single-stage build - no separate compile stage needed since all Python
# dependencies install from prebuilt wheels on this platform (verified locally
# on Python 3.12; matched here for parity with local dev).
FROM python:3.12-slim

# weasyprint (PDF export) binds to system Pango/Cairo/GDK-Pixbuf at runtime -
# these are C libraries, not something pip installs. Missing them causes an
# OSError at import time, not at `pip install` time, so it's easy to miss
# until the export endpoint is actually hit.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install Python deps first so this layer only invalidates when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files are baked into the image at build time; DEBUG must be false here
# purely so STATICFILES_STORAGE resolves to the Whitenoise compressed/manifest
# backend - actual runtime DEBUG comes from the DEBUG env var set on Render.
RUN DEBUG=False SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput

RUN addgroup --system app && adduser --system --ingroup app app && \
    chown -R app:app /app
USER app

EXPOSE 8000

# Must reference $PORT, not a hardcoded port - Render assigns PORT dynamically
# (e.g. 10000) and gunicorn binds to it below. A hardcoded port here would
# silently check a port nothing is listening on and never pass.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health/')" || exit 1

# JSON-array form so Docker doesn't wrap this in its own shell layer; `exec`
# inside still lets ${PORT} expand, but replaces the sh process with gunicorn
# (PID 1) so it receives SIGTERM directly instead of a shell eating it -
# fixes slow/forced container shutdown on `docker stop` / Ctrl+C.
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --access-logfile - --error-logfile -"]
