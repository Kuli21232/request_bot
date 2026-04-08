"""add flow entities

Revision ID: 002
Revises: 001
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flow_cases",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger, sa.ForeignKey("telegram_groups.id"), nullable=False),
        sa.Column("department_id", sa.BigInteger, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("requests.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("kind", sa.String(64), nullable=False, server_default="signal_cluster"),
        sa.Column("suggested_owner_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("owners", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("stores_affected", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("ai_labels", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("recommended_action", sa.Text, nullable=True),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("last_signal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signal_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("media_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_critical", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "flow_signals",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger, sa.ForeignKey("telegram_groups.id"), nullable=False),
        sa.Column("department_id", sa.BigInteger, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("submitter_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("requests.id"), nullable=True),
        sa.Column("case_id", sa.BigInteger, sa.ForeignKey("flow_cases.id"), nullable=True),
        sa.Column("duplicate_signal_id", sa.BigInteger, sa.ForeignKey("flow_signals.id"), nullable=True),
        sa.Column("source_topic_id", sa.Integer, nullable=True),
        sa.Column("source_message_id", sa.Integer, nullable=False),
        sa.Column("source_chat_id", sa.BigInteger, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("store", sa.String(255), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False, server_default="request"),
        sa.Column("importance", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("actionability", sa.String(64), nullable=False, server_default="digest_only"),
        sa.Column("case_key", sa.String(255), nullable=True),
        sa.Column("topic_label", sa.String(255), nullable=True),
        sa.Column("recommended_action", sa.Text, nullable=True),
        sa.Column("ai_summary", sa.Text, nullable=True),
        sa.Column("ai_labels", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("entities", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("media_flags", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("attachments", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("has_media", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("requires_attention", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_noise", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("digest_bucket", sa.String(64), nullable=True),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("happened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_flow_cases_status", "flow_cases", ["status"])
    op.create_index("idx_flow_cases_last_signal", "flow_cases", ["last_signal_at"])
    op.create_index("idx_flow_signals_kind", "flow_signals", ["kind"])
    op.create_index("idx_flow_signals_case", "flow_signals", ["case_id"])
    op.create_index("idx_flow_signals_happened_at", "flow_signals", ["happened_at"])
    op.create_index("idx_flow_signals_topic", "flow_signals", ["source_chat_id", "source_topic_id"])


def downgrade() -> None:
    op.drop_index("idx_flow_signals_topic", table_name="flow_signals")
    op.drop_index("idx_flow_signals_happened_at", table_name="flow_signals")
    op.drop_index("idx_flow_signals_case", table_name="flow_signals")
    op.drop_index("idx_flow_signals_kind", table_name="flow_signals")
    op.drop_index("idx_flow_cases_last_signal", table_name="flow_cases")
    op.drop_index("idx_flow_cases_status", table_name="flow_cases")
    op.drop_table("flow_signals")
    op.drop_table("flow_cases")
