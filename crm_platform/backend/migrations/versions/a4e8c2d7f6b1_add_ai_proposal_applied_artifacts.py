"""add ai proposal applied artifacts

Revision ID: a4e8c2d7f6b1
Revises: f9d1c4b7e8a2
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a4e8c2d7f6b1"
down_revision: Union[str, Sequence[str], None] = "f9d1c4b7e8a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "ai_change_proposals" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("ai_change_proposals")}
    if "applied_artifacts" not in columns:
        op.add_column(
            "ai_change_proposals",
            sa.Column(
                "applied_artifacts",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "ai_change_proposals" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("ai_change_proposals")}
    if "applied_artifacts" in columns:
        op.drop_column("ai_change_proposals", "applied_artifacts")
