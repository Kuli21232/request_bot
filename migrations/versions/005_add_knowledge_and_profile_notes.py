"""add knowledge articles and user profile notes

Revision ID: 005
Revises: 004
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.String(length=512), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("audience", sa.String(length=50), nullable=False, server_default="all"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_knowledge_articles_slug"),
    )

    op.create_table(
        "user_profile_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("notify_target", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "user_profile_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("watcher_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[\"profile_note\"]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("watcher_user_id", "target_user_id", name="uq_profile_subscription"),
    )

    op.execute(
        """
        INSERT INTO knowledge_articles (slug, title, summary, body, tags, audience, is_published)
        VALUES
        (
            'intro-flowdesk',
            'Как работает бот',
            'Короткое объяснение, что делает бот в Telegram.',
            'Бот автоматически разбирает сообщения из топиков, выделяет важное, объединяет повторы в ситуации и при необходимости создает рабочие задачи. Если вы просто пишете в тематический топик, система сама решает, нужно ли это отправлять в работу, держать в сводке или связать с уже известной ситуацией.',
            '["бот", "инструктаж", "поток"]'::jsonb,
            'all',
            true
        ),
        (
            'employees-profiles',
            'Профили сотрудников и уведомления',
            'Как смотреть профили, оставлять заметки и подписываться на обновления.',
            'Через бота можно открыть профиль сотрудника, посмотреть его базовую информацию, последние заметки и подписаться на уведомления. Руководители и исполнители могут оставлять заметки в профиле, а подписчики получают уведомления в Telegram, когда появляется новая заметка.',
            '["сотрудники", "профили", "уведомления"]'::jsonb,
            'agent',
            true
        )
        """
    )


def downgrade() -> None:
    op.drop_table("user_profile_subscriptions")
    op.drop_table("user_profile_notes")
    op.drop_table("knowledge_articles")
