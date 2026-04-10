"""add case responsibles and user profile ai snapshots

Revision ID: 006
Revises: 005
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("flow_cases", sa.Column("responsible_user_id", sa.Integer(), nullable=True))
    op.add_column("flow_cases", sa.Column("assigned_by_user_id", sa.Integer(), nullable=True))
    op.add_column("flow_cases", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_flow_cases_responsible_user", "flow_cases", "users", ["responsible_user_id"], ["id"])
    op.create_foreign_key("fk_flow_cases_assigned_by_user", "flow_cases", "users", ["assigned_by_user_id"], ["id"])

    op.create_table(
        "user_profile_ai_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("dominant_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("assigned_case_stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_user_profile_ai_snapshots_user_id"),
    )

    op.execute(
        """
        UPDATE flow_signals
        SET submitter_id = requests.submitter_id
        FROM requests
        WHERE flow_signals.request_id = requests.id
          AND flow_signals.submitter_id IS NULL
          AND requests.submitter_id IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE flow_cases
        SET responsible_user_id = requests.assigned_to_id,
            assigned_at = NOW()
        FROM requests
        WHERE flow_cases.request_id = requests.id
          AND flow_cases.responsible_user_id IS NULL
          AND requests.assigned_to_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_table("user_profile_ai_snapshots")
    op.drop_constraint("fk_flow_cases_assigned_by_user", "flow_cases", type_="foreignkey")
    op.drop_constraint("fk_flow_cases_responsible_user", "flow_cases", type_="foreignkey")
    op.drop_column("flow_cases", "assigned_at")
    op.drop_column("flow_cases", "assigned_by_user_id")
    op.drop_column("flow_cases", "responsible_user_id")
