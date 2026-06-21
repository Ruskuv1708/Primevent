"""add animator unavailability table

Revision ID: c8a7d6e5b4f3
Revises: bbf02a9c4d11
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "c8a7d6e5b4f3"
down_revision: Union[str, Sequence[str], None] = "bbf02a9c4d11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "animator_unavailability" not in tables:
        op.create_table(
            "animator_unavailability",
            sa.Column("animator_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("unavailable_date", sa.Date(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.ForeignKeyConstraint(["animator_id"], ["access_users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["access_workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_animator_unavailability_workspace_date",
            "animator_unavailability",
            ["workspace_id", "unavailable_date", "start_time"],
            unique=False,
        )
        op.create_index(
            "ix_animator_unavailability_animator_date",
            "animator_unavailability",
            ["animator_id", "unavailable_date"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "animator_unavailability" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("animator_unavailability")}
        if "ix_animator_unavailability_workspace_date" in indexes:
            op.drop_index("ix_animator_unavailability_workspace_date", table_name="animator_unavailability")
        if "ix_animator_unavailability_animator_date" in indexes:
            op.drop_index("ix_animator_unavailability_animator_date", table_name="animator_unavailability")
        op.drop_table("animator_unavailability")
