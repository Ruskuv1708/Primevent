"""add employee evaluations table

Revision ID: e7f9a1b2c3d4
Revises: d6e7f8a9b0c1
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "e7f9a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    created_table = False

    if "employee_evaluations" not in tables:
        op.create_table(
            "employee_evaluations",
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("evaluator_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("period_label", sa.String(), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.ForeignKeyConstraint(["workspace_id"], ["access_workspaces.id"]),
            sa.ForeignKeyConstraint(["employee_id"], ["access_users.id"]),
            sa.ForeignKeyConstraint(["evaluator_id"], ["access_users.id"]),
            sa.CheckConstraint("score >= 1 AND score <= 10", name="employee_evaluations_score_range"),
            sa.PrimaryKeyConstraint("id"),
        )
        created_table = True

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_evaluations_workspace_employee "
        "ON employee_evaluations (workspace_id, employee_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_evaluations_workspace_period "
        "ON employee_evaluations (workspace_id, period_label)"
    )
    if not created_table and bind.dialect.name != "sqlite":
        existing_checks = {
            constraint.get("name")
            for constraint in inspector.get_check_constraints("employee_evaluations")
        }
        if "employee_evaluations_score_range" not in existing_checks:
            op.create_check_constraint(
                "employee_evaluations_score_range",
                "employee_evaluations",
                "score >= 1 AND score <= 10",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "employee_evaluations" in inspector.get_table_names():
        op.drop_table("employee_evaluations")
