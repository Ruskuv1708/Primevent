"""extend ai refinement proposals

Revision ID: d1f4a6b8c2e0
Revises: a4e8c2d7f6b1
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "d1f4a6b8c2e0"
down_revision: Union[str, Sequence[str], None] = "a4e8c2d7f6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "ai_change_proposals" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ai_change_proposals")}
    specs = [
        ("operation", sa.Column("operation", sa.String(), nullable=False, server_default="create")),
        ("target_artifacts", sa.Column("target_artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb"))),
        ("before_state", sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"))),
        ("after_state", sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"))),
        ("risk_level", sa.Column("risk_level", sa.String(), nullable=False, server_default="low")),
    ]
    for name, column in specs:
        if name not in columns:
            op.add_column("ai_change_proposals", column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "ai_change_proposals" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ai_change_proposals")}
    for name in ("risk_level", "after_state", "before_state", "target_artifacts", "operation"):
        if name in columns:
            op.drop_column("ai_change_proposals", name)
