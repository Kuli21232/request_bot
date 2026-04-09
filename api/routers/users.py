"""Endpoints for users, profiles, notes, and subscriptions."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from api.dependencies import get_db, get_current_user, require_agent, require_admin
from bot.config import settings
from bot.database.repositories.knowledge_repo import KnowledgeRepository
from bot.database.repositories.user_repo import UserRepository
from bot.services.notification_service import NotificationService
from models.enums import UserRole
from models.user import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class ProfileNoteIn(BaseModel):
    body: str
    notify_target: bool = False


@router.get("")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by roles: agent,admin,supervisor"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, le=200),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    q = select(User)

    if role:
        roles_list = [r.strip() for r in role.split(",")]
        valid_roles = []
        for r in roles_list:
            try:
                valid_roles.append(UserRole(r))
            except ValueError:
                pass
        if valid_roles:
            q = q.where(User.role.in_(valid_roles))

    if search:
        q = q.where(
            User.first_name.ilike(f"%{search}%")
            | User.username.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
        )

    q = q.order_by(User.first_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    users = result.scalars().all()
    return [_serialize_user(user) for user in users]


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return _serialize_user(current_user)


@router.get("/{user_id}")
async def get_user_profile(
    user_id: int,
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    knowledge_repo = KnowledgeRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    notes = await knowledge_repo.list_profile_notes(user_id, limit=20)
    subscription = await knowledge_repo.get_subscription(current_user.id, user_id)
    data = _serialize_user(user)
    data["notes"] = [_serialize_note(note) for note in notes]
    data["is_watching"] = bool(subscription and subscription.is_active)
    data["watchers_count"] = len([item for item in user.profile_watchers if item.is_active])
    return data


@router.post("/{user_id}/notes")
async def add_profile_note(
    user_id: int,
    payload: ProfileNoteIn,
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    knowledge_repo = KnowledgeRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    note = await knowledge_repo.add_profile_note(
        target_user_id=user_id,
        author_id=current_user.id,
        body=payload.body,
        notify_target=payload.notify_target,
    )
    notes = await knowledge_repo.list_profile_notes(user_id, limit=1)
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
    return _serialize_note(notes[0] if notes else note)


@router.post("/{user_id}/watch")
async def watch_profile(
    user_id: int,
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
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
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
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


def _serialize_user(user: User) -> dict:
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
        "notes_count": len(getattr(user, "profile_notes", []) or []),
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
