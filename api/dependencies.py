"""Dependency Injection для FastAPI: сессия БД, текущий пользователь."""
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import api_settings

# ── БД ──────────────────────────────────────────────────────────
_engine = create_async_engine(api_settings.DATABASE_URL, pool_pre_ping=True)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionLocal() as session:
        yield session


# ── JWT Auth ──────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = jwt.decode(
            credentials.credentials,
            api_settings.API_SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id: int = int(user_id_raw)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    from sqlalchemy import select
    from models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.is_banned:
        raise HTTPException(status_code=401, detail="User not found or banned")

    return user


async def require_agent(user=Depends(get_current_user)):
    from models.enums import UserRole
    if user.role not in (UserRole.agent, UserRole.supervisor, UserRole.admin):
        raise HTTPException(status_code=403, detail="Agent role required")
    return user


async def require_admin(user=Depends(get_current_user)):
    from models.enums import UserRole
    if user.role not in (UserRole.supervisor, UserRole.admin):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
