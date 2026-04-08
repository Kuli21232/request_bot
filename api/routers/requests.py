"""CRUD эндпоинты для заявок."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_db, get_current_user, require_agent
from models.request import Request, RequestComment, RequestHistory
from models.enums import RequestStatus, RequestPriority, UserRole

router = APIRouter(prefix="/api/v1/requests", tags=["requests"])


# ── Pydantic схемы ─────────────────────────────────────────────

class RequestOut(BaseModel):
    id: int
    ticket_number: str
    subject: Optional[str]
    body: str
    status: str
    priority: str
    department_id: int
    submitter_id: int
    assigned_to_id: Optional[int]
    sla_deadline: Optional[str]
    sla_breached: bool
    is_duplicate: bool
    created_at: str

    class Config:
        from_attributes = True


class CommentIn(BaseModel):
    body: str
    is_internal: bool = False


class StatusUpdate(BaseModel):
    status: str


class PriorityUpdate(BaseModel):
    priority: str


class AssignUpdate(BaseModel):
    agent_id: int


class RateRequest(BaseModel):
    score: int
    comment: Optional[str] = None


# ── Эндпоинты ─────────────────────────────────────────────────

@router.get("")
async def list_requests(
    status: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to_me: bool = Query(False),
    my: bool = Query(False),
    sla_breached: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    search: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Request).options(
        selectinload(Request.submitter),
        selectinload(Request.assigned_to),
        selectinload(Request.department),
    )

    # Пользователи видят только свои заявки; или если запрошено my=true
    if current_user.role == UserRole.user or my:
        q = q.where(Request.submitter_id == current_user.id)

    if sla_breached is not None:
        q = q.where(Request.sla_breached == sla_breached)

    if status:
        q = q.where(Request.status == RequestStatus(status))
    if department_id:
        q = q.where(Request.department_id == department_id)
    if priority:
        q = q.where(Request.priority == RequestPriority(priority))
    if assigned_to_me:
        q = q.where(Request.assigned_to_id == current_user.id)
    if search:
        q = q.where(
            Request.body.ilike(f"%{search}%") |
            Request.ticket_number.ilike(f"%{search}%") |
            Request.subject.ilike(f"%{search}%")
        )

    # Общее количество
    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    q = q.order_by(Request.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(q)
    items = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_request(r) for r in items],
    }


@router.get("/{request_id}")
async def get_request(
    request_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Request)
        .options(
            selectinload(Request.submitter),
            selectinload(Request.assigned_to),
            selectinload(Request.department),
            selectinload(Request.comments).selectinload(RequestComment.author),
            selectinload(Request.history),
        )
        .where(Request.id == request_id)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    if current_user.role == UserRole.user and req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _serialize_request_full(req, current_user)


@router.post("/{request_id}/comments")
async def add_comment(
    request_id: int,
    body: CommentIn,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Request).where(Request.id == request_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    if current_user.role == UserRole.user and req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Только агенты могут делать внутренние комментарии
    is_internal = body.is_internal and current_user.role in (
        UserRole.agent, UserRole.supervisor, UserRole.admin
    )

    comment = RequestComment(
        request_id=request_id,
        author_id=current_user.id,
        body=body.body,
        is_internal=is_internal,
    )
    db.add(comment)

    if req.first_response_at is None and not is_internal:
        from datetime import datetime, timezone
        req.first_response_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(comment)
    return {"id": comment.id, "body": comment.body, "is_internal": comment.is_internal}


@router.patch("/{request_id}/status")
async def update_status(
    request_id: int,
    body: StatusUpdate,
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Request).where(Request.id == request_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    try:
        new_status = RequestStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    old_status = req.status
    req.status = new_status

    if new_status in (RequestStatus.resolved, RequestStatus.closed):
        from datetime import datetime, timezone
        req.resolved_at = datetime.now(timezone.utc)

    db.add(RequestHistory(
        request_id=request_id,
        actor_id=current_user.id,
        action="status_change",
        field_name="status",
        old_value=old_status.value,
        new_value=new_status.value,
    ))
    await db.commit()
    return {"status": new_status.value}


@router.patch("/{request_id}/priority")
async def update_priority(
    request_id: int,
    body: PriorityUpdate,
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Request).where(Request.id == request_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        new_priority = RequestPriority(body.priority)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid priority")

    old_priority = req.priority
    req.priority = new_priority
    db.add(RequestHistory(
        request_id=request_id,
        actor_id=current_user.id,
        action="priority_change",
        field_name="priority",
        old_value=old_priority.value,
        new_value=new_priority.value,
    ))
    await db.commit()
    return {"priority": new_priority.value}


@router.post("/{request_id}/assign")
async def assign_request(
    request_id: int,
    body: AssignUpdate,
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Request).where(Request.id == request_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Not found")

    old_agent = req.assigned_to_id
    req.assigned_to_id = body.agent_id
    if req.status == RequestStatus.new:
        req.status = RequestStatus.open
    db.add(RequestHistory(
        request_id=request_id,
        actor_id=current_user.id,
        action="assignment",
        field_name="assigned_to_id",
        old_value=str(old_agent),
        new_value=str(body.agent_id),
    ))
    await db.commit()
    return {"assigned_to_id": body.agent_id}


@router.post("/{request_id}/rate")
async def rate_request(
    request_id: int,
    body: RateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.score < 1 or body.score > 5:
        raise HTTPException(status_code=400, detail="Score must be 1-5")

    result = await db.execute(select(Request).where(Request.id == request_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Not found")

    if req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    req.satisfaction_score = body.score
    req.satisfaction_comment = body.comment
    await db.commit()
    return {"score": body.score}


@router.get("/{request_id}/history")
async def get_history(
    request_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RequestHistory)
        .where(RequestHistory.request_id == request_id)
        .order_by(RequestHistory.created_at)
    )
    history = result.scalars().all()
    return [
        {
            "action": h.action,
            "field_name": h.field_name,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "created_at": h.created_at.isoformat(),
        }
        for h in history
    ]


# ── Публичный эндпоинт (с внешнего сайта) ────────────────────

class PublicSubmitRequest(BaseModel):
    department_slug: str
    name: str
    email: Optional[str] = None
    body: str


@router.post("/public/submit", include_in_schema=False)
async def public_submit(body: PublicSubmitRequest, db: AsyncSession = Depends(get_db)):
    """Приём заявок с внешнего сайта по slug отдела."""
    from models.department import Department
    from models.user import User

    result = await db.execute(
        select(Department).where(Department.name.ilike(body.department_slug))
    )
    dept = result.scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found")

    # Ищем или создаём системного пользователя для заявок с сайта
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            first_name=body.name,
            email=body.email,
        )
        db.add(user)
        await db.flush()

    req = Request(
        ticket_number="",
        group_id=dept.group_id,
        department_id=dept.id,
        submitter_id=user.id,
        body=f"[Сайт] {body.body}",
        telegram_message_id=0,
        telegram_chat_id=0,
    )
    db.add(req)
    await db.flush()
    await db.commit()
    await db.refresh(req)

    return {"ticket_number": req.ticket_number, "id": req.id}


# ── Вспомогательные функции ────────────────────────────────────

def _serialize_request(req: Request) -> dict:
    return {
        "id": req.id,
        "ticket_number": req.ticket_number,
        "subject": req.subject or req.ai_subject,
        "body": req.body[:200],
        "status": req.status.value,
        "priority": req.priority.value,
        "department_id": req.department_id,
        "department_name": req.department.name if req.department else None,
        "submitter_id": req.submitter_id,
        "submitter_name": req.submitter.first_name if req.submitter else None,
        "assigned_to_id": req.assigned_to_id,
        "assigned_to_name": req.assigned_to.first_name if req.assigned_to else None,
        "sla_deadline": req.sla_deadline.isoformat() if req.sla_deadline else None,
        "sla_breached": req.sla_breached,
        "is_duplicate": req.is_duplicate,
        "ai_category": getattr(req, "ai_category", None),
        "ai_sentiment": getattr(req, "ai_sentiment", None),
        "ai_subject": getattr(req, "ai_subject", None),
        "satisfaction_score": req.satisfaction_score,
        "created_at": req.created_at.isoformat(),
        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
    }


def _serialize_request_full(req: Request, current_user) -> dict:
    data = _serialize_request(req)
    data["body"] = req.body
    data["attachments"] = req.attachments or []
    data["current_user_role"] = current_user.role.value
    data["first_response_at"] = req.first_response_at.isoformat() if req.first_response_at else None
    data["resolved_at"] = req.resolved_at.isoformat() if req.resolved_at else None
    data["comments"] = [
        {
            "id": c.id,
            "body": c.body,
            "is_internal": c.is_internal,
            "is_system": c.is_system,
            "author": c.author.first_name if c.author else "Система",
            "author_id": c.author_id,
            "created_at": c.created_at.isoformat(),
        }
        for c in req.comments
        if not c.is_internal or current_user.role.value in ("agent", "supervisor", "admin")
    ]
    data["history"] = [
        {
            "action": h.action,
            "field_name": h.field_name,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "created_at": h.created_at.isoformat(),
        }
        for h in (req.history or [])
    ]
    return data
