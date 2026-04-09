"""Сигналы, кейсы и сводки инфопотока."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_current_user, get_db, require_agent
from bot.database.repositories.flow_repo import FlowRepository
from bot.database.repositories.topic_repo import TopicRepository
from bot.services.topic_ai_engine import TopicAIEngine
from models.flow import FlowCase, FlowSignal
from models.request import Request

router = APIRouter(prefix="/api/v1/flow", tags=["flow"])


@router.get("/signals")
async def list_signals(
    kind: str | None = Query(None),
    importance: str | None = Query(None),
    case_id: int | None = Query(None),
    has_media: bool | None = Query(None),
    requires_attention: bool | None = Query(None),
    digest_bucket: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(FlowSignal)
        .options(
            selectinload(FlowSignal.case),
            selectinload(FlowSignal.department),
            selectinload(FlowSignal.topic),
            selectinload(FlowSignal.media_items),
            selectinload(FlowSignal.request),
            selectinload(FlowSignal.submitter),
        )
    )

    if kind:
        q = q.where(FlowSignal.kind == kind)
    if importance:
        q = q.where(FlowSignal.importance == importance)
    if case_id:
        q = q.where(FlowSignal.case_id == case_id)
    if has_media is not None:
        q = q.where(FlowSignal.has_media == has_media)
    if requires_attention is not None:
        q = q.where(FlowSignal.requires_attention == requires_attention)
    if digest_bucket:
        q = q.where(FlowSignal.digest_bucket == digest_bucket)
    if search:
        q = q.where(
            or_(
                FlowSignal.body.ilike(f"%{search}%"),
                FlowSignal.summary.ilike(f"%{search}%"),
                FlowSignal.store.ilike(f"%{search}%"),
                FlowSignal.topic_label.ilike(f"%{search}%"),
            )
        )

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(FlowSignal.happened_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
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
            selectinload(FlowSignal.case),
            selectinload(FlowSignal.department),
            selectinload(FlowSignal.topic),
            selectinload(FlowSignal.media_items),
            selectinload(FlowSignal.request),
            selectinload(FlowSignal.submitter),
        )
        .where(FlowSignal.id == signal_id)
    )
    signal = result.scalar_one_or_none()
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return _serialize_signal(signal, full=True)


@router.get("/cases")
async def list_cases(
    status: str | None = Query(None),
    kind: str | None = Query(None),
    priority: str | None = Query(None),
    is_critical: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    q = select(FlowCase).options(selectinload(FlowCase.department), selectinload(FlowCase.request), selectinload(FlowCase.primary_topic))

    if status:
        q = q.where(FlowCase.status == status)
    if kind:
        q = q.where(FlowCase.kind == kind)
    if priority:
        q = q.where(FlowCase.priority == priority)
    if is_critical is not None:
        q = q.where(FlowCase.is_critical == is_critical)
    if search:
        q = q.where(or_(FlowCase.title.ilike(f"%{search}%"), FlowCase.summary.ilike(f"%{search}%")))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(FlowCase.is_critical.desc(), FlowCase.last_signal_at.desc().nullslast()).offset(
        (page - 1) * page_size
    ).limit(page_size)
    result = await db.execute(q)
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
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FlowCase)
        .options(
            selectinload(FlowCase.department),
            selectinload(FlowCase.primary_topic),
            selectinload(FlowCase.request),
            selectinload(FlowCase.signals),
        )
        .where(FlowCase.id == case_id)
    )
    flow_case = result.scalar_one_or_none()
    if flow_case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return _serialize_case(flow_case, full=True)


@router.patch("/cases/{case_id}/status")
async def update_case_status(
    case_id: int,
    body: dict,
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FlowCase).where(FlowCase.id == case_id))
    flow_case = result.scalar_one_or_none()
    if flow_case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    new_status = body.get("status", "").strip() or "open"
    flow_case.status = new_status
    await db.commit()
    await db.refresh(flow_case)
    return {"id": flow_case.id, "status": flow_case.status}


@router.get("/digests/overview")
async def get_digest_overview(
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
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
    topic_repo = TopicRepository(db)
    flow_repo = FlowRepository(db)
    engine = TopicAIEngine()

    groups = await topic_repo.list_groups_with_topics()
    metrics = await topic_repo.build_topic_metrics()
    ranked_topics: list[dict] = []
    for group in groups:
        ranked_topics.extend(
            engine.sort_topics([topic for topic in group.topics if topic.is_active], metrics)
        )

    ranked_topics.sort(
        key=lambda item: (
            item["score"],
            item["metrics"]["attention_count"],
            item["metrics"]["open_case_count"],
            item["metrics"]["signal_count"],
        ),
        reverse=True,
    )

    sections = []
    for item in ranked_topics:
        topic = item["topic"]
        profile = item["profile"]
        signals = await flow_repo.list_topic_signal_briefs(
            topic_id=topic.id,
            limit=signals_per_topic,
            kind=kind,
            requires_attention=requires_attention,
        )
        cases = await flow_repo.list_topic_cases(topic_id=topic.id, limit=cases_per_topic)
        if not signals and not cases:
            continue

        automation = dict(profile.behavior_rules or {}).get("automation", {})
        sections.append(
            {
                "topic_id": topic.id,
                "topic_title": topic.title,
                "group_id": topic.group_id,
                "group_title": topic.group.title if topic.group else None,
                "icon_emoji": topic.icon_emoji,
                "topic_kind": topic.topic_kind,
                "priority": item["priority"],
                "score": item["score"],
                "reasons": item["reasons"],
                "stats": {
                    **item["metrics"],
                    "message_count": topic.message_count,
                    "media_count": topic.media_count,
                },
                "profile_summary": profile.profile_summary,
                "automation": automation,
                "signals": [_serialize_signal(signal) for signal in signals],
                "cases": [_serialize_case(flow_case) for flow_case in cases],
            }
        )
        if len(sections) >= limit_topics:
            break

    return {
        "items": sections,
        "total": len(sections),
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
        data["media"] = [
            {
                "id": item.id,
                "kind": item.kind,
                "mime_type": item.mime_type,
                "file_name": item.file_name,
                "original_size": item.original_size,
                "compressed_size": item.compressed_size,
                "width": item.width,
                "height": item.height,
                "duration_seconds": item.duration_seconds,
            }
            for item in signal.media_items or []
        ]
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
        "last_signal_at": flow_case.last_signal_at.isoformat() if flow_case.last_signal_at else None,
        "updated_at": flow_case.updated_at.isoformat() if flow_case.updated_at else None,
    }
    if full:
        sorted_signals = sorted(flow_case.signals or [], key=lambda item: item.happened_at, reverse=True)
        data["owners"] = flow_case.owners or []
        data["ai_labels"] = flow_case.ai_labels or {}
        data["signals"] = [_serialize_signal(item) for item in sorted_signals[:100]]
    return data
