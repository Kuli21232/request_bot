"""Telegram topics and AI profiles."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_current_user, get_db, require_admin
from bot.services.topic_learning_service import TopicLearningService
from models.topic import TelegramTopic, TopicAIProfile


class TopicMetaUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    icon_emoji: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None

router = APIRouter(prefix="/api/v1/topics", tags=["topics"])


@router.get("")
async def list_topics(
    include_archived: bool = False,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(TelegramTopic, TopicAIProfile)
        .options(selectinload(TelegramTopic.group))
        .join(TopicAIProfile, TopicAIProfile.topic_id == TelegramTopic.id, isouter=True)
        .order_by(TelegramTopic.last_seen_at.desc().nullslast())
    )
    if not include_archived:
        query = query.where(TelegramTopic.is_active.is_(True))
    result = await db.execute(query)
    rows = result.all()
    return [_serialize_topic(topic, profile) for topic, profile in rows]


@router.get("/{topic_id}")
async def get_topic(
    topic_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TelegramTopic, TopicAIProfile)
        .options(selectinload(TelegramTopic.group))
        .join(TopicAIProfile, TopicAIProfile.topic_id == TelegramTopic.id, isouter=True)
        .where(TelegramTopic.id == topic_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    topic, profile = row
    return _serialize_topic(topic, profile, full=True)


@router.patch("/{topic_id}")
async def update_topic_meta(
    topic_id: int,
    body: TopicMetaUpdate,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    topic = await db.get(TelegramTopic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    data = body.model_dump(exclude_unset=True)
    if "title" in data:
        new_title = (data["title"] or "").strip()
        if not new_title:
            raise HTTPException(status_code=400, detail="Title must not be empty")
        topic.title = new_title
    if "icon_emoji" in data:
        topic.icon_emoji = data["icon_emoji"] or None
    if "is_active" in data and data["is_active"] is not None:
        topic.is_active = bool(data["is_active"])

    await db.commit()
    await db.refresh(topic)

    result = await db.execute(
        select(TelegramTopic, TopicAIProfile)
        .options(selectinload(TelegramTopic.group))
        .join(TopicAIProfile, TopicAIProfile.topic_id == TelegramTopic.id, isouter=True)
        .where(TelegramTopic.id == topic_id)
    )
    row = result.one_or_none()
    topic, profile = row if row else (topic, None)
    return _serialize_topic(topic, profile, full=True)


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(
    topic_id: int,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: mark topic inactive so it disappears from the mini app.

    Hard-delete would cascade into flow signals/cases — we keep history instead.
    """
    topic = await db.get(TelegramTopic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    topic.is_active = False
    await db.commit()
    return None


@router.patch("/{topic_id}/profile")
async def update_topic_profile(
    topic_id: int,
    body: dict,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TopicAIProfile).where(TopicAIProfile.topic_id == topic_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Topic profile not found")

    for field in [
        "profile_summary",
        "system_prompt",
        "allowed_signal_types",
        "default_actions",
        "priority_rules",
        "media_policy",
        "examples",
        "behavior_rules",
        "confidence_threshold",
        "auto_learn_enabled",
        "preferred_department_id",
    ]:
        if field in body:
            setattr(profile, field, body[field])

    await db.commit()
    await db.refresh(profile)
    topic = await db.get(TelegramTopic, topic_id)
    return _serialize_topic(topic, profile, full=True)


@router.post("/{topic_id}/train")
async def train_topic_profile(
    topic_id: int,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    trainer = TopicLearningService()
    result = await trainer.retrain_topic(db, topic_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    await db.commit()
    topic = await db.get(TelegramTopic, topic_id)
    await db.refresh(topic)
    return {
        "trained": True,
        "result": result,
        "topic": _serialize_topic(topic, topic.profile, full=True),
    }


@router.post("/train-all")
async def train_all_topics(
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    trainer = TopicLearningService()
    results = await trainer.retrain_active_topics(db, limit=50)
    await db.commit()
    return {
        "trained_count": len(results),
        "results": results,
    }


def _serialize_topic(topic: TelegramTopic, profile: TopicAIProfile | None, *, full: bool = False) -> dict:
    data = {
        "id": topic.id,
        "group_id": topic.group_id,
        "group_title": topic.group.title if getattr(topic, "group", None) else None,
        "telegram_topic_id": topic.telegram_topic_id,
        "title": topic.title,
        "icon_emoji": topic.icon_emoji,
        "topic_kind": topic.topic_kind,
        "is_active": topic.is_active,
        "message_count": topic.message_count,
        "media_count": topic.media_count,
        "signal_count": topic.signal_count,
        "last_seen_at": topic.last_seen_at.isoformat() if topic.last_seen_at else None,
        "profile_version": topic.profile_version,
    }
    if profile:
        automation = dict(profile.behavior_rules or {}).get("automation")
        data["profile"] = {
            "preferred_department_id": profile.preferred_department_id,
            "profile_summary": profile.profile_summary,
            "allowed_signal_types": profile.allowed_signal_types,
            "default_actions": profile.default_actions,
            "priority_rules": profile.priority_rules,
            "media_policy": profile.media_policy,
            "confidence_threshold": profile.confidence_threshold,
            "auto_learn_enabled": profile.auto_learn_enabled,
            "automation": automation,
        }
        if full:
            data["profile"]["system_prompt"] = profile.system_prompt
            data["profile"]["examples"] = profile.examples
            data["profile"]["behavior_rules"] = profile.behavior_rules
            data["profile"]["learning_snapshot"] = profile.learning_snapshot
    return data
