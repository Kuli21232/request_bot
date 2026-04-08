"""add topic automation core

Revision ID: 003
Revises: 002
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_topics",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger, sa.ForeignKey("telegram_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_topic_id", sa.Integer, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("icon_emoji", sa.String(32), nullable=True),
        sa.Column("topic_kind", sa.String(64), nullable=False, server_default="mixed"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("media_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("signal_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("profile_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "telegram_topic_id", name="uq_telegram_topic_group_thread"),
    )

    op.create_table(
        "topic_ai_profiles",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("topic_id", sa.BigInteger, sa.ForeignKey("telegram_topics.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("preferred_department_id", sa.BigInteger, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("profile_summary", sa.Text, nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("allowed_signal_types", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("default_actions", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("priority_rules", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("media_policy", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("examples", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("learning_snapshot", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("behavior_rules", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence_threshold", sa.Float, nullable=False, server_default="0.65"),
        sa.Column("auto_learn_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_retrained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_rule_update_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("flow_cases", sa.Column("primary_topic_id", sa.BigInteger, sa.ForeignKey("telegram_topics.id"), nullable=True))
    op.add_column("flow_signals", sa.Column("topic_id", sa.BigInteger, sa.ForeignKey("telegram_topics.id"), nullable=True))

    op.create_table(
        "signal_media",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("signal_id", sa.BigInteger, sa.ForeignKey("flow_signals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("telegram_file_id", sa.String(255), nullable=True),
        sa.Column("telegram_file_path", sa.Text, nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("original_size", sa.Integer, nullable=True),
        sa.Column("compressed_size", sa.Integer, nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("preview_bytes", sa.LargeBinary, nullable=True),
        sa.Column("storage_meta", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_topics_group", "telegram_topics", ["group_id"])
    op.create_index("idx_topics_last_seen", "telegram_topics", ["last_seen_at"])
    op.create_index("idx_flow_cases_primary_topic", "flow_cases", ["primary_topic_id"])
    op.create_index("idx_flow_signals_topic_id", "flow_signals", ["topic_id"])
    op.create_index("idx_signal_media_signal", "signal_media", ["signal_id"])


def downgrade() -> None:
    op.drop_index("idx_signal_media_signal", table_name="signal_media")
    op.drop_index("idx_flow_signals_topic_id", table_name="flow_signals")
    op.drop_index("idx_flow_cases_primary_topic", table_name="flow_cases")
    op.drop_index("idx_topics_last_seen", table_name="telegram_topics")
    op.drop_index("idx_topics_group", table_name="telegram_topics")
    op.drop_table("signal_media")
    op.drop_column("flow_signals", "topic_id")
    op.drop_column("flow_cases", "primary_topic_id")
    op.drop_table("topic_ai_profiles")
    op.drop_table("telegram_topics")
