from io import BytesIO
from uuid import uuid4
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


def test_demo_and_qa_workspace_specs_are_distinct(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from scripts.bootstrap_demo_workspace import DEMO_WORKSPACE_EMAIL
    from scripts.bootstrap_qa_workspace import QA_WORKSPACE_EMAIL

    assert DEMO_WORKSPACE_EMAIL != QA_WORKSPACE_EMAIL
    assert DEMO_WORKSPACE_EMAIL.endswith("@example.com")
    assert QA_WORKSPACE_EMAIL.endswith("@example.com")


def test_demo_workspace_story_includes_records_and_ai_history(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from scripts.bootstrap_demo_workspace import demo_story_summary

    summary = demo_story_summary()

    assert summary["form_record_count"] >= 2
    assert summary["ai_history_statuses"] == {"available", "rolled_back"}


def test_development_workspace_enables_every_default_module(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.module_registry.definitions import DEFAULT_ENABLED_MODULE_IDS
    from scripts.bootstrap_dev_workspace import DEV_WORKSPACE_EMAIL, development_workspace_summary

    summary = development_workspace_summary()

    assert DEV_WORKSPACE_EMAIL.endswith("@example.com")
    assert summary["enabled_modules"] == list(DEFAULT_ENABLED_MODULE_IDS)
    assert summary["department_count"] >= 4
    assert summary["user_count"] >= 5
    assert summary["form_template_count"] >= 3
    assert summary["report_type_count"] >= 3


def test_access_token_round_trips_user_identity(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from core.security import create_access_token, verify_access_token

    token = create_access_token(user_id="user-1", role="admin")
    payload = verify_access_token(token)

    assert payload["user_id"] == "user-1"
    assert payload["role"] == "admin"


def test_form_template_lookup_is_workspace_scoped(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.access_control import models as access_models  # noqa: F401
    from modules.dynamic_records.models import FormTemplate
    from modules.dynamic_records.service import DynamicRecordService

    workspace_id = uuid4()
    template = FormTemplate(id=uuid4(), name="Scoped", schema_structure=[], workspace_id=workspace_id)

    class RecordingQuery:
        def __init__(self):
            self.filters = []

        def filter(self, *conditions):
            self.filters.extend(conditions)
            return self

        def first(self):
            return template

    class DatabaseStub:
        def __init__(self):
            self.query_stub = RecordingQuery()

        def query(self, model):
            assert model is FormTemplate
            return self.query_stub

    db = DatabaseStub()
    result = DynamicRecordService.get_template(db, template.id, workspace_id)

    assert result is template
    assert any(getattr(condition.left, "name", None) == "workspace_id" for condition in db.query_stub.filters)


def test_template_delete_refuses_existing_records(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.access_control import models as access_models  # noqa: F401
    from modules.dynamic_records.models import FormRecord, FormTemplate
    from modules.dynamic_records.service import DynamicRecordService

    workspace_id = uuid4()
    template = FormTemplate(id=uuid4(), name="Intake", schema_structure=[], workspace_id=workspace_id)
    record = FormRecord(id=uuid4(), template_id=template.id, entry_data={})

    class QueryStub:
        def __init__(self, item):
            self.item = item

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.item

    class DatabaseStub:
        def query(self, model):
            if model is FormTemplate:
                return QueryStub(template)
            if model is FormRecord:
                return QueryStub(record)
            raise AssertionError(model)

    with pytest.raises(HTTPException) as exc:
        DynamicRecordService.delete_template(DatabaseStub(), template.id, workspace_id)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Cannot delete template with existing records"


def test_department_delete_refuses_linked_requests(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow.models import Department, Request
    from modules.workflow.service import WorkflowService

    workspace_id = uuid4()
    department = Department(id=uuid4(), name="Ops", description="", workspace_id=workspace_id)

    class QueryStub:
        def __init__(self, item):
            self.item = item

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.item

    class DatabaseStub:
        def query(self, model):
            if model is Department:
                return QueryStub(department)
            if getattr(model, "name", None) == "id" and model.class_ is Request:
                return QueryStub(uuid4())
            return QueryStub(None)

    with pytest.raises(HTTPException) as exc:
        WorkflowService.delete_department(DatabaseStub(), department.id, workspace_id)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Cannot delete department with existing requests"


def test_department_delete_refuses_assigned_users(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.access_control.models import User
    from modules.workflow.models import Department, Request
    from modules.workflow.service import WorkflowService

    workspace_id = uuid4()
    department = Department(id=uuid4(), name="Ops", description="", workspace_id=workspace_id)

    class QueryStub:
        def __init__(self, item):
            self.item = item

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.item

    class DatabaseStub:
        def query(self, model):
            if model is Department:
                return QueryStub(department)
            if getattr(model, "name", None) == "id" and model.class_ is Request:
                return QueryStub(None)
            if getattr(model, "name", None) == "id" and model.class_ is User:
                return QueryStub(uuid4())
            return QueryStub(None)

    with pytest.raises(HTTPException) as exc:
        WorkflowService.delete_department(DatabaseStub(), department.id, workspace_id)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Cannot delete department with assigned users"


def test_report_type_create_and_update_serialize_normalized_columns(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.reports.models import ReportType
    from modules.reports.schemas import (
        ReportTypeColumnSchema,
        ReportTypeCreateSchema,
        ReportTypeUpdateSchema,
    )
    from modules.reports.service import ReportService

    workspace_id = uuid4()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self):
            self.items = []
            self.report_query_count = 0

        def add(self, item):
            if getattr(item, "id", None) is None:
                item.id = uuid4()
            self.items.append(item)

        def commit(self):
            return None

        def refresh(self, item):
            return None

        def query(self, model):
            if model is ReportType:
                self.report_query_count += 1
                if self.report_query_count == 1:
                    return QueryStub([])
                return QueryStub([item for item in self.items if isinstance(item, ReportType)])
            return QueryStub([])

    db = DatabaseStub()
    created = ReportService.create_report_type(
        db,
        workspace_id,
        ReportTypeCreateSchema(
            name="  Open Requests  ",
            description="  Queue view  ",
            columns=[ReportTypeColumnSchema(key=" status ", label=" Status ")],
        ),
    )
    report = db.items[0]
    updated = ReportService.update_report_type(
        db,
        workspace_id,
        report.id,
        ReportTypeUpdateSchema(
            columns=[ReportTypeColumnSchema(key="owner", label="Owner", formula=" ", format=" ")],
        ),
    )

    assert created["name"] == "Open Requests"
    assert created["description"] == "Queue view"
    assert created["columns"] == [{"key": "status", "label": "Status", "formula": None, "format": None}]
    assert updated["columns"] == [{"key": "owner", "label": "Owner", "formula": None, "format": None}]


def test_superadmin_can_save_ai_settings_without_exposing_api_key(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.workspace_management.router import AISettingsUpdateSchema, update_ai_settings

    class QueryStub:
        def __init__(self, db):
            self.db = db

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.db.setting

    class DatabaseStub:
        def __init__(self):
            self.setting = None
            self.committed = False

        def query(self, model):
            assert model.__name__ == "SystemSetting"
            return QueryStub(self)

        def add(self, item):
            self.setting = item

        def commit(self):
            self.committed = True

        def refresh(self, item):
            return None

    db = DatabaseStub()
    current_user = SimpleNamespace(role=UserRole.SUPERADMIN, email="root@example.com")

    result = update_ai_settings(
        AISettingsUpdateSchema(
            provider="gemini",
            model="gemini-1.5-pro",
            api_key="provider-secret-1234",
            base_url="",
        ),
        db,
        current_user,
    )

    assert result["provider"] == "gemini"
    assert result["model"] == "gemini-1.5-pro"
    assert result["api_key_configured"] is True
    assert result["api_key_preview"] == "••••1234"
    assert "api_key" not in result
    assert db.setting.value["api_key"] == "provider-secret-1234"
    assert db.committed is True


def test_non_superadmin_cannot_save_ai_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.workspace_management.router import AISettingsUpdateSchema, update_ai_settings

    current_user = SimpleNamespace(role=UserRole.ADMIN, email="admin@example.com")

    with pytest.raises(HTTPException) as exc:
        update_ai_settings(
            AISettingsUpdateSchema(provider="deterministic"),
            SimpleNamespace(),
            current_user,
        )

    assert exc.value.status_code == 403


def test_live_ai_settings_require_model_and_api_key(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.workspace_management.router import AISettingsUpdateSchema, update_ai_settings

    class QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class DatabaseStub:
        def query(self, model):
            return QueryStub()

    current_user = SimpleNamespace(role=UserRole.SUPERADMIN, email="root@example.com")

    with pytest.raises(HTTPException) as exc:
        update_ai_settings(
            AISettingsUpdateSchema(provider="gemini", model="", api_key=""),
            DatabaseStub(),
            current_user,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Model and API key are required for live AI providers"


def test_ai_settings_refresh_runtime_provider(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from core.config import settings
    from modules.access_control.enums import UserRole
    from modules.ai_architect.service import AIArchitectService
    from modules.workspace_management.router import AISettingsUpdateSchema, update_ai_settings

    class QueryStub:
        def __init__(self, db):
            self.db = db

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.db.setting

    class DatabaseStub:
        def __init__(self):
            self.setting = None

        def query(self, model):
            return QueryStub(self)

        def add(self, item):
            self.setting = item

        def commit(self):
            return None

        def refresh(self, item):
            return None

    current_user = SimpleNamespace(role=UserRole.SUPERADMIN, email="root@example.com")

    result = update_ai_settings(
        AISettingsUpdateSchema(
            provider="gemini",
            model="gemini-1.5-pro",
            api_key="runtime-secret-5678",
        ),
        DatabaseStub(),
        current_user,
    )

    assert result["api_key_preview"] == "••••5678"
    assert settings.AI_ARCHITECT_PROVIDER == "gemini"
    assert settings.AI_ARCHITECT_MODEL == "gemini-1.5-pro"
    assert settings.AI_ARCHITECT_API_KEY == "runtime-secret-5678"
    assert AIArchitectService.provider.provider_name == "gemini"


def test_current_user_password_change_requires_current_password(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.router import PasswordChangeSchema, change_current_user_password, pwd_context
    from modules.access_control.enums import UserRole

    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.SUPERADMIN,
        hashed_password=pwd_context.hash("OldPass123!"),
    )

    with pytest.raises(HTTPException) as exc:
        change_current_user_password(
            PasswordChangeSchema(current_password="wrong-password", new_password="NewPass123!"),
            SimpleNamespace(),
            current_user,
        )

    assert exc.value.status_code == 401
    assert pwd_context.verify("OldPass123!", current_user.hashed_password)


def test_current_user_password_change_updates_hash(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.router import PasswordChangeSchema, change_current_user_password, pwd_context
    from modules.access_control.enums import UserRole

    class DatabaseStub:
        def __init__(self):
            self.committed = False

        def commit(self):
            self.committed = True

        def refresh(self, item):
            return None

    db = DatabaseStub()
    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.SUPERADMIN,
        hashed_password=pwd_context.hash("OldPass123!"),
    )

    result = change_current_user_password(
        PasswordChangeSchema(current_password="OldPass123!", new_password="NewPass123!"),
        db,
        current_user,
    )

    assert result == {"message": "Password updated"}
    assert pwd_context.verify("NewPass123!", current_user.hashed_password)
    assert db.committed is True


def test_superadmin_can_reset_workspace_user_password(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.router import UserPasswordResetSchema, reset_user_password, pwd_context
    from modules.access_control.enums import UserRole
    from modules.access_control.models import User

    workspace_id = uuid4()
    target_user = SimpleNamespace(
        id=uuid4(),
        full_name="Workspace User",
        email="user@example.com",
        role=UserRole.USER,
        is_active=True,
        workspace_id=workspace_id,
        department_id=None,
        meta_data={},
        hashed_password=pwd_context.hash("OldPass123!"),
    )

    class QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return target_user

    class DatabaseStub:
        def __init__(self):
            self.committed = False

        def query(self, model):
            assert model is User
            return QueryStub()

        def commit(self):
            self.committed = True

        def refresh(self, item):
            return None

    db = DatabaseStub()
    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.SUPERADMIN,
        workspace_id=None,
        email="root@example.com",
    )

    result = reset_user_password(
        target_user.id,
        UserPasswordResetSchema(new_password="NewPass123!"),
        db,
        current_user,
    )

    assert result["message"] == "Password reset"
    assert result["user"]["email"] == "user@example.com"
    assert pwd_context.verify("NewPass123!", target_user.hashed_password)
    assert db.committed is True


def test_admin_cannot_reset_protected_admin_password(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.router import UserPasswordResetSchema, reset_user_password, pwd_context
    from modules.access_control.enums import UserRole
    from modules.access_control.models import User

    workspace_id = uuid4()
    target_user = SimpleNamespace(
        id=uuid4(),
        full_name="Workspace Admin",
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=True,
        workspace_id=workspace_id,
        department_id=None,
        meta_data={},
        hashed_password=pwd_context.hash("OldPass123!"),
    )

    class QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return target_user

    class DatabaseStub:
        def query(self, model):
            assert model is User
            return QueryStub()

        def commit(self):
            raise AssertionError("commit should not be called")

        def refresh(self, item):
            return None

    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.ADMIN,
        workspace_id=workspace_id,
        email="admin2@example.com",
    )

    with pytest.raises(HTTPException) as exc:
        reset_user_password(
            target_user.id,
            UserPasswordResetSchema(new_password="NewPass123!"),
            DatabaseStub(),
            current_user,
        )

    assert exc.value.status_code == 403
    assert pwd_context.verify("OldPass123!", target_user.hashed_password)


def test_user_update_cannot_deactivate_current_user(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.access_control.models import User
    from modules.access_control.router import UserUpdateSchema, update_user

    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.SUPERADMIN,
        workspace_id=uuid4(),
        email="root@example.com",
    )
    target_user = SimpleNamespace(
        id=current_user.id,
        role=UserRole.SUPERADMIN,
        workspace_id=current_user.workspace_id,
        is_active=True,
    )

    class QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return target_user

    class DatabaseStub:
        def query(self, model):
            assert model is User
            return QueryStub()

    with pytest.raises(HTTPException) as exc:
        update_user(
            current_user.id,
            UserUpdateSchema(is_active=False),
            DatabaseStub(),
            current_user,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Cannot deactivate your own account"


def test_user_serializer_defaults_to_russian_language(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.router import _serialize_user
    from modules.access_control.enums import UserRole

    user = SimpleNamespace(
        id=uuid4(),
        full_name="Workspace User",
        email="user@example.com",
        role=UserRole.USER,
        is_active=True,
        workspace_id=uuid4(),
        department_id=None,
        meta_data={},
    )

    assert _serialize_user(user)["language"] == "ru"


def test_admin_can_create_workspace_role_with_visibility_permissions(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.access_control.models import WorkspaceRole
    from modules.access_control.router import (
        WorkspaceRoleCreateSchema,
        create_workspace_role,
    )

    workspace_id = uuid4()

    class QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class DatabaseStub:
        def __init__(self):
            self.added = None
            self.committed = False

        def query(self, model):
            assert model is WorkspaceRole
            return QueryStub()

        def add(self, item):
            self.added = item
            if getattr(item, "id", None) is None:
                item.id = uuid4()

        def commit(self):
            self.committed = True

        def refresh(self, item):
            return None

    db = DatabaseStub()
    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.ADMIN,
        workspace_id=workspace_id,
        email="admin@example.com",
    )

    result = create_workspace_role(
        WorkspaceRoleCreateSchema(
            workspace_id=workspace_id,
            name="Coordinator",
            description="Only sees work and forms",
            base_role=UserRole.USER,
            permissions={
                "tabs": {"home": True, "work": True, "money": False},
                "fields": {"forms": {"guest_phone": False}},
            },
        ),
        db,
        current_user,
    )

    assert db.committed is True
    assert result["name"] == "Coordinator"
    assert result["workspace_id"] == workspace_id
    assert result["permissions"]["tabs"]["work"] is True
    assert result["permissions"]["tabs"]["money"] is False
    assert result["permissions"]["fields"]["forms"]["guest_phone"] is False


def test_admin_cannot_create_workspace_role_for_another_workspace(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.access_control.router import (
        WorkspaceRoleCreateSchema,
        create_workspace_role,
    )

    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.ADMIN,
        workspace_id=uuid4(),
        email="admin@example.com",
    )

    with pytest.raises(HTTPException) as exc:
        create_workspace_role(
            WorkspaceRoleCreateSchema(
                workspace_id=uuid4(),
                name="External",
                base_role=UserRole.USER,
                permissions={"tabs": {"home": True}},
            ),
            SimpleNamespace(),
            current_user,
        )

    assert exc.value.status_code == 403


def test_admin_can_assign_custom_role_to_workspace_user(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.access_control.models import User, WorkspaceRole
    from modules.access_control.router import (
        UserCustomRoleUpdateSchema,
        assign_user_custom_role,
    )

    workspace_id = uuid4()
    role_id = uuid4()
    target_user = SimpleNamespace(
        id=uuid4(),
        full_name="User",
        email="user@example.com",
        language="ru",
        role=UserRole.USER,
        is_active=True,
        workspace_id=workspace_id,
        department_id=None,
        meta_data={},
        custom_role_id=None,
        custom_role=None,
    )
    custom_role = SimpleNamespace(
        id=role_id,
        workspace_id=workspace_id,
        name="Coordinator",
        description="",
        base_role=UserRole.USER,
        permissions={"tabs": {"work": True, "reports": False}, "fields": {}},
    )

    class QueryStub:
        def __init__(self, item):
            self.item = item

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.item

    class DatabaseStub:
        def __init__(self):
            self.committed = False

        def query(self, model):
            if model is User:
                return QueryStub(target_user)
            if model is WorkspaceRole:
                return QueryStub(custom_role)
            raise AssertionError(model)

        def commit(self):
            self.committed = True

        def refresh(self, item):
            item.custom_role = custom_role

    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.ADMIN,
        workspace_id=workspace_id,
        email="admin@example.com",
    )

    result = assign_user_custom_role(
        target_user.id,
        UserCustomRoleUpdateSchema(custom_role_id=role_id),
        DatabaseStub(),
        current_user,
    )

    assert result["custom_role_id"] == role_id
    assert result["custom_role"]["name"] == "Coordinator"
    assert result["custom_role"]["permissions"]["tabs"]["reports"] is False


def test_user_language_rejects_unsupported_values(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.router import _normalize_language

    assert _normalize_language("EN") == "en"
    with pytest.raises(HTTPException) as exc:
        _normalize_language("uz")

    assert exc.value.status_code == 400


def test_ai_create_rollback_refuses_form_with_records(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.access_control import models as access_models  # noqa: F401
    from modules.ai_architect.models import AIChangeEvent
    from modules.ai_architect.rollback_service import AIChangeRollbackService
    from modules.dynamic_records.models import FormRecord, FormTemplate

    template = FormTemplate(id=uuid4(), workspace_id=uuid4(), name="Student intake", schema_structure=[])
    record = FormRecord(id=uuid4(), template_id=template.id, entry_data={})
    event = AIChangeEvent(
        id=uuid4(),
        workspace_id=template.workspace_id,
        proposal_id=uuid4(),
        operation="create",
        affected_artifacts=[{"type": "form", "id": str(template.id)}],
    )

    class QueryStub:
        def __init__(self, item):
            self.item = item

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.item

    class DatabaseStub:
        def query(self, model):
            if model is FormTemplate:
                return QueryStub(template)
            if model is FormRecord:
                return QueryStub(record)
            return QueryStub(None)

    with pytest.raises(HTTPException) as exc:
        AIChangeRollbackService.rollback(DatabaseStub(), event)

    assert exc.value.status_code == 400
    assert event.rollback_status == "unavailable"
    assert event.rollback_reason == "Form already has submitted records"


def test_spreadsheet_export_values_are_formula_safe(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from core.export_safety import safe_spreadsheet_cell, safe_spreadsheet_row

    assert safe_spreadsheet_cell("=HYPERLINK(\"http://example.com\")") == "'=HYPERLINK(\"http://example.com\")"
    assert safe_spreadsheet_cell("+SUM(1,1)") == "'+SUM(1,1)"
    assert safe_spreadsheet_cell("-10+20") == "'-10+20"
    assert safe_spreadsheet_cell("@cmd") == "'@cmd"
    assert safe_spreadsheet_cell("plain text") == "plain text"
    assert safe_spreadsheet_row(["=cmd", 5, None]) == ["'=cmd", 5, None]


def test_ai_architect_routes_require_permission(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.ai_architect.router import create_conversation
    from modules.ai_architect.schemas import ConversationCreateRequest

    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.USER,
        workspace_id=uuid4(),
        email="user@example.com",
    )

    with pytest.raises(HTTPException) as exc:
        create_conversation(
            ConversationCreateRequest(title="Setup"),
            SimpleNamespace(),
            current_user,
        )

    assert exc.value.status_code == 403


def test_system_admin_cannot_resolve_another_workspace(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from core.workspace_resolver import resolve_workspace_id
    from modules.access_control.enums import UserRole

    current_user = SimpleNamespace(
        role=UserRole.SYSTEM_ADMIN,
        workspace_id=uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        resolve_workspace_id(current_user, uuid4())

    assert exc.value.status_code == 403


def test_file_upload_stops_before_persisting_oversized_file(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.file_storage import service as file_service
    from modules.file_storage.service import FileStorageService

    monkeypatch.setattr(file_service, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(file_service, "MAX_UPLOAD_BYTES", 4)

    upload_file = SimpleNamespace(
        filename="oversized.txt",
        content_type="text/plain",
        file=BytesIO(b"12345"),
    )
    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.ADMIN,
        workspace_id=uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        FileStorageService.save_file(
            SimpleNamespace(),
            upload_file,
            current_user.id,
            current_user.workspace_id,
            current_user=current_user,
        )

    assert exc.value.status_code == 413
    assert not any(path.is_file() for path in tmp_path.rglob("*"))


def test_batch_form_submit_rolls_back_when_later_row_is_invalid(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control import models as access_models  # noqa: F401
    from modules.access_control.enums import UserRole
    from modules.dynamic_records.models import FormTemplate
    from modules.dynamic_records.service import DynamicRecordService

    workspace_id = uuid4()
    template = FormTemplate(
        id=uuid4(),
        name="Batch intake",
        schema_structure=[{"key": "guest", "label": "Guest", "type": "text", "required": True}],
        workspace_id=workspace_id,
    )

    class QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return template

    class DatabaseStub:
        def __init__(self):
            self.added = []
            self.committed = False
            self.rolled_back = False

        def query(self, model):
            assert model is FormTemplate
            return QueryStub()

        def add(self, item):
            if getattr(item, "id", None) is None:
                item.id = uuid4()
            self.added.append(item)

        def flush(self):
            return None

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True
            self.added = []

        def refresh(self, item):
            return None

    db = DatabaseStub()
    current_user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.USER,
        workspace_id=workspace_id,
        email="user@example.com",
    )

    with pytest.raises(HTTPException) as exc:
        DynamicRecordService.submit_records(
            db,
            template.id,
            [{"guest": "Valid"}, {"guest": ""}],
            workspace_id,
            current_user,
        )

    assert exc.value.status_code == 400
    assert db.committed is False
    assert db.rolled_back is True
    assert db.added == []


def test_user_can_self_assign_own_unassigned_request(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")

    from modules.access_control.enums import UserRole
    from modules.access_control.models import User
    from modules.workflow.enums import RequestPriority, RequestStatus
    from modules.workflow.models import Request
    from modules.workflow.service import WorkflowService

    workspace_id = uuid4()
    user_id = uuid4()
    request = Request(
        id=uuid4(),
        title="Own request",
        description="Created by the current user",
        priority=RequestPriority.MEDIUM,
        department_id=uuid4(),
        workspace_id=workspace_id,
        status=RequestStatus.NEW,
        created_by_id=user_id,
    )
    assignee = User(
        id=user_id,
        full_name="Form User",
        email="user@example.com",
        role=UserRole.USER,
        workspace_id=workspace_id,
        is_active=True,
    )

    class QueryStub:
        def __init__(self, item):
            self.item = item

        def options(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.item

    class DatabaseStub:
        def __init__(self):
            self.committed = False

        def query(self, model):
            if model is Request:
                return QueryStub(request)
            if model is User:
                return QueryStub(assignee)
            raise AssertionError(model)

        def commit(self):
            self.committed = True

        def refresh(self, item):
            item.assignee = assignee

    current_user = SimpleNamespace(
        id=user_id,
        role=UserRole.USER,
        workspace_id=workspace_id,
        email="user@example.com",
    )

    db = DatabaseStub()
    result = WorkflowService.assign_request(db, request.id, user_id, workspace_id, current_user)

    assert db.committed is True
    assert result["assigned_to_id"] == str(user_id)
    assert result["status"] == "assigned"
