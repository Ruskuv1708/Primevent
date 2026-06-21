from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect


def test_runtime_schema_sync_adds_missing_ai_proposal_columns():
    from core.schema_sync import ensure_runtime_schema

    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    Table(
        "ai_change_proposals",
        metadata,
        Column("id", String, primary_key=True),
        Column("workspace_id", String, nullable=False),
        Column("blueprint_id", String, nullable=False),
        Column("proposal_type", String, nullable=False),
        Column("title", String, nullable=False),
        Column("description", String, nullable=False),
        Column("rationale", String, nullable=False),
        Column("generated_artifacts", String, nullable=False),
        Column("status", String, nullable=False),
    )
    metadata.create_all(engine)

    added_columns = ensure_runtime_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("ai_change_proposals")}
    assert {
        "operation",
        "applied_artifacts",
        "target_artifacts",
        "before_state",
        "after_state",
        "risk_level",
    }.issubset(columns)
    assert {
        "ai_change_proposals.operation",
        "ai_change_proposals.applied_artifacts",
        "ai_change_proposals.target_artifacts",
        "ai_change_proposals.before_state",
        "ai_change_proposals.after_state",
        "ai_change_proposals.risk_level",
    }.issubset(set(added_columns))

    assert ensure_runtime_schema(engine) == []


def test_runtime_schema_sync_adds_user_language_column():
    from core.schema_sync import ensure_runtime_schema

    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    Table(
        "access_users",
        metadata,
        Column("id", String, primary_key=True),
        Column("email", String, nullable=False),
        Column("hashed_password", String, nullable=False),
        Column("full_name", String, nullable=False),
        Column("role", String, nullable=False),
    )
    metadata.create_all(engine)

    added_columns = ensure_runtime_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("access_users")}
    assert "language" in columns
    assert "access_users.language" in added_columns
    assert ensure_runtime_schema(engine) == []


def test_runtime_schema_sync_adds_user_custom_role_column():
    from core.schema_sync import ensure_runtime_schema

    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    Table(
        "access_users",
        metadata,
        Column("id", String, primary_key=True),
        Column("email", String, nullable=False),
        Column("hashed_password", String, nullable=False),
        Column("full_name", String, nullable=False),
        Column("language", String, nullable=False),
        Column("role", String, nullable=False),
    )
    metadata.create_all(engine)

    added_columns = ensure_runtime_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("access_users")}
    assert "custom_role_id" in columns
    assert "access_users.custom_role_id" in added_columns
    assert ensure_runtime_schema(engine) == []


def test_runtime_schema_sync_adds_animator_booking_event_type_column():
    from core.schema_sync import ensure_runtime_schema

    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    Table(
        "animator_bookings",
        metadata,
        Column("id", String, primary_key=True),
        Column("workspace_id", String, nullable=False),
        Column("title", String, nullable=False),
        Column("client_name", String, nullable=False),
        Column("event_date", String, nullable=False),
        Column("start_time", String, nullable=False),
        Column("duration_minutes", String, nullable=False),
        Column("status", String, nullable=False),
        Column("color", String, nullable=False),
    )
    metadata.create_all(engine)

    added_columns = ensure_runtime_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("animator_bookings")}
    assert "event_type" in columns
    assert "animator_bookings.event_type" in added_columns
    assert ensure_runtime_schema(engine) == []
