"""Управление отделами."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_current_user, require_admin
from models.department import Department
from models.routing import RoutingRule

router = APIRouter(prefix="/api/v1/departments", tags=["departments"])


class DepartmentOut(BaseModel):
    id: int
    name: str
    icon_emoji: Optional[str]
    color_hex: str
    sla_hours: int
    is_active: bool
    telegram_topic_id: int


class RoutingRuleIn(BaseModel):
    pattern: str
    pattern_type: str = "keyword"


@router.get("")
async def list_departments(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Department).where(Department.is_active == True).order_by(Department.sort_order)
    )
    depts = result.scalars().all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "icon_emoji": d.icon_emoji,
            "color_hex": d.color_hex,
            "sla_hours": d.sla_hours,
            "telegram_topic_id": d.telegram_topic_id,
        }
        for d in depts
    ]


@router.get("/{dept_id}/routing-rules")
async def get_routing_rules(
    dept_id: int,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoutingRule)
        .where(RoutingRule.department_id == dept_id)
        .order_by(RoutingRule.match_count.desc())
    )
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "pattern": r.pattern,
            "pattern_type": r.pattern_type,
            "is_active": r.is_active,
            "match_count": r.match_count,
        }
        for r in rules
    ]


@router.post("/{dept_id}/routing-rules")
async def add_routing_rule(
    dept_id: int,
    body: RoutingRuleIn,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rule = RoutingRule(
        department_id=dept_id,
        pattern=body.pattern,
        pattern_type=body.pattern_type,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, "pattern": rule.pattern}


@router.delete("/{dept_id}/routing-rules/{rule_id}")
async def delete_routing_rule(
    dept_id: int,
    rule_id: int,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoutingRule).where(
            RoutingRule.id == rule_id,
            RoutingRule.department_id == dept_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
    return {"deleted": rule_id}
