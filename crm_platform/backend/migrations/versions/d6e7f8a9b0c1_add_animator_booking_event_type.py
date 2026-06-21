"""add animator booking event type

Revision ID: d6e7f8a9b0c1
Revises: c8a7d6e5b4f3
Create Date: 2026-06-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c8a7d6e5b4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "animator_bookings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("animator_bookings")}
    if "event_type" not in columns:
        op.add_column(
            "animator_bookings",
            sa.Column("event_type", sa.String(), nullable=False, server_default="order"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "animator_bookings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("animator_bookings")}
    if "event_type" in columns:
        op.drop_column("animator_bookings", "event_type")
