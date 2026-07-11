#!/usr/bin/env sh
# MEATZE Campus container entrypoint.
# Role is passed as the first argument (default "web"): web | ws | worker | <raw cmd>
set -e

ROLE="${1:-web}"

APP_DIR=/app
MEDIA_ROOT="${MEDIA_ROOT:-/app/files}"

wait_for() {
    host="$1"; port="$2"; name="$3"
    if [ -z "$host" ]; then return 0; fi
    echo "[entrypoint] waiting for $name at $host:$port ..."
    i=0
    while ! python -c "import socket,sys; s=socket.socket(); s.settimeout(2)
try:
    s.connect(('$host', int('$port'))); s.close()
except Exception: sys.exit(1)" 2>/dev/null; do
        i=$((i+1))
        if [ "$i" -ge 60 ]; then
            echo "[entrypoint] ERROR: $name not reachable after 60 tries"; exit 1
        fi
        sleep 2
    done
    echo "[entrypoint] $name is up."
}

seed_media_assets() {
    # docx template logos are template assets, not user data. Seed them into
    # MEDIA_ROOT so docx export works even on a fresh (empty) media volume.
    mkdir -p "$MEDIA_ROOT"
    for f in lanbide.png euskadi.png eu.png; do
        if [ ! -f "$MEDIA_ROOT/$f" ] && [ -f "$APP_DIR/deploy/assets/$f" ]; then
            cp "$APP_DIR/deploy/assets/$f" "$MEDIA_ROOT/$f"
            echo "[entrypoint] seeded media asset: $f"
        fi
    done
}

wait_for "${DB_HOST:-db}" "${DB_PORT:-5432}" "postgres"

case "$ROLE" in
    web)
        seed_media_assets
        echo "[entrypoint] running migrations ..."
        python manage.py migrate --noinput
        echo "[entrypoint] collecting static ..."
        python manage.py collectstatic --noinput
        exec gunicorn meatze_site.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers "${GUNICORN_WORKERS:-3}" \
            --timeout "${GUNICORN_TIMEOUT:-120}" \
            --access-logfile - \
            --error-logfile -
        ;;
    ws)
        # Redis is only needed by the ASGI (channels) role.
        wait_for "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "redis"
        exec daphne -b 0.0.0.0 -p 8011 meatze_site.asgi:application
        ;;
    worker)
        # Optional background command. NOTE: the original jitsi_live_watch
        # controls host systemd units and will NOT work as-is in a container.
        # Provide WORKER_CMD to override. Left as a no-op by default.
        if [ -n "$WORKER_CMD" ]; then
            exec sh -c "$WORKER_CMD"
        fi
        echo "[entrypoint] no WORKER_CMD set; worker idle. See deploy/README.md caveats."
        exec tail -f /dev/null
        ;;
    *)
        # Treat the arguments as a raw command (e.g. manage.py shell)
        exec "$@"
        ;;
esac
