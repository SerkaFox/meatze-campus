# MEATZE Campus — Docker deployment / перенос на другой сервер

Самодостаточный docker-compose стек для MEATZE Campus: `web` (Gunicorn/WSGI),
`ws` (Daphne/ASGI WebSocket), `db` (PostgreSQL 17), `redis`, `nginx`.
Jitsi (видеоконференции) — отдельный стек в `deploy/jitsi/`.

> **Данные не переносятся.** Стек стартует с чистой БД (`migrate`). Личные данные
> (курсы, учителя, ученики, материалы) не копируются. Логотипы docx-шаблонов
> (не личные данные) поставляются в `deploy/assets/` и автоматически кладутся в
> `/app/files` при первом старте.

## Архитектура

| Сервис | Роль | Порт |
|---|---|---|
| `nginx` | reverse proxy, отдаёт статику/медиа | `${HTTP_PORT}` → 80 |
| `web` | Gunicorn `meatze_site.wsgi` | 8000 (внутр.) |
| `ws` | Daphne `meatze_site.asgi`, маршрут `/ws/` | 8011 (внутр.) |
| `db` | PostgreSQL 17 | 5432 (внутр., **не публикуется**) |
| `redis` | channel layer | 6379 (внутр., **не публикуется**) |

Внешние зависимости (через env, НЕ в этом стеке): **Ollama** (`OLLAMA_BASE_URL`),
**Jitsi** (`JITSI_*` + `deploy/jitsi/`), **ComfyUI** (`COMFY_BASE`),
**Gmail SMTP**, **WhatsApp Cloud API**, **Google Drive**.

## Быстрый старт на целевом сервере

```bash
git clone <repo> meatze && cd meatze/deploy
cp .env.docker.example .env
nano .env                 # заполнить секреты и домен (см. ниже)
docker compose up -d --build
docker compose ps
docker compose logs -f web
```

Открыть `http://<сервер>:${HTTP_PORT}/` (по умолчанию 8080). Для продакшена
поставить `HTTP_PORT=80` и терминировать TLS внешним прокси/Certbot.

### Что обязательно поменять в `.env`
- `DJANGO_SECRET_KEY` — сгенерировать новый.
- `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` — домен(ы) нового сервера.
- `SESSION_COOKIE_DOMAIN` / `CSRF_COOKIE_DOMAIN` — домен нового сервера
  (для теста на `localhost` оставить пустыми).
- `DB_PASSWORD`, `MEATZE_ADMIN_PASS` — новые пароли.
- `OLLAMA_BASE_URL` — адрес хоста с Ollama (из контейнера `127.0.0.1` = сам контейнер;
  использовать `host.docker.internal` или LAN-IP сервера).
- `JITSI_DOMAIN` и `JITSI_JWT_*` — под ваш Jitsi.

## Перенос без доступа к интернету на целевом сервере

Собрать образ здесь и перенести tar:

```bash
# на исходном сервере
cd meatze
docker build -t meatze-app:latest .
docker save meatze-app:latest postgres:17 redis:7-alpine nginx:alpine \
  | gzip > meatze-images.tar.gz
# перенести meatze-images.tar.gz + репозиторий на целевой сервер, затем:
docker load < meatze-images.tar.gz
cd deploy && docker compose up -d      # без --build, образы уже загружены
```

## (Опционально) перенос реальных данных

Стек по умолчанию стартует пустым. Если нужно перенести боевые данные:

```bash
# БД: дамп на исходном сервере
pg_dump -h 127.0.0.1 -U meatze_user meatze_db | gzip > meatze_db.sql.gz
# восстановление в контейнер db (после up -d):
gunzip -c meatze_db.sql.gz | docker compose exec -T db psql -U meatze_user -d meatze_db

# Медиа (~18 ГБ): залить в том media
docker run --rm -v meatze_media:/dst -v /path/to/files:/src alpine \
  sh -c "cp -a /src/. /dst/"
```

## Jitsi

```bash
cd deploy/jitsi
cp .env.example .env
# сгенерировать секреты компонентов:
for v in JICOFO_COMPONENT_SECRET JICOFO_AUTH_PASSWORD JVB_AUTH_PASSWORD; do \
  echo "$v=$(openssl rand -hex 16)"; done   # вписать в .env
nano .env      # PUBLIC_URL, DOCKER_HOST_ADDRESS/JVB_ADVERTISE_IPS = публичный IP,
               # LETSENCRYPT_*, JWT_* == Django JITSI_JWT_*
mkdir -p ~/.jitsi-meet-cfg/{web,prosody/config,prosody/prosody-plugins-custom,jicofo,jvb}
docker compose up -d
```

Требуется публичный HTTPS на `PUBLIC_URL` и открытый **UDP 10000**. В Django
выставить `JITSI_DOMAIN` = домен Jitsi, `JITSI_JWT_SECRET/APP_ID/AUD` = значения из
`deploy/jitsi/.env`.

## Caveats

1. **`jitsi_live_watch`** (фоновый воркер, закрывал простаивающие комнаты через
   `systemctl` хоста) в контейнер **не переносится** — systemd хоста недоступен.
   Сервис `worker` в compose по умолчанию отсутствует. При необходимости логику
   надо переписать на управление Jitsi через API и задать `WORKER_CMD`.
2. **TLS** здесь не настроен — терминируйте на целевом сервере (Certbot/внешний LB)
   и проксируйте на `:80` контейнера. Django доверяет `X-Forwarded-Proto`.
3. **Chromium/Playwright** (превью docx→pdf) не ставится по умолчанию. Включить:
   `WITH_CHROMIUM=1` в `.env` (образ станет крупнее на ~400 МБ).
4. **Секреты** в поставку не входят — только `.env*.example`. Реальные значения
   переносите отдельным безопасным каналом.
5. **ComfyUI** (`COMFY_BASE`) остаётся внешним сервисом.
