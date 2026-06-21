"""add animator bookings table

Revision ID: bbf02a9c4d11
Revises: 8d3f2a1c9b0e
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "bbf02a9c4d11"
down_revision: Union[str, Sequence[str], None] = "8d3f2a1c9b0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "animator_bookings" not in tables:
        op.create_table(
            "animator_bookings",
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("client_name", sa.String(), nullable=False),
            sa.Column("client_phone", sa.String(), nullable=True),
            sa.Column("event_date", sa.Date(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), nullable=False),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("program_name", sa.String(), nullable=True),
            sa.Column("price", sa.Integer(), nullable=True),
            sa.Column("prepayment", sa.Integer(), nullable=True),
            sa.Column("payment_status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("inventory_notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="confirmed"),
            sa.Column("color", sa.String(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "assigned_animator_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.ForeignKeyConstraint(["workspace_id"], ["access_workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_animator_bookings_workspace_date_start",
            "animator_bookings",
            ["workspace_id", "event_date", "start_time"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "animator_bookings" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("animator_bookings")}
        if "ix_animator_bookings_workspace_date_start" in indexes:
            op.drop_index("ix_animator_bookings_workspace_date_start", table_name="animator_bookings")
        op.drop_table("animator_bookings")
