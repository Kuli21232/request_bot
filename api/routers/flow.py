"""Signals, cases, and flow automation endpoints."""
from datetime import datetime, timezone

import aiohttp
from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_current_user, get_db
from bot.config import settings
from bot.services.notification_service import NotificationService
from bot.services.topic_automation_service import TopicAutomationService
from bot.services.user_profile_ai_service import STAFF_ROLES, UserProfileAIService
from models.flow import FlowCase, FlowSignal, SignalMedia
from models.request import Request
from models.user import User

router = APIRouter(prefix="/api/v1/flow", tags=["flow"])


class ResponsibleUpdate(BaseModel):
    user_id: int | None = None


@router.get("/signals")
async def list_signals(
    kind: str | None = Query(None),
    importance: str | None = Query(None),
    case_id: int | None = Query(None),
    topic_id: int | None = Query(None),
    has_media: bool | None = Query(None),
    requires_attention: bool | None = Query(None),
    digest_bucket: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(FlowSignal)
        .options(
            selectinload(FlowSignal.case).selectinload(FlowCase.responsible_user),
            selectinload(FlowSignal.case).selectinload(FlowCase.suggested_owner),
            selectinload(FlowSignal.department),
            selectinload(FlowSignal.topic),
            selectinload(FlowSignal.media_items),
            selectinload(FlowSignal.request).selectinload(Request.submitter),
            selectinload(FlowSignal.submitter),
        )
    )

    if kind:
        query = query.where(FlowSignal.kind == kind)
    if importance:
        query = query.where(FlowSignal.importance == importance)
    if case_id:
        query = query.where(FlowSignal.case_id == case_id)
    if topic_id:
        query = query.where(FlowSignal.topic_id == topic_id)
    if has_media is not None:
        query = query.where(FlowSignal.has_media == has_media)
    if requires_attention is not None:
        query = query.where(FlowSignal.requires_attention == requires_attention)
    if digest_bucket:
        query = query.where(FlowSignal.digest_bucket == digest_bucket)
    if search:
        query = query.where(
            or_(
                FlowSignal.body.ilike(f"%{search}%"),
                FlowSignal.summary.ilike(f"%{search}%"),
                FlowSignal.store.ilike(f"%{search}%"),
                FlowSignal.topic_label.ilike(f"%{search}%"),
            )
        )
    if current_user.role not in STAFF_ROLES:
        query = query.where(
            or_(
                FlowSignal.submitter_id == current_user.id,
                FlowSignal.case.has(FlowCase.responsible_user_id == current_user.id),
                FlowSignal.request.has(Request.submitter_id == current_user.id),
            )
        )

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    query = query.order_by(FlowSignal.happened_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_signal(item) for item in items],
    }


@router.get("/signals/{signal_id}")
async def get_signal(
    signal_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FlowSignal)
        .options(
            selectinload(FlowSignal.case).selectinload(FlowCase.responsible_user),
            selectinload(FlowSignal.case).selectinload(FlowCase.suggested_owner),
            selectinload(FlowSignal.department),
            selectinload(FlowSignal.topic),
            selectinload(FlowSignal.media_items),
            selectinload(FlowSignal.request).selectinload(Request.submitter),
            selectinload(FlowSignal.submitter),
        )
        .where(FlowSignal.id == signal_id)
    )
    signal = result.scalar_one_or_none()
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    _assert_signal_visible(signal, current_user)
    return _serialize_signal(signal, full=True)


@router.get("/cases")
async def list_cases(
    status: str | None = Query(None),
    kind: str | None = Query(None),
    priority: str | None = Query(None),
    topic_id: int | None = Query(None),
    is_critical: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(FlowCase)
        .options(
            selectinload(FlowCase.department),
            selectinload(FlowCase.request).selectinload(Request.submitter),
            selectinload(FlowCase.primary_topic),
            selectinload(FlowCase.responsible_user),
            selectinload(FlowCase.assigned_by),
            selectinload(FlowCase.suggested_owner),
        )
    )

    if status:
        query = query.where(FlowCase.status == status)
    if kind:
        query = query.where(FlowCase.kind == kind)
    if priority:
        query = query.where(FlowCase.priority == priority)
    if topic_id:
        query = query.where(FlowCase.primary_topic_id == topic_id)
    if is_critical is not None:
        query = query.where(FlowCase.is_critical == is_critical)
    if search:
        query = query.where(or_(FlowCase.title.ilike(f"%{search}%"), FlowCase.summary.ilike(f"%{search}%")))
    query = _apply_case_visibility(query, current_user)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    query = query.order_by(FlowCase.is_critical.desc(), FlowCase.last_signal_at.desc().nullslast()).offset(
        (page - 1) * page_size
    ).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_case(item) for item in items],
    }


@router.get("/cases/{case_id}")
async def get_case(
    case_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FlowCase)
        .options(
            selectinload(FlowCase.department),
            selectinload(FlowCase.primary_topic),
            selectinload(FlowCase.request).selectinload(Request.submitter),
            selectinload(FlowCase.signals).selectinload(FlowSignal.submitter),
            selectinload(FlowCase.responsible_user),
            selectinload(FlowCase.assigned_by),
            selectinload(FlowCase.suggested_owner),
        )
        .where(FlowCase.id == case_id)
    )
    flow_case = result.scalar_one_or_none()
    if flow_case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    _assert_case_visible(flow_case, current_user)
    return _serialize_case(flow_case, full=True)


@router.patch("/cases/{case_id}/status")
async def update_case_status(
    case_id: int,
    body: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Agent role required")

    result = await db.execute(select(FlowCase).where(FlowCase.id == case_id))
    flow_case = result.scalar_one_or_none()
    if flow_case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    new_status = body.get("status", "").strip() or "open"
    flow_case.status = new_status
    await db.commit()
    await db.refresh(flow_case)
    return {"id": flow_case.id, "status": flow_case.status}


@router.patch("/cases/{case_id}/responsible")
async def update_case_responsible(
    case_id: int,
    body: ResponsibleUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Agent role required")

    case_result = await db.execute(
        select(FlowCase)
        .options(
            selectinload(FlowCase.responsible_user),
            selectinload(FlowCase.suggested_owner),
            selectinload(FlowCase.primary_topic),
        )
        .where(FlowCase.id == case_id)
    )
    flow_case = case_result.scalar_one_or_none()
    if flow_case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    target_user = None
    if body.user_id is not None:
        user_result = await db.execute(select(User).where(User.id == body.user_id))
        target_user = user_result.scalar_one_or_none()
        if target_user is None or target_user.is_banned:
            raise HTTPException(status_code=404, detail="Target user not found")

    previous_user_id = flow_case.responsible_user_id
    flow_case.responsible_user_id = target_user.id if target_user else None
    flow_case.assigned_by_user_id = current_user.id if target_user else None
    flow_case.assigned_at = datetime.now(timezone.utc) if target_user else None

    profile_ai = UserProfileAIService()
    if previous_user_id:
        await profile_ai.refresh_snapshot(db, previous_user_id)
    if target_user:
        await profile_ai.refresh_snapshot(db, target_user.id)

    await db.commit()
    await db.refresh(flow_case)

    if target_user and target_user.telegram_user_id:
        bot = Bot(settings.BOT_TOKEN)
        try:
            await NotificationService(bot).notify_case_responsible_assigned(
                target_user=target_user,
                actor=current_user,
                flow_case=flow_case,
            )
        finally:
            await bot.session.close()

    return {
        "id": flow_case.id,
        "responsible_user_id": flow_case.responsible_user_id,
        "responsible_user_name": target_user.first_name if target_user else None,
        "assigned_by_user_id": flow_case.assigned_by_user_id,
        "assigned_at": flow_case.assigned_at.isoformat() if flow_case.assigned_at else None,
    }


@router.get("/digests/overview")
async def get_digest_overview(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Agent role required")

    overview = (
        await db.execute(
            select(
                func.count(FlowSignal.id).label("total_signals"),
                func.count(case((FlowSignal.requires_attention == True, 1))).label("attention"),
                func.count(case((FlowSignal.has_media == True, 1))).label("with_media"),
                func.count(case((FlowSignal.is_noise == True, 1))).label("noise"),
                func.count(case((FlowCase.is_critical == True, 1))).label("critical_cases"),
            )
            .select_from(FlowSignal)
            .join(FlowCase, FlowSignal.case_id == FlowCase.id, isouter=True)
        )
    ).one()

    top_kinds = (
        await db.execute(
            select(FlowSignal.kind, func.count(FlowSignal.id).label("count"))
            .group_by(FlowSignal.kind)
            .order_by(func.count(FlowSignal.id).desc())
            .limit(8)
        )
    ).all()

    return {
        "total_signals": overview.total_signals,
        "requires_attention": overview.attention,
        "with_media": overview.with_media,
        "noise": overview.noise,
        "critical_cases": overview.critical_cases,
        "top_kinds": [{"kind": row.kind, "count": row.count} for row in top_kinds],
    }


@router.get("/topic-sections")
async def get_topic_sections(
    kind: str | None = Query(None),
    requires_attention: bool | None = Query(None),
    limit_topics: int = Query(12, ge=1, le=30),
    signals_per_topic: int = Query(4, ge=1, le=10),
    cases_per_topic: int = Query(3, ge=1, le=10),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TopicAutomationService()
    sections = await service.build_topic_sections(
        db,
        kind=kind,
        requires_attention=requires_attention,
        limit_topics=limit_topics,
        signals_per_topic=signals_per_topic,
        cases_per_topic=cases_per_topic,
    )
    return {
        "items": [
            {
                **section,
                "signals": [_serialize_signal(signal) for signal in section["signals"]],
                "cases": [_serialize_case(flow_case) for flow_case in section["cases"]],
            }
            for section in sections
        ],
        "total": len(sections),
    }


@router.get("/action-board")
async def get_action_board(
    limit: int = Query(8, ge=1, le=20),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TopicAutomationService()
    items = await service.build_action_board(db, limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/group-digests")
async def get_group_digests(
    limit_groups: int = Query(8, ge=1, le=20),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TopicAutomationService()
    items = await service.build_group_digests(db, limit_groups=limit_groups)
    return {"items": items, "total": len(items)}


@router.get("/media/{media_id}/preview")
async def get_media_preview(
    media_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media = await _load_media(db, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    _assert_signal_visible(media.signal, current_user)
    if media.preview_bytes is None:
        raise HTTPException(status_code=404, detail="Preview not available")
    return Response(content=media.preview_bytes, media_type=media.mime_type or "image/jpeg")


@router.get("/media/{media_id}/content")
async def get_media_content(
    media_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media = await _load_media(db, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    _assert_signal_visible(media.signal, current_user)

    if media.telegram_file_path:
        file_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{media.telegram_file_path}"
        async with aiohttp.ClientSession() as client:
            async with client.get(file_url) as response:
                if response.status >= 400:
                    raise HTTPException(status_code=502, detail="Telegram file unavailable")
                payload = await response.read()
                return Response(content=payload, media_type=media.mime_type or "application/octet-stream")

    if media.preview_bytes is not None:
        return Response(content=media.preview_bytes, media_type=media.mime_type or "application/octet-stream")

    raise HTTPException(status_code=404, detail="Content not available")


async def _load_media(db: AsyncSession, media_id: int) -> SignalMedia | None:
    result = await db.execute(
        select(SignalMedia)
        .options(
            selectinload(SignalMedia.signal).selectinload(FlowSignal.request).selectinload(Request.submitter),
            selectinload(SignalMedia.signal).selectinload(FlowSignal.case).selectinload(FlowCase.responsible_user),
        )
        .where(SignalMedia.id == media_id)
    )
    return result.scalar_one_or_none()


def _apply_case_visibility(query, current_user):
    # All authenticated team members can view all operational cases
    return query


def _assert_case_visible(flow_case: FlowCase, current_user) -> None:
    # All authenticated team members can view all operational cases
    return


def _assert_signal_visible(signal: FlowSignal, current_user) -> None:
    # All authenticated team members can view all operational signals
    return


def _serialize_media(item: SignalMedia) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "mime_type": item.mime_type,
        "file_name": item.file_name,
        "original_size": item.original_size,
        "compressed_size": item.compressed_size,
        "width": item.width,
        "height": item.height,
        "duration_seconds": item.duration_seconds,
        "preview_url": f"/api/v1/flow/media/{item.id}/preview",
        "content_url": f"/api/v1/flow/media/{item.id}/content",
        "has_preview": item.preview_bytes is not None,
        "can_open_content": bool(item.preview_bytes is not None or item.telegram_file_path),
    }


def _serialize_signal(signal: FlowSignal, *, full: bool = False) -> dict:
    data = {
        "id": signal.id,
        "kind": signal.kind,
        "importance": signal.importance,
        "actionability": signal.actionability,
        "summary": signal.summary,
        "body": signal.body if full else signal.body[:220],
        "store": signal.store,
        "topic_label": signal.topic_label,
        "case_key": signal.case_key,
        "recommended_action": signal.recommended_action,
        "has_media": signal.has_media,
        "requires_attention": signal.requires_attention,
        "is_noise": signal.is_noise,
        "digest_bucket": signal.digest_bucket,
        "ai_confidence": signal.ai_confidence,
        "case_id": signal.case_id,
        "case_title": signal.case.title if signal.case else None,
        "department_id": signal.department_id,
        "department_name": signal.department.name if signal.department else None,
        "topic_id": signal.topic_id,
        "topic_title": signal.topic.title if signal.topic else signal.topic_label,
        "request_id": signal.request_id,
        "request_ticket": signal.request.ticket_number if signal.request else None,
        "submitter_id": signal.submitter_id,
        "submitter_name": signal.submitter.first_name if signal.submitter else None,
        "submitter_username": signal.submitter.username if signal.submitter else None,
        "responsible_user_id": signal.case.responsible_user_id if signal.case else None,
        "responsible_user_name": signal.case.responsible_user.first_name if signal.case and signal.case.responsible_user else None,
        "suggested_owner_id": signal.case.suggested_owner_id if signal.case else None,
        "suggested_owner_name": signal.case.suggested_owner.first_name if signal.case and signal.case.suggested_owner else None,
        "source_topic_id": signal.source_topic_id,
        "source_message_id": signal.source_message_id,
        "source_chat_id": signal.source_chat_id,
        "happened_at": signal.happened_at.isoformat() if signal.happened_at else signal.created_at.isoformat(),
    }
    if full:
        data["attachments"] = signal.attachments or []
        data["entities"] = signal.entities or {}
        data["ai_labels"] = signal.ai_labels or {}
        data["media_flags"] = signal.media_flags or {}
        data["media"] = [_serialize_media(item) for item in signal.media_items or []]
    return data


def _serialize_case(flow_case: FlowCase, *, full: bool = False) -> dict:
    data = {
        "id": flow_case.id,
        "title": flow_case.title,
        "summary": flow_case.summary,
        "status": flow_case.status,
        "priority": flow_case.priority,
        "kind": flow_case.kind,
        "signal_count": flow_case.signal_count,
        "media_count": flow_case.media_count,
        "is_critical": flow_case.is_critical,
        "stores_affected": flow_case.stores_affected or [],
        "recommended_action": flow_case.recommended_action,
        "ai_confidence": flow_case.ai_confidence,
        "department_id": flow_case.department_id,
        "department_name": flow_case.department.name if flow_case.department else None,
        "primary_topic_id": flow_case.primary_topic_id,
        "primary_topic_title": flow_case.primary_topic.title if flow_case.primary_topic else None,
        "request_id": flow_case.request_id,
        "request_ticket": flow_case.request.ticket_number if flow_case.request else None,
        "responsible_user_id": flow_case.responsible_user_id,
        "responsible_user_name": flow_case.responsible_user.first_name if flow_case.responsible_user else None,
        "responsible_user_username": flow_case.responsible_user.username if flow_case.responsible_user else None,
        "assigned_by_user_id": flow_case.assigned_by_user_id,
        "assigned_by_user_name": flow_case.assigned_by.first_name if flow_case.assigned_by else None,
        "assigned_at": flow_case.assigned_at.isoformat() if flow_case.assigned_at else None,
        "suggested_owner_id": flow_case.suggested_owner_id,
        "suggested_owner_name": flow_case.suggested_owner.first_name if flow_case.suggested_owner else None,
        "last_signal_at": flow_case.last_signal_at.isoformat() if flow_case.last_signal_at else None,
        "updated_at": flow_case.updated_at.isoformat() if flow_case.updated_at else None,
    }
    if full:
        sorted_signals = sorted(flow_case.signals or [], key=lambda item: item.happened_at, reverse=True)
        data["owners"] = flow_case.owners or []
        data["ai_labels"] = flow_case.ai_labels or {}
        data["signals"] = [_serialize_signal(item) for item in sorted_signals[:100]]
    return data
