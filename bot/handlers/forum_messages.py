"""Ключевой хэндлер: захват сообщений из форум-топиков → создание заявок."""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message

from bot.config import settings
from bot.database import AsyncSessionLocal
from bot.database.repositories.request_repo import RequestRepository
from bot.database.repositories.department_repo import DepartmentRepository
from bot.database.repositories.user_repo import UserRepository
from bot.services.duplicate_detector import DuplicateDetector
from bot.services.auto_router import AutoRouter
from bot.services.notification_service import NotificationService
from bot.services.ai_classifier import AIClassifier
from bot.keyboards.inline import build_request_created_keyboard
from models.user import User
from models.department import Department

logger = logging.getLogger(__name__)

router = Router()

# Фильтр: только суперегруппы с топиками, только не-боты
router.message.filter(
    F.chat.type == "supergroup",
    F.message_thread_id.is_not(None),
)


@router.message(F.text | F.photo | F.document | F.voice | F.audio)
async def handle_forum_message(
    message: Message,
    bot: Bot,
    department: Department | None,
    db_user: User | None,
) -> None:
    # Пропускаем если это сообщение от бота
    if message.from_user is None or message.from_user.is_bot:
        return

    # Пропускаем если топик не зарегистрирован
    if department is None:
        return

    # Пропускаем если пользователь не идентифицирован
    if db_user is None:
        return

    # Извлекаем текст (или подпись к медиа)
    content = message.text or message.caption or ""
    attachments = await _extract_attachments(message, bot)

    # Если нет текста и нет вложений — игнорируем
    if not content.strip() and not attachments:
        return

    auto_router = AutoRouter()
    duplicate_detector = DuplicateDetector()
    ai_classifier = AIClassifier()
    notification_service = NotificationService(bot)

    # 1. Auto-routing: может перенаправить в другой отдел
    suggested_dept = await auto_router.suggest_department(
        text=content,
        group_id=department.group_id,
        exclude_department_id=department.id,
    )
    final_department = suggested_dept if suggested_dept else department
    auto_routed = suggested_dept is not None
    routing_reason = auto_router.last_match_reason

    # 2. Поиск дублей
    dup_result = await duplicate_detector.find_duplicate(
        content=content,
        department_id=final_department.id,
        submitter_id=db_user.id,
    )

    # 3. Создаём заявку
    async with AsyncSessionLocal() as session:
        request_repo = RequestRepository(session)
        new_request = await request_repo.create(
            group_id=final_department.group_id,
            department_id=final_department.id,
            submitter_id=db_user.id,
            body=content,
            telegram_message_id=message.message_id,
            telegram_topic_id=message.message_thread_id,
            telegram_chat_id=message.chat.id,
            attachments=attachments,
            auto_routed=auto_routed,
            routing_reason=routing_reason,
            is_duplicate=dup_result.is_duplicate,
            duplicate_of_id=dup_result.original_id,
            similarity_score=dup_result.score,
        )

    # 4. AI-классификация (асинхронно, не блокируем ответ)
    ai_result = await ai_classifier.classify(content)
    if ai_result:
        async with AsyncSessionLocal() as session:
            req_repo = RequestRepository(session)
            req = await req_repo.get_by_id(new_request.id)
            if req:
                req.ai_subject = ai_result.get("subject")
                req.ai_category = ai_result.get("category")
                req.ai_sentiment = ai_result.get("sentiment")
                if not req.subject:
                    req.subject = ai_result.get("subject")
                await session.commit()

    # 5. Формируем mini_app_url (используем WEBHOOK_BASE_URL как базу)
    mini_app_url = (
        f"{settings.WEBHOOK_BASE_URL.rstrip('/')}/app/requests/{new_request.id}"
        if settings.WEBHOOK_BASE_URL
        else f"https://t.me/{(await bot.get_me()).username}"
    )

    # 6. Ответ пользователю
    text = (
        f"✅ Заявка зарегистрирована!\n"
        f"Номер: <code>{new_request.ticket_number}</code>\n"
        f"Отдел: {final_department.icon_emoji or ''} {final_department.name}\n"
        f"Статус: <b>Новая</b>"
    )

    if auto_routed:
        text += f"\n\n↪️ Перенаправлена из <i>{department.name}</i>"

    if dup_result.is_duplicate:
        text += (
            f"\n\n⚠️ Похожа на заявку <code>{dup_result.original_ticket}</code>. "
            f"Заявки связаны."
        )

    keyboard = build_request_created_keyboard(
        ticket_number=new_request.ticket_number,
        mini_app_url=mini_app_url,
        request_id=new_request.id,
    )

    await message.reply(text, reply_markup=keyboard, parse_mode="HTML")

    # 7. Уведомляем агентов отдела
    await notification_service.notify_new_request(new_request, final_department)


async def _extract_attachments(message: Message, bot: Bot) -> list[dict]:
    attachments = []
    if message.photo:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        attachments.append({
            "type": "photo",
            "file_id": photo.file_id,
            "file_path": file.file_path,
        })
    if message.document:
        attachments.append({
            "type": "document",
            "file_id": message.document.file_id,
            "file_name": message.document.file_name,
            "mime_type": message.document.mime_type,
        })
    if message.voice:
        attachments.append({
            "type": "voice",
            "file_id": message.voice.file_id,
            "duration": message.voice.duration,
        })
    if message.audio:
        attachments.append({
            "type": "audio",
            "file_id": message.audio.file_id,
            "file_name": message.audio.file_name,
        })
    return attachments
