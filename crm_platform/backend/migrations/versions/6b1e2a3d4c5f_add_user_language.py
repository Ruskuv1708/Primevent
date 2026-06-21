"""add user language preference

Revision ID: 6b1e2a3d4c5f
Revises: 2b7c8d9e0f12
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "6b1e2a3d4c5f"
down_revision: Union[str, Sequence[str], None] = "2b7c8d9e0f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "access_users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("access_users")}
    if "language" not in columns:
        op.add_column(
            "access_users",
            sa.Column("language", sa.String(), nullable=False, server_default="ru"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "access_users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("access_users")}
    if "language" in columns:
        op.drop_column("access_users", "language")
