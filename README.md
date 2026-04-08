# RequestBot — Telegram-бот для автоматизации заявок

Helpdesk-система на базе Telegram. Каждый топик суперегруппы = отдел. Сообщение в топик → заявка в БД. Управление через Telegram Mini App и веб-админку.

## Стек

- **Бот**: Python 3.12, aiogram 3.13
- **БД**: PostgreSQL 16 (self-hosted на Timeweb VDS)
- **ORM**: SQLAlchemy 2 async + Alembic
- **API**: FastAPI + uvicorn
- **AI**: Ollama (llama3/mistral) — бесплатно, локально
- **Деплой**: Docker Compose + Nginx

## Быстрый старт (разработка)

```bash
# 1. Клонировать и установить зависимости
cd bots/request_bot
pip install -r requirements.txt

# 2. Создать .env из примера
cp .env.example .env
# Заполнить BOT_TOKEN, DATABASE_URL и API_SECRET_KEY

# 3. Применить миграции
alembic upgrade head

# 4. Запустить бота (polling режим — без WEBHOOK_BASE_URL)
python -m bot.main

# 5. Запустить API (отдельный терминал)
uvicorn api.main:app --reload --port 8000
```

## Production configuration

Для продакшена используйте разные публичные URL для backend/webhook и Mini App:

```env
WEBHOOK_BASE_URL=https://bot-api.24beershop.ru
MINIAPP_BASE_URL=https://app.24beershop.ru
```

- `WEBHOOK_BASE_URL` используется только для регистрации Telegram webhook.
- `MINIAPP_BASE_URL` используется только для кнопок Web App в сообщениях бота.
- `miniapp/.env` должен указывать `VITE_API_URL=https://bot-api.24beershop.ru`.

## Деплой на Timeweb VDS (`46.19.67.135`)

```bash
# 1. Сделать бэкап перед выкаткой
docker exec request_bot-postgres-1 pg_dump -U requestbot requestbot > /root/requestbot-backup.sql
cp /opt/sites/nginx.conf /opt/sites/nginx.conf.bak
cp /opt/sites/docker-compose.yml /opt/sites/docker-compose.yml.bak

# 2. Клонировать или обновить чистый git checkout
git clone https://github.com/Kuli21232/request_bot.git /opt/request_bot_clean
cd /opt/request_bot_clean
cp .env.example .env

# 3. Заполнить .env реальными значениями и доменами
# WEBHOOK_BASE_URL=https://bot-api.24beershop.ru
# MINIAPP_BASE_URL=https://app.24beershop.ru

# 4. Создать общий network для request_bot и sites-nginx
docker network create sites_shared || true

# 5. Поднять стек с фиксированным compose project name
docker compose up -d --build

# 6. Применить миграции
docker compose exec bot alembic upgrade head

# 7. При необходимости загрузить модель Ollama
docker compose exec ollama ollama pull llama3
```

### Reverse proxy contract

- `bot-api.24beershop.ru/webhook/*` → `request-bot-bot:8080`
- `bot-api.24beershop.ru/*` → `request-bot-api:8000`
- `app.24beershop.ru/*` → `/opt/miniapp/dist`
- `admin.24beershop.ru/*` → `/opt/admin/dist`

Контейнер nginx должен быть подключён к внешней сети `sites_shared`.

### Smoke checks после деплоя

```bash
curl -fsS https://bot-api.24beershop.ru/health
curl -I https://app.24beershop.ru/
curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
docker logs --tail 100 request_bot-bot-1
```

- В `getWebhookInfo` должен появиться URL на `https://bot-api.24beershop.ru/webhook/...`
- В логах бота должен быть `Webhook установлен`, а не `Запуск в режиме polling`
- Кнопка `Открыть заявку` должна открывать `app.24beershop.ru`

## Безопасность

- Не коммитьте реальный `.env`
- Секреты, которые уже попадали в git-историю, нужно считать скомпрометированными и ротировать
- Не используйте старые ad hoc deploy-скрипты с захардкоженными SSH-паролями

## Настройка бота в группе

1. Добавьте бота в Telegram суперегруппу с включёнными форумами
2. Дайте боту права администратора
3. В каждом нужном топике отправьте `/register_topic`
4. Следуйте инструкциям: название отдела → SLA → эмодзи

## Структура заявок

```
REQ-2025-00001  ← автоматический номер тикета
├── Статус: new / open / in_progress / waiting_for_user / resolved / closed
├── Приоритет: low / normal / high / critical
├── SLA дедлайн: вычисляется из настроек отдела
├── Вложения: фото, документы, голосовые
├── Комментарии: публичные и внутренние (только агенты)
└── История: все изменения с audit trail
```

## API документация

После запуска API доступна на `http://localhost:8000/docs`

## Роли пользователей

| Роль | Возможности |
|------|------------|
| `user` | Создание заявок, просмотр своих заявок, оценка |
| `agent` | + Просмотр всех заявок, смена статуса, комментарии |
| `supervisor` | + Управление отделами, назначение агентов |
| `admin` | Полный доступ, управление правилами маршрутизации |
