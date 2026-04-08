"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    op.execute("CREATE TYPE user_role AS ENUM ('user', 'agent', 'supervisor', 'admin')")
    op.execute(
        "CREATE TYPE request_status AS ENUM "
        "('new', 'open', 'in_progress', 'waiting_for_user', 'resolved', 'closed', 'duplicate')"
    )
    op.execute(
        "CREATE TYPE request_priority AS ENUM ('low', 'normal', 'high', 'critical')"
    )

    # telegram_groups
    op.create_table(
        "telegram_groups",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("telegram_chat_id", sa.BigInteger, unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("telegram_user_id", sa.BigInteger, unique=True, nullable=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("language_code", sa.String(10), default="ru", nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("user", "agent", "supervisor", "admin", name="user_role", create_type=False),
            default="user", nullable=False,
        ),
        sa.Column("is_banned", sa.Boolean, default=False, nullable=False),
        sa.Column(
            "notification_preferences",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text(
                "'{\"on_status_change\": true, \"on_assignment\": true, "
                "\"on_comment\": true, \"digest_frequency\": \"daily\"}'::jsonb"
            ),
        ),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # departments
    op.create_table(
        "departments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger, sa.ForeignKey("telegram_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_topic_id", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon_emoji", sa.String(10), nullable=True),
        sa.Column("color_hex", sa.String(7), default="#6B7280", nullable=False),
        sa.Column("sla_hours", sa.Integer, default=24, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("sort_order", sa.Integer, default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "telegram_topic_id", name="uq_dept_group_topic"),
    )

    # requests
    op.create_table(
        "requests",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("ticket_number", sa.String(30), unique=True, nullable=False),
        sa.Column("group_id", sa.BigInteger, sa.ForeignKey("telegram_groups.id"), nullable=False),
        sa.Column("department_id", sa.BigInteger, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("submitter_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("subject", sa.String(512), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("attachments", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("telegram_message_id", sa.Integer, nullable=False),
        sa.Column("telegram_topic_id", sa.Integer, nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger, nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "new", "open", "in_progress", "waiting_for_user",
                "resolved", "closed", "duplicate",
                name="request_status", create_type=False,
            ),
            default="new", nullable=False,
        ),
        sa.Column(
            "priority",
            postgresql.ENUM("low", "normal", "high", "critical", name="request_priority", create_type=False),
            default="normal", nullable=False,
        ),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_breached", sa.Boolean, default=False, nullable=False),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_duplicate", sa.Boolean, default=False, nullable=False),
        sa.Column("duplicate_of_id", sa.BigInteger, sa.ForeignKey("requests.id"), nullable=True),
        sa.Column("similarity_score", sa.Float, nullable=True),
        sa.Column("auto_routed", sa.Boolean, default=False, nullable=False),
        sa.Column("routing_reason", sa.Text, nullable=True),
        sa.Column("ai_subject", sa.String(512), nullable=True),
        sa.Column("ai_category", sa.String(255), nullable=True),
        sa.Column("ai_sentiment", sa.String(50), nullable=True),
        sa.Column("satisfaction_score", sa.Integer, nullable=True),
        sa.Column("satisfaction_comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Автогенерация ticket_number через PostgreSQL-функцию
    op.execute("CREATE SEQUENCE IF NOT EXISTS ticket_seq START 1")

    op.execute("""
        CREATE OR REPLACE FUNCTION generate_ticket_number()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.ticket_number := 'REQ-' || TO_CHAR(NOW(), 'YYYY') || '-'
                                 || LPAD(nextval('ticket_seq')::TEXT, 5, '0');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER set_ticket_number
        BEFORE INSERT ON requests
        FOR EACH ROW
        WHEN (NEW.ticket_number IS NULL OR NEW.ticket_number = '')
        EXECUTE FUNCTION generate_ticket_number()
    """)

    # Автовычисление sla_deadline
    op.execute("""
        CREATE OR REPLACE FUNCTION compute_sla_deadline()
        RETURNS TRIGGER AS $$
        DECLARE dept_sla INTEGER;
        BEGIN
            SELECT sla_hours INTO dept_sla FROM departments WHERE id = NEW.department_id;
            NEW.sla_deadline := NOW() + (COALESCE(dept_sla, 24) * INTERVAL '1 hour');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER set_sla_deadline
        BEFORE INSERT ON requests
        FOR EACH ROW
        EXECUTE FUNCTION compute_sla_deadline()
    """)

    # request_comments
    op.create_table(
        "request_comments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_internal", sa.Boolean, default=False, nullable=False),
        sa.Column("is_system", sa.Boolean, default=False, nullable=False),
        sa.Column("attachments", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("telegram_message_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # request_history
    op.create_table(
        "request_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # routing_rules
    op.create_table(
        "routing_rules",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("department_id", sa.BigInteger, sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pattern", sa.Text, nullable=False),
        sa.Column("pattern_type", sa.String(20), default="keyword", nullable=False),
        sa.Column(
            "priority_boost",
            postgresql.ENUM("low", "normal", "high", "critical", name="request_priority", create_type=False),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("match_count", sa.Integer, default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # canned_responses
    op.create_table(
        "canned_responses",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("department_id", sa.BigInteger, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("tags", sa.String(500), nullable=True),
        sa.Column("use_count", sa.Integer, default=0, nullable=False),
        sa.Column("created_by_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # department_agents
    op.create_table(
        "department_agents",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("department_id", sa.BigInteger, sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_supervisor", sa.Boolean, default=False, nullable=False),
        sa.UniqueConstraint("department_id", "agent_id", name="uq_dept_agent"),
    )

    # notifications_queue
    op.create_table(
        "notifications_queue",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel", sa.String(20), default="telegram", nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("retry_count", sa.Integer, default=0, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )

    # Индексы
    op.create_index("idx_requests_status", "requests", ["status"])
    op.create_index("idx_requests_department", "requests", ["department_id"])
    op.create_index("idx_requests_submitter", "requests", ["submitter_id"])
    op.create_index("idx_requests_assigned", "requests", ["assigned_to_id"])
    op.create_index("idx_requests_created", "requests", ["created_at"])
    op.create_index("idx_requests_telegram", "requests", ["telegram_chat_id", "telegram_message_id"])
    op.create_index("idx_comments_request", "request_comments", ["request_id"])
    op.create_index("idx_history_request", "request_history", ["request_id"])


def downgrade() -> None:
    op.drop_table("notifications_queue")
    op.drop_table("department_agents")
    op.drop_table("canned_responses")
    op.drop_table("routing_rules")
    op.drop_table("request_history")
    op.drop_table("request_comments")
    op.execute("DROP TRIGGER IF EXISTS set_sla_deadline ON requests")
    op.execute("DROP TRIGGER IF EXISTS set_ticket_number ON requests")
    op.execute("DROP FUNCTION IF EXISTS compute_sla_deadline")
    op.execute("DROP FUNCTION IF EXISTS generate_ticket_number")
    op.execute("DROP SEQUENCE IF EXISTS ticket_seq")
    op.drop_table("requests")
    op.drop_table("departments")
    op.drop_table("users")
    op.drop_table("telegram_groups")
    op.execute("DROP TYPE IF EXISTS request_priority")
    op.execute("DROP TYPE IF EXISTS request_status")
    op.execute("DROP TYPE IF EXISTS user_role")
