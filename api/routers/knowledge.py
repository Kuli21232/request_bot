from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_current_user, require_admin
from bot.database.repositories.knowledge_repo import KnowledgeRepository

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class KnowledgeIn(BaseModel):
    title: str
    slug: str
    body: str
    summary: str | None = None
    tags: list[str] = []
    audience: str = "all"
    is_published: bool = True


@router.get("")
async def list_articles(
    search: str | None = Query(None),
    include_drafts: bool = Query(False),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = KnowledgeRepository(db)
    articles = await repo.list_articles(
        published_only=not include_drafts or current_user.role.value == "user",
        search=search,
    )
    return [_serialize_article(article) for article in articles]


@router.get("/{article_id}")
async def get_article(
    article_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = KnowledgeRepository(db)
    article = await repo.get_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    if not article.is_published and current_user.role.value == "user":
        raise HTTPException(status_code=403, detail="Access denied")
    return _serialize_article(article)


@router.post("")
async def create_article(
    payload: KnowledgeIn,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = KnowledgeRepository(db)
    article = await repo.create_article(
        title=payload.title,
        slug=payload.slug,
        body=payload.body,
        summary=payload.summary,
        tags=payload.tags,
        audience=payload.audience,
        is_published=payload.is_published,
        actor_id=current_user.id,
    )
    return _serialize_article(article)


@router.patch("/{article_id}")
async def update_article(
    article_id: int,
    payload: dict,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = KnowledgeRepository(db)
    article = await repo.get_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    updated = await repo.update_article(article, payload, current_user.id)
    return _serialize_article(updated)


def _serialize_article(article) -> dict:
    return {
        "id": article.id,
        "slug": article.slug,
        "title": article.title,
        "summary": article.summary,
        "body": article.body,
        "tags": article.tags or [],
        "audience": article.audience,
        "is_published": article.is_published,
        "created_by": article.created_by.first_name if article.created_by else None,
        "updated_by": article.updated_by.first_name if article.updated_by else None,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "updated_at": article.updated_at.isoformat() if article.updated_at else None,
    }
