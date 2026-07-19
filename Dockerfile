# MEATZE Campus — application image (serves web/gunicorn, ws/daphne and worker roles)
# Python 3.13 to match the original virtualenv.
FROM python:3.13-slim

# ---- Build-time options ----------------------------------------------------
# Set to "1" to install Chromium for the docx->pdf preview (Playwright) feature.
# Default 0 keeps the image ~400MB smaller. Enable with:
#   docker build --build-arg WITH_CHROMIUM=1 .
ARG WITH_CHROMIUM=0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=meatze_site.settings

# ---- System dependencies ---------------------------------------------------
# libpq5 for psycopg2 runtime, curl for healthchecks, plus fonts/libs used by
# python-docx / docxtpl / pillow rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        fonts-dejavu-core \
        libreoffice-writer \
        libjpeg62-turbo \
        zlib1g \
    && if [ "$WITH_CHROMIUM" = "1" ]; then \
         apt-get install -y --no-install-recommends chromium; \
       fi \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Python dependencies (cached layer) ------------------------------------
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# ---- Application code -------------------------------------------------------
COPY . /app

# docx template logos are template assets (NOT personal data); ship them so
# MEDIA_ROOT can be seeded on first boot even with an empty media volume.
# (deploy/assets/*.png are copied here by the repo.)

# entrypoint dispatches by the ROLE env var (web | ws | worker)
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PLAYWRIGHT_BIN=/usr/bin/chromium

EXPOSE 8000 8011
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["web"]
