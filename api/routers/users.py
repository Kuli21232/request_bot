"""Эндпоинты для управления пользователями."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_current_user, require_agent, require_admin
from models.user import User
from models.enums import UserRole

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("")
async def list_users(
    role: Optional[str] = Query(None, description="Фильтр по роли (через запятую): agent,admin,supervisor"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, le=200),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """Список пользователей. Доступно агентам и выше."""
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
            User.first_name.ilike(f"%{search}%") |
            User.username.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%")
        )

    q = q.order_by(User.first_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    users = result.scalars().all()

    return [_serialize_user(u) for u in users]


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """Информация о текущем пользователе."""
    return _serialize_user(current_user)


@router.patch("/{user_id}/role")
async def update_role(
    user_id: int,
    body: dict,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Сменить роль пользователя. Только для admin/supervisor."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    try:
        new_role = UserRole(body.get("role"))
    except ValueError:
        from fastapi import HTTPException
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
    """Заблокировать/разблокировать пользователя."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        from fastapi import HTTPException
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
        "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
    }
