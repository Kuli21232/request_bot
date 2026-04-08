"""Аналитика и статистика."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, require_agent, get_current_user
from models.request import Request
from models.enums import RequestStatus, RequestPriority, UserRole

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/my-stats")
async def get_my_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Статистика по заявкам текущего пользователя (доступна всем)."""
    result = await db.execute(
        select(
            func.count(Request.id).label("total"),
            func.count(case((Request.status == RequestStatus.open, 1))).label("open"),
            func.count(case((Request.status == RequestStatus.in_progress, 1))).label("in_progress"),
            func.count(case((Request.status == RequestStatus.resolved, 1))).label("resolved"),
            func.count(case((Request.status == RequestStatus.closed, 1))).label("closed"),
            func.count(case((Request.sla_breached == True, 1))).label("sla_breached"),
        ).where(Request.submitter_id == current_user.id)
    )
    row = result.one()
    return {
        "role": current_user.role.value,
        "total": row.total,
        "new": 0,
        "open": row.open,
        "in_progress": row.in_progress,
        "resolved": row.resolved,
        "closed": row.closed,
        "sla_breached": row.sla_breached,
    }


@router.get("/overview")
async def get_overview(
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """Общая сводка KPI."""
    result = await db.execute(
        select(
            func.count(Request.id).label("total"),
            func.count(case((Request.status == RequestStatus.new, 1))).label("new"),
            func.count(case((Request.status == RequestStatus.in_progress, 1))).label("in_progress"),
            func.count(case((Request.status == RequestStatus.resolved, 1))).label("resolved"),
            func.count(case((Request.sla_breached == True, 1))).label("sla_breached"),
            func.avg(Request.satisfaction_score).label("avg_satisfaction"),
        )
    )
    row = result.one()
    return {
        "total": row.total,
        "new": row.new,
        "in_progress": row.in_progress,
        "resolved": row.resolved,
        "sla_breached": row.sla_breached,
        "avg_satisfaction": round(float(row.avg_satisfaction or 0), 2),
    }


@router.get("/volume")
async def get_volume(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """Объём заявок по дням за последние N дней."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date_trunc("day", Request.created_at).label("day"),
            func.count(Request.id).label("count"),
        )
        .where(Request.created_at >= since)
        .group_by(func.date_trunc("day", Request.created_at))
        .order_by(func.date_trunc("day", Request.created_at))
    )
    rows = result.all()
    return [{"day": r.day.date().isoformat(), "count": r.count} for r in rows]


@router.get("/by-department")
async def get_by_department(
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """Количество заявок по отделам."""
    from models.department import Department
    result = await db.execute(
        select(
            Department.name,
            Department.icon_emoji,
            func.count(Request.id).label("count"),
        )
        .join(Request, Request.department_id == Department.id)
        .group_by(Department.name, Department.icon_emoji)
        .order_by(func.count(Request.id).desc())
    )
    return [
        {"department": r.name, "emoji": r.icon_emoji, "count": r.count}
        for r in result.all()
    ]


@router.get("/sla")
async def get_sla_stats(
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """Статистика SLA."""
    result = await db.execute(
        select(
            func.count(Request.id).label("total"),
            func.count(case((Request.sla_breached == True, 1))).label("breached"),
            func.count(case((Request.sla_breached == False, 1))).label("on_time"),
        )
        .where(Request.sla_deadline.is_not(None))
    )
    row = result.one()
    compliance = 0.0
    if row.total > 0:
        compliance = round((row.on_time / row.total) * 100, 1)
    return {
        "total_with_sla": row.total,
        "breached": row.breached,
        "on_time": row.on_time,
        "compliance_percent": compliance,
    }


@router.get("/agents")
async def get_agents_stats(
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """Нагрузка агентов: открытые заявки."""
    from models.user import User
    result = await db.execute(
        select(
            User.first_name,
            User.username,
            func.count(Request.id).label("open_count"),
        )
        .join(Request, Request.assigned_to_id == User.id)
        .where(Request.status.in_([RequestStatus.new, RequestStatus.open, RequestStatus.in_progress]))
        .group_by(User.first_name, User.username)
        .order_by(func.count(Request.id).desc())
    )
    return [
        {"name": r.first_name, "username": r.username, "open_count": r.open_count}
        for r in result.all()
    ]
