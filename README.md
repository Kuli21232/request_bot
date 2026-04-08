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
# Заполнить BOT_TOKEN и DATABASE_URL

# 3. Применить миграции
alembic upgrade head

# 4. Запустить бота (polling режим — без WEBHOOK_BASE_URL)
python -m bot.main

# 5. Запустить API (отдельный терминал)
uvicorn api.main:app --reload --port 8000
```

## Деплой на Timeweb VDS

```bash
# 1. Скопировать проект на сервер
# 2. Создать .env с реальными значениями
# 3. Запустить через Docker Compose
docker compose up -d

# 4. Применить миграции
docker compose exec bot alembic upgrade head

# 5. Загрузить модель Ollama (опционально)
docker compose exec ollama ollama pull llama3

# 6. Настроить Nginx (nginx.conf) и SSL через certbot
certbot --nginx -d api.yourdomain.com -d admin.yourdomain.com -d app.yourdomain.com
```

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
