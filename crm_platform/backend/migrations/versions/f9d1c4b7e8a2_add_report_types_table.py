"""add report types table

Revision ID: f9d1c4b7e8a2
Revises: e4f7a1c2d9b0
Create Date: 2026-02-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f9d1c4b7e8a2"
down_revision: Union[str, Sequence[str], None] = "e4f7a1c2d9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports_report_types",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="requests"),
        sa.Column("columns", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        "ix_reports_report_types_workspace_id",
        "reports_report_types",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_reports_report_types_workspace_name",
        "reports_report_types",
        ["workspace_id", "name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reports_report_types_workspace_name", table_name="reports_report_types")
    op.drop_index("ix_reports_report_types_workspace_id", table_name="reports_report_types")
    op.drop_table("reports_report_types")