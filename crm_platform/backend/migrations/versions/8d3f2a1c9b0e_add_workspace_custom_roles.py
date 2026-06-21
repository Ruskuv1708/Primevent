"""add workspace custom visibility roles

Revision ID: 8d3f2a1c9b0e
Revises: 6b1e2a3d4c5f
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "8d3f2a1c9b0e"
down_revision: Union[str, Sequence[str], None] = "6b1e2a3d4c5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "access_workspace_roles" not in tables:
        op.create_table(
            "access_workspace_roles",
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("base_role", sa.String(), nullable=False, server_default="USER"),
            sa.Column("permissions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
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
            "ix_access_workspace_roles_workspace_id",
            "access_workspace_roles",
            ["workspace_id"],
            unique=False,
        )

    if "access_users" in tables:
        columns = {column["name"] for column in inspector.get_columns("access_users")}
        if "custom_role_id" not in columns:
            op.add_column(
                "access_users",
                sa.Column("custom_role_id", postgresql.UUID(as_uuid=True), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "access_users" in tables:
        columns = {column["name"] for column in inspector.get_columns("access_users")}
        if "custom_role_id" in columns:
            op.drop_column("access_users", "custom_role_id")

    if "access_workspace_roles" in tables:
        op.drop_index("ix_access_workspace_roles_workspace_id", table_name="access_workspace_roles")
        op.drop_table("access_workspace_roles")
