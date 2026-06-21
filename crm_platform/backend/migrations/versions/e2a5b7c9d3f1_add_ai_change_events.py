"""add ai change events

Revision ID: e2a5b7c9d3f1
Revises: d1f4a6b8c2e0
Create Date: 2026-05-17 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "e2a5b7c9d3f1"
down_revision: Union[str, Sequence[str], None] = "d1f4a6b8c2e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "ai_change_events" in inspector.get_table_names():
        return
    op.create_table(
        "ai_change_events",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("affected_artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("rollback_status", sa.String(), nullable=False, server_default="available"),
        sa.Column("rollback_reason", sa.Text(), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["access_workspaces.id"]),
        sa.ForeignKeyConstraint(["proposal_id"], ["ai_change_proposals.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["access_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_change_events_workspace_id", "ai_change_events", ["workspace_id"], unique=False)
    op.create_index("ix_ai_change_events_proposal_id", "ai_change_events", ["proposal_id"], unique=False)
    op.create_index("ix_ai_change_events_conversation_id", "ai_change_events", ["conversation_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "ai_change_events" not in inspector.get_table_names():
        return
    op.drop_index("ix_ai_change_events_conversation_id", table_name="ai_change_events")
    op.drop_index("ix_ai_change_events_proposal_id", table_name="ai_change_events")
    op.drop_index("ix_ai_change_events_workspace_id", table_name="ai_change_events")
    op.drop_table("ai_change_events")
