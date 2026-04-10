"""Forum topic ingestion into flow signals, cases, and optional shadow requests."""
import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from bot.config import settings
from bot.database import AsyncSessionLocal
from bot.database.repositories.flow_repo import FlowRepository
from bot.database.repositories.request_repo import RequestRepository
from bot.database.repositories.topic_repo import TopicRepository
from bot.database.repositories.user_repo import UserRepository
from bot.keyboards.inline import build_request_created_keyboard
from bot.services.ai_classifier import AIClassifier
from bot.services.auto_router import AutoRouter
from bot.services.duplicate_detector import DuplicateDetector, DuplicateResult
from bot.services.media_processor import MediaProcessor
from bot.services.notification_service import NotificationService
from bot.services.signal_threader import SignalThreader
from bot.services.topic_ai_engine import TopicAIEngine
from bot.services.user_profile_ai_service import UserProfileAIService
from models.department import Department
from models.topic import TelegramTopic, TopicAIProfile
from models.user import User

logger = logging.getLogger(__name__)

router = Router()

router.message.filter(
    F.chat.type == "supergroup",
    F.message_thread_id.is_not(None),
)


@router.message(F.forum_topic_created)
async def handle_forum_topic_created(message: Message) -> None:
    await _sync_topic_metadata(message, title_override=message.forum_topic_created.name)


@router.message(F.forum_topic_edited)
async def handle_forum_topic_edited(message: Message) -> None:
    await _sync_topic_metadata(message, title_override=message.forum_topic_edited.name)


@router.message(F.text | F.photo | F.document | F.voice | F.audio | F.video)
async def handle_forum_message(
    message: Message,
    bot: Bot,
    department: Department | None,
    topic: TelegramTopic | None,
    topic_profile: TopicAIProfile | None,
    db_user: User | None,
) -> None:
    if message.from_user is None or message.from_user.is_bot or db_user is None:
        return

    if topic is None or topic_profile is None:
        return

    content = (message.text or message.caption or "").strip()
    media_processor = MediaProcessor()
    topic_ai = TopicAIEngine()
    topic_context = topic_ai.build_context(topic, topic_profile)
    attachments, media_items, media_flags = await media_processor.extract(
        message,
        bot,
        media_policy=topic_profile.media_policy,
    )
    has_media = any(media_flags.values())

    if not content and not attachments:
        return

    auto_router = AutoRouter()
    duplicate_detector = DuplicateDetector()
    ai_classifier = AIClassifier()
    notification_service = NotificationService(bot)

    suggested_dept = await auto_router.suggest_department(
        text=content,
        group_id=topic.group_id,
        exclude_department_id=department.id if department else None,
    )
    final_department = suggested_dept if suggested_dept else department
    auto_routed = suggested_dept is not None
    routing_reason = auto_router.last_match_reason

    ai_result = await ai_classifier.classify(content, topic_context=topic_context)
    ai_result = topic_ai.apply_profile(ai_result, topic, topic_profile, has_media=has_media)

    signal_type = ai_result.get("signal_type", "request")
    if signal_type == "chat_noise":
        signal_type = "chat/noise"
    importance = ai_result.get("importance", "normal")
    action_needed = ai_result.get("action_needed", "digest_only")
    summary = ai_result.get("summary") or (content[:120] if content else topic.title)
    store = ai_result.get("store")
    topic_label = ai_result.get("topic_label") or topic.title
    case_key = ai_result.get("case_key")
    recommended_action = ai_result.get("recommended_action")
    entities = ai_result.get("entities") or {}
    ai_confidence = ai_result.get("confidence")

    is_noise = signal_type == "chat/noise"
    requires_attention = importance in {"high", "critical"} or action_needed in {
        "create_case", "attach_to_case", "suggest_escalation", "route_to_topic",
    }

    dup_result = DuplicateResult(is_duplicate=False)
    if final_department is not None:
        dup_result = await duplicate_detector.find_duplicate(
            content=content,
            department_id=final_department.id,
            submitter_id=db_user.id,
        )

    new_request = None
    created_case = None
    matched_case = None
    signal = None
    match_score = 0.0

    async with AsyncSessionLocal() as session:
        flow_repo = FlowRepository(session)
        topic_repo = TopicRepository(session)
        user_repo = UserRepository(session)
        threader = SignalThreader()
        profile_ai = UserProfileAIService()

        stored_topic = await topic_repo.get_topic(topic.id)
        if stored_topic is None:
            return

        stored_profile = stored_topic.profile
        if stored_profile is None:
            return

        if final_department is not None and stored_profile.preferred_department_id is None:
            stored_profile.preferred_department_id = final_department.id

        if final_department is not None and not is_noise and action_needed in {
            "create_case", "attach_to_case", "suggest_escalation", "route_to_topic", "suggest_reply"
        }:
            request_repo = RequestRepository(session)
            new_request = await request_repo.create(
                group_id=stored_topic.group_id,
                department_id=final_department.id,
                submitter_id=db_user.id,
                body=content or summary,
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
            new_request.ai_subject = summary
            new_request.ai_category = signal_type
            new_request.ai_sentiment = "urgent" if importance in {"high", "critical"} else "neutral"
            if not new_request.subject:
                new_request.subject = summary
            await session.flush()

        case_match = await threader.match_case(
            flow_repo,
            group_id=stored_topic.group_id,
            department_id=final_department.id if final_department else None,
            summary=summary,
            body=content or summary,
            case_key=case_key,
            store=store,
        )
        matched_case = case_match.case
        match_score = case_match.score

        if matched_case is None and action_needed in {"create_case", "attach_to_case", "suggest_escalation"} and not is_noise:
            suggested_owner = (
                await user_repo.get_agent_with_min_load(final_department.id)
                if final_department is not None
                else None
            )
            created_case = await flow_repo.create_case(
                group_id=stored_topic.group_id,
                department_id=final_department.id if final_department else None,
                primary_topic_id=stored_topic.id,
                request_id=new_request.id if new_request else None,
                title=topic_label or summary[:120],
                summary=summary,
                status="watching" if importance == "normal" else "open",
                priority=importance,
                kind=signal_type,
                suggested_owner_id=suggested_owner.id if suggested_owner else None,
                owners=[],
                stores_affected=[store] if store else [],
                ai_labels={
                    "case_key": case_key,
                    "signal_type": signal_type,
                    "action_needed": action_needed,
                    "routing_reason": routing_reason,
                    "topic_title": stored_topic.title,
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
            group_id=stored_topic.group_id,
            department_id=final_department.id if final_department else None,
            topic_id=stored_topic.id,
            submitter_id=db_user.id,
            request_id=new_request.id if new_request else None,
            case_id=matched_case.id if matched_case else None,
            duplicate_signal_id=None,
            source_topic_id=message.message_thread_id,
            source_message_id=message.message_id,
            source_chat_id=message.chat.id,
            body=content or summary,
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
                "tags": ai_result.get("tags", []),
                "auto_routed": auto_routed,
                "routing_reason": routing_reason,
                "match_score": match_score,
                "topic_kind": stored_topic.topic_kind,
                "topic_profile_version": stored_topic.profile_version,
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

        for media_item in media_items:
            await flow_repo.create_signal_media(signal_id=signal.id, **media_item)

        topic_ai.observe_signal(
            stored_topic,
            stored_profile,
            signal_type=signal_type,
            action_needed=action_needed,
            importance=importance,
            has_media=has_media,
        )
        await topic_repo.mark_signal_recorded(stored_topic)
        await profile_ai.refresh_snapshot(session, db_user.id)
        if matched_case and matched_case.responsible_user_id and matched_case.responsible_user_id != db_user.id:
            await profile_ai.refresh_snapshot(session, matched_case.responsible_user_id)
        await session.commit()

    mini_app_url = (
        f"{settings.MINIAPP_BASE_URL.rstrip('/')}/signals/{signal.id}"
        if settings.MINIAPP_BASE_URL
        else f"https://t.me/{(await bot.get_me()).username}"
    )

    response_lines = [
        "🧠 <b>Сигнал обработан</b>",
        f"Тема: {summary}",
        f"Топик: <b>{topic.title}</b>",
        f"Тип: <b>{_signal_type_label(signal_type)}</b>",
    ]

    if auto_routed and department and final_department:
        response_lines.append(f"↪️ Маршрутизация: из <i>{department.name}</i> в <i>{final_department.name}</i>")

    if matched_case:
        response_lines.append(
            f"🗂 {'Создан кейс' if created_case else 'Добавлено в кейс'}: <b>{matched_case.title}</b>"
        )

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

    if new_request is not None and final_department is not None:
        await notification_service.notify_new_request(new_request, final_department)


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
        "chat/noise": "Шум/уточнение",
        "escalation": "Эскалация",
        "news": "Новость",
    }
    return labels.get(signal_type, signal_type)


async def _sync_topic_metadata(message: Message, *, title_override: str) -> None:
    if message.message_thread_id is None:
        return

    async with AsyncSessionLocal() as session:
        topic_repo = TopicRepository(session)
        department = await topic_repo.get_department_by_topic(
            chat_id=message.chat.id,
            topic_id=message.message_thread_id,
        )
        await topic_repo.ensure_topic(
            chat_id=message.chat.id,
            chat_title=message.chat.title or "Telegram group",
            topic_id=message.message_thread_id,
            topic_title=title_override,
            department=department,
            seen_at=message.date,
        )
        await session.commit()
