from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.knowledge import KnowledgeArticle, UserProfileNote, UserProfileSubscription
from models.user import User


class KnowledgeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_articles(self, *, published_only: bool = True, search: str | None = None) -> list[KnowledgeArticle]:
        query = select(KnowledgeArticle).options(
            selectinload(KnowledgeArticle.created_by),
            selectinload(KnowledgeArticle.updated_by),
        )
        if published_only:
            query = query.where(KnowledgeArticle.is_published == True)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    KnowledgeArticle.title.ilike(pattern),
                    KnowledgeArticle.summary.ilike(pattern),
                    KnowledgeArticle.body.ilike(pattern),
                )
            )
        query = query.order_by(KnowledgeArticle.updated_at.desc(), KnowledgeArticle.id.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_article(self, article_id: int) -> KnowledgeArticle | None:
        result = await self.session.execute(
            select(KnowledgeArticle)
            .options(
                selectinload(KnowledgeArticle.created_by),
                selectinload(KnowledgeArticle.updated_by),
            )
            .where(KnowledgeArticle.id == article_id)
        )
        return result.scalar_one_or_none()

    async def create_article(
        self,
        *,
        title: str,
        slug: str,
        body: str,
        summary: str | None,
        tags: list[str],
        audience: str,
        is_published: bool,
        actor_id: int | None,
    ) -> KnowledgeArticle:
        article = KnowledgeArticle(
            title=title,
            slug=slug,
            body=body,
            summary=summary,
            tags=tags,
            audience=audience,
            is_published=is_published,
            created_by_id=actor_id,
            updated_by_id=actor_id,
        )
        self.session.add(article)
        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def update_article(self, article: KnowledgeArticle, payload: dict, actor_id: int | None) -> KnowledgeArticle:
        for field in ("title", "slug", "body", "summary", "tags", "audience", "is_published"):
            if field in payload:
                setattr(article, field, payload[field])
        article.updated_by_id = actor_id
        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def add_profile_note(
        self,
        *,
        target_user_id: int,
        author_id: int | None,
        body: str,
        notify_target: bool = False,
    ) -> UserProfileNote:
        note = UserProfileNote(
            target_user_id=target_user_id,
            author_id=author_id,
            body=body,
            notify_target=notify_target,
        )
        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def list_profile_notes(self, target_user_id: int, *, limit: int = 20) -> list[UserProfileNote]:
        result = await self.session.execute(
            select(UserProfileNote)
            .options(selectinload(UserProfileNote.author))
            .where(UserProfileNote.target_user_id == target_user_id)
            .order_by(UserProfileNote.created_at.desc(), UserProfileNote.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_subscription(self, watcher_user_id: int, target_user_id: int) -> UserProfileSubscription | None:
        result = await self.session.execute(
            select(UserProfileSubscription).where(
                UserProfileSubscription.watcher_user_id == watcher_user_id,
                UserProfileSubscription.target_user_id == target_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_subscription(
        self,
        *,
        watcher_user_id: int,
        target_user_id: int,
        active: bool = True,
    ) -> UserProfileSubscription:
        subscription = await self.get_subscription(watcher_user_id, target_user_id)
        if subscription is None:
            subscription = UserProfileSubscription(
                watcher_user_id=watcher_user_id,
                target_user_id=target_user_id,
                is_active=active,
            )
            self.session.add(subscription)
        else:
            subscription.is_active = active
        await self.session.commit()
        await self.session.refresh(subscription)
        return subscription

    async def list_active_watchers(self, target_user_id: int) -> list[User]:
        result = await self.session.execute(
            select(User)
            .join(UserProfileSubscription, UserProfileSubscription.watcher_user_id == User.id)
            .where(UserProfileSubscription.target_user_id == target_user_id)
            .where(UserProfileSubscription.is_active == True)
        )
        return list(result.scalars().all())
