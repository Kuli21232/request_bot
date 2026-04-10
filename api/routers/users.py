"""Endpoints for users, profiles, notes, subscriptions, and profile AI."""
from typing import Optional

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db, require_admin
from bot.config import settings
from bot.database.repositories.knowledge_repo import KnowledgeRepository
from bot.database.repositories.user_repo import UserRepository
from bot.services.notification_service import NotificationService
from bot.services.user_profile_ai_service import STAFF_ROLES, UserProfileAIService
from models.enums import UserRole
from models.user import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class ProfileNoteIn(BaseModel):
    body: str
    notify_target: bool = False


def _is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


@router.get("")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by roles: agent,admin,supervisor"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Agent role required")

    query = select(User)

    if role:
        roles_list = [item.strip() for item in role.split(",")]
        valid_roles = []
        for item in roles_list:
            try:
                valid_roles.append(UserRole(item))
            except ValueError:
                pass
        if valid_roles:
            query = query.where(User.role.in_(valid_roles))

    if search:
        pattern = f"%{search}%"
        query = query.where(
            User.first_name.ilike(pattern)
            | User.last_name.ilike(pattern)
            | User.username.ilike(pattern)
            | User.email.ilike(pattern)
        )

    query = query.order_by(User.first_name, User.last_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = list(result.scalars().all())
    metrics = await UserProfileAIService().build_team_metrics(db, users)
    return [_serialize_user(user, metrics.get(user.id)) for user in users]


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return _serialize_user(current_user)


@router.get("/profile")
async def get_my_profile(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserProfileAIService()
    return await service.build_profile_payload(db, target_user=current_user, viewer_user=current_user)


@router.get("/{user_id}")
async def get_user_basic(
    user_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Agent role required")

    repo = UserRepository(db)
    service = UserProfileAIService()
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    metrics = await service.build_team_metrics(db, [user])
    return _serialize_user(user, metrics.get(user.id))


@router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.id != user_id and not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    service = UserProfileAIService()
    return await service.build_profile_payload(db, target_user=user, viewer_user=current_user)


@router.post("/{user_id}/notes")
async def add_profile_note(
    user_id: int,
    payload: ProfileNoteIn,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Agent role required")

    user_repo = UserRepository(db)
    knowledge_repo = KnowledgeRepository(db)
    profile_ai = UserProfileAIService()
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    note = await knowledge_repo.add_profile_note(
        target_user_id=user_id,
        author_id=current_user.id,
        body=payload.body,
        notify_target=payload.notify_target,
    )
    await profile_ai.refresh_snapshot(db, user_id)
    await db.commit()

    bot = Bot(settings.BOT_TOKEN)
    try:
        service = NotificationService(bot)
        await service.notify_profile_note(
            target_user=user,
            author=current_user,
            note_body=note.body,
            notify_target=payload.notify_target,
        )
    finally:
        await bot.session.close()

    notes = await knowledge_repo.list_profile_notes(user_id, limit=1)
    return _serialize_note(notes[0] if notes else note)


@router.post("/{user_id}/watch")
async def watch_profile(
    user_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Agent role required")
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot watch yourself")

    user_repo = UserRepository(db)
    target = await user_repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    repo = KnowledgeRepository(db)
    subscription = await repo.upsert_subscription(
        watcher_user_id=current_user.id,
        target_user_id=user_id,
        active=True,
    )
    return {"ok": True, "subscription_id": subscription.id}


@router.delete("/{user_id}/watch")
async def unwatch_profile(
    user_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Agent role required")

    repo = KnowledgeRepository(db)
    subscription = await repo.get_subscription(current_user.id, user_id)
    if subscription is None:
        return {"ok": True}
    await repo.upsert_subscription(
        watcher_user_id=current_user.id,
        target_user_id=user_id,
        active=False,
    )
    return {"ok": True}


@router.patch("/{user_id}/role")
async def update_role(
    user_id: int,
    body: dict,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        new_role = UserRole(body.get("role"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    user.role = new_role
    await db.commit()
    return _serialize_user(user)


@router.patch("/{user_id}/ban")
async def toggle_ban(
    user_id: int,
    body: dict,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_banned = body.get("is_banned", not user.is_banned)
    await db.commit()
    return _serialize_user(user)


def _serialize_user(user: User, metrics: dict | None = None) -> dict:
    metrics = metrics or {}
    loaded_notes = user.__dict__.get("profile_notes")
    return {
        "id": user.id,
        "telegram_user_id": user.telegram_user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "is_banned": user.is_banned,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        "created_at": user.created_at.isoformat() if hasattr(user, "created_at") and user.created_at else None,
        "notes_count": len(loaded_notes or []) if loaded_notes is not None else 0,
        "assigned_open_case_count": metrics.get("assigned_open_case_count", 0),
        "critical_case_count": metrics.get("critical_case_count", 0),
        "submitted_signal_count": metrics.get("submitted_signal_count", 0),
        "ai_summary": metrics.get("ai_summary"),
        "top_topics": metrics.get("top_topics", []),
    }


def _serialize_note(note) -> dict:
    return {
        "id": note.id,
        "body": note.body,
        "notify_target": note.notify_target,
        "author_id": note.author_id,
        "author_name": note.author.first_name if note.author else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }
