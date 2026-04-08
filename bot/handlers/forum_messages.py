"""Ключевой хэндлер: захват сообщений из форум-топиков → создание сигналов потока."""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message

from bot.config import settings
from bot.database import AsyncSessionLocal
from bot.database.repositories.flow_repo import FlowRepository
from bot.database.repositories.request_repo import RequestRepository
from bot.services.duplicate_detector import DuplicateDetector
from bot.services.auto_router import AutoRouter
from bot.services.notification_service import NotificationService
from bot.services.ai_classifier import AIClassifier
from bot.services.signal_threader import SignalThreader
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

    ai_result = await ai_classifier.classify(content)
    signal_type = (ai_result or {}).get("signal_type", "request")
    importance = (ai_result or {}).get("importance", "normal")
    action_needed = (ai_result or {}).get("action_needed", "digest_only")
    summary = (ai_result or {}).get("summary") or (content[:120] if content else "Медиа-сигнал")
    store = (ai_result or {}).get("store")
    topic_label = (ai_result or {}).get("topic_label")
    case_key = (ai_result or {}).get("case_key")
    recommended_action = (ai_result or {}).get("recommended_action")
    entities = (ai_result or {}).get("entities") or {}
    ai_confidence = (ai_result or {}).get("confidence")

    # 2. Дубликаты/повторы ищем уже на уровне потока, но request-слой сохраняем для actionable сигналов
    dup_result = await duplicate_detector.find_duplicate(
        content=content,
        department_id=final_department.id,
        submitter_id=db_user.id,
    )

    media_flags = {
        "has_photo": bool(message.photo),
        "has_document": bool(message.document),
        "has_voice": bool(message.voice),
        "has_audio": bool(message.audio),
        "has_video": bool(getattr(message, "video", None)),
    }
    has_media = any(media_flags.values())
    if signal_type == "chat_noise":
        signal_type = "chat/noise"
    is_noise = signal_type == "chat/noise"
    requires_attention = importance in {"high", "critical"} or action_needed in {
        "create_case", "attach_to_case", "suggest_escalation", "route_to_topic",
    }

    new_request = None
    created_case = None
    matched_case = None
    match_score = 0.0

    async with AsyncSessionLocal() as session:
        flow_repo = FlowRepository(session)
        threader = SignalThreader()

        # Shadow request only for actionable operational messages.
        if not is_noise and action_needed in {
            "create_case", "attach_to_case", "suggest_escalation", "route_to_topic", "suggest_reply"
        }:
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
                routing_reason=routing_reason or recommended_action,
                is_duplicate=dup_result.is_duplicate,
                duplicate_of_id=dup_result.original_id,
                similarity_score=dup_result.score,
            )
            if ai_result:
                new_request.ai_subject = summary
                new_request.ai_category = signal_type
                new_request.ai_sentiment = "urgent" if importance in {"high", "critical"} else "neutral"
                if not new_request.subject:
                    new_request.subject = summary
                await session.flush()

        case_match = await threader.match_case(
            flow_repo,
            group_id=final_department.group_id,
            department_id=final_department.id,
            summary=summary,
            body=content,
            case_key=case_key,
            store=store,
        )
        matched_case = case_match.case
        match_score = case_match.score

        if matched_case is None and action_needed in {"create_case", "attach_to_case", "suggest_escalation"} and not is_noise:
            created_case = await flow_repo.create_case(
                group_id=final_department.group_id,
                department_id=final_department.id,
                request_id=new_request.id if new_request else None,
                title=topic_label or summary[:120],
                summary=summary,
                status="watching" if importance == "normal" else "open",
                priority=importance,
                kind=signal_type,
                suggested_owner_id=None,
                owners=[],
                stores_affected=[store] if store else [],
                ai_labels={
                    "case_key": case_key,
                    "signal_type": signal_type,
                    "action_needed": action_needed,
                    "routing_reason": routing_reason,
                },
                recommended_action=recommended_action,
                ai_confidence=ai_confidence,
                last_signal_at=message.date,
                signal_count=1,
                media_count=1 if has_media else 0,
                is_critical=importance == "critical",
            )
            matched_case = created_case

        if matched_case is not None:
            await flow_repo.touch_case_with_signal(
                matched_case,
                signal_time=message.date,
                store=store,
                increment_media=has_media,
                importance=importance,
            )

        signal = await flow_repo.create_signal(
            group_id=final_department.group_id,
            department_id=final_department.id,
            submitter_id=db_user.id,
            request_id=new_request.id if new_request else None,
            case_id=matched_case.id if matched_case else None,
            duplicate_signal_id=None,
            source_topic_id=message.message_thread_id,
            source_message_id=message.message_id,
            source_chat_id=message.chat.id,
            body=content,
            summary=summary,
            store=store,
            kind=signal_type,
            importance=importance,
            actionability=action_needed,
            case_key=case_key,
            topic_label=topic_label,
            recommended_action=recommended_action,
            ai_summary=summary,
            ai_labels={
                "signal_type": signal_type,
                "tags": (ai_result or {}).get("tags", []),
                "auto_routed": auto_routed,
                "routing_reason": routing_reason,
                "match_score": match_score,
            },
            entities=entities,
            media_flags=media_flags,
            attachments=attachments,
            has_media=has_media,
            requires_attention=requires_attention,
            is_noise=is_noise,
            digest_bucket=signal_type if signal_type in {"photo_report", "news", "status_update"} else "operations",
            ai_confidence=ai_confidence,
        )
        await session.commit()

    # 3. Формируем mini_app_url отдельно от webhook-домена
    mini_app_url = (
        f"{settings.MINIAPP_BASE_URL.rstrip('/')}/signals/{signal.id}"
        if settings.MINIAPP_BASE_URL
        else f"https://t.me/{(await bot.get_me()).username}"
    )

    # 4. Ответ пользователю только когда есть смысловая автоматизация, чтобы не зашумлять поток
    response_lines = [
        f"🧠 <b>Сигнал обработан</b>",
        f"Тема: {summary}",
        f"Тип: <b>{_signal_type_label(signal_type)}</b>",
    ]

    if auto_routed:
        response_lines.append(f"↪️ Маршрутизация: из <i>{department.name}</i> в <i>{final_department.name}</i>")

    if matched_case:
        if created_case:
            response_lines.append(f"🗂 Создан кейс: <b>{matched_case.title}</b>")
        else:
            response_lines.append(f"🗂 Добавлено в кейс: <b>{matched_case.title}</b>")

    if new_request is not None:
        response_lines.append(f"🎫 Actionable задача: <code>{new_request.ticket_number}</code>")

    if dup_result.is_duplicate and dup_result.original_ticket:
        response_lines.append(f"🔁 Похоже на тикет <code>{dup_result.original_ticket}</code>")

    if recommended_action:
        response_lines.append(f"➡️ Рекомендация: {recommended_action}")

    keyboard = build_request_created_keyboard(
        ticket_number=new_request.ticket_number if new_request else f"SIG-{signal.id}",
        mini_app_url=mini_app_url,
        request_id=new_request.id if new_request else signal.id,
    )

    if requires_attention or created_case or new_request is not None:
        await message.reply("\n".join(response_lines), reply_markup=keyboard, parse_mode="HTML")

    # 5. Уведомляем агентов только по actionable кейсам/задачам
    if new_request is not None:
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


def _signal_type_label(signal_type: str) -> str:
    labels = {
        "problem": "Проблема",
        "request": "Запрос",
        "status_update": "Статус",
        "photo_report": "Фотоотчет",
        "delivery": "Поставка",
        "finance": "Финансы",
        "compliance": "Комплаенс",
        "inventory": "Остатки/товар",
        "chat_noise": "Шум/уточнение",
        "escalation": "Эскалация",
        "news": "Новость",
    }
    return labels.get(signal_type, signal_type)
