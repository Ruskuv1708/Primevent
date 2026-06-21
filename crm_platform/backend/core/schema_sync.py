from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class AdditiveColumnSpec:
    table_name: str
    column_name: str
    postgres_definition: str
    sqlite_definition: str

    def definition_for(self, dialect_name: str) -> str:
        if dialect_name == "postgresql":
            return self.postgres_definition
        if dialect_name == "sqlite":
            return self.sqlite_definition
        return self.sqlite_definition


ADDITIVE_COLUMN_SPECS = [
    AdditiveColumnSpec(
        table_name="access_users",
        column_name="language",
        postgres_definition="VARCHAR NOT NULL DEFAULT 'ru'",
        sqlite_definition="VARCHAR NOT NULL DEFAULT 'ru'",
    ),
    AdditiveColumnSpec(
        table_name="access_users",
        column_name="custom_role_id",
        postgres_definition="UUID NULL",
        sqlite_definition="VARCHAR NULL",
    ),
    AdditiveColumnSpec(
        table_name="animator_bookings",
        column_name="event_type",
        postgres_definition="VARCHAR NOT NULL DEFAULT 'order'",
        sqlite_definition="VARCHAR NOT NULL DEFAULT 'order'",
    ),
    AdditiveColumnSpec(
        table_name="ai_change_proposals",
        column_name="operation",
        postgres_definition="VARCHAR NOT NULL DEFAULT 'create'",
        sqlite_definition="VARCHAR NOT NULL DEFAULT 'create'",
    ),
    AdditiveColumnSpec(
        table_name="ai_change_proposals",
        column_name="applied_artifacts",
        postgres_definition="JSONB NOT NULL DEFAULT '[]'::jsonb",
        sqlite_definition="TEXT NOT NULL DEFAULT '[]'",
    ),
    AdditiveColumnSpec(
        table_name="ai_change_proposals",
        column_name="target_artifacts",
        postgres_definition="JSONB NOT NULL DEFAULT '[]'::jsonb",
        sqlite_definition="TEXT NOT NULL DEFAULT '[]'",
    ),
    AdditiveColumnSpec(
        table_name="ai_change_proposals",
        column_name="before_state",
        postgres_definition="JSONB NOT NULL DEFAULT '{}'::jsonb",
        sqlite_definition="TEXT NOT NULL DEFAULT '{}'",
    ),
    AdditiveColumnSpec(
        table_name="ai_change_proposals",
        column_name="after_state",
        postgres_definition="JSONB NOT NULL DEFAULT '{}'::jsonb",
        sqlite_definition="TEXT NOT NULL DEFAULT '{}'",
    ),
    AdditiveColumnSpec(
        table_name="ai_change_proposals",
        column_name="risk_level",
        postgres_definition="VARCHAR NOT NULL DEFAULT 'low'",
        sqlite_definition="VARCHAR NOT NULL DEFAULT 'low'",
    ),
]

AI_CHANGE_PROPOSAL_COLUMN_SPECS = [
    spec for spec in ADDITIVE_COLUMN_SPECS if spec.table_name == "ai_change_proposals"
]


def ensure_runtime_schema(engine: Engine) -> list[str]:
    """Patch safe additive schema drift for deployments that use create_all().

    ``Base.metadata.create_all`` is intentionally conservative: it creates
    missing tables but does not alter existing tables. This helper handles the
    narrow class of additive, defaulted columns that older CRM Platform
    databases need in order to run newer AI Architect code safely.
    """

    added_columns: list[str] = []
    dialect_name = engine.dialect.name

    expected_columns_by_table: dict[str, set[str]] = {}
    for spec in ADDITIVE_COLUMN_SPECS:
        expected_columns_by_table.setdefault(spec.table_name, set()).add(spec.column_name)

    with engine.begin() as connection:
        if dialect_name == "postgresql":
            for spec in ADDITIVE_COLUMN_SPECS:
                connection.execute(
                    text(
                        f"ALTER TABLE {spec.table_name} "
                        f"ADD COLUMN IF NOT EXISTS {spec.column_name} "
                        f"{spec.definition_for(dialect_name)}"
                    )
                )
                added_columns.append(f"{spec.table_name}.{spec.column_name}")
        else:
            inspector = inspect(connection)
            table_names = set(inspector.get_table_names())
            specs_by_table: dict[str, list[AdditiveColumnSpec]] = {}
            for spec in ADDITIVE_COLUMN_SPECS:
                specs_by_table.setdefault(spec.table_name, []).append(spec)

            for table_name, specs in specs_by_table.items():
                if table_name not in table_names:
                    continue

                existing_columns = {
                    column["name"] for column in inspector.get_columns(table_name)
                }
                for spec in specs:
                    if spec.column_name in existing_columns:
                        continue

                    connection.execute(
                        text(
                            f"ALTER TABLE {spec.table_name} "
                            f"ADD COLUMN {spec.column_name} {spec.definition_for(dialect_name)}"
                        )
                    )
                    added_columns.append(f"{spec.table_name}.{spec.column_name}")

        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        missing_after_sync: list[str] = []
        for table_name, expected_columns in expected_columns_by_table.items():
            if table_name not in table_names:
                continue
            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            missing_after_sync.extend(
                f"{table_name}.{column_name}"
                for column_name in sorted(expected_columns - existing_columns)
            )

        if missing_after_sync:
            raise RuntimeError(
                "Runtime schema sync failed; still missing columns: "
                + ", ".join(missing_after_sync)
            )

    return added_columns
