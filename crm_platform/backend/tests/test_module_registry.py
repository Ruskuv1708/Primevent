from uuid import uuid4

from modules.module_registry.definitions import DEFAULT_ENABLED_MODULE_IDS
from modules.module_registry.install_service import ModuleInstallService
from modules.module_registry.service import ModuleService


class WorkspaceStub:
    def __init__(self, settings=None):
        self.settings = settings


class InstalledItemStub:
    def __init__(self, template_id: str):
        self.meta_data = {"module_plugin": {"template_id": template_id}}


class QueryStub:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class DatabaseStub:
    def __init__(self, workspace_result=None, user_result=None):
        self.workspace_result = workspace_result
        self.user_result = user_result
        self.added = []
        self.committed = False

    def query(self, model):
        if model.__name__ == "Workspace":
            return QueryStub(self.workspace_result)
        if model.__name__ == "User":
            return QueryStub(self.user_result)
        return QueryStub(None)

    def add(self, item):
        self.added.append(item)

    def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()

    def commit(self):
        self.committed = True

    def refresh(self, item):
        pass


def test_default_workspace_modules_include_existing_crm_features():
    settings = ModuleService.get_workspace_module_settings(WorkspaceStub(settings=None))

    assert settings["module_preset"] == "functional"
    assert "business_profile" not in settings
    assert settings["enabled_modules"] == list(DEFAULT_ENABLED_MODULE_IDS)


def test_normalize_enabled_modules_drops_unknown_ids_without_auto_enabling_synergies():
    enabled_modules = ModuleService.normalize_enabled_modules([
        "animator_events",
        "animator_schedule",
        "not_a_real_module",
    ])

    assert "not_a_real_module" not in enabled_modules
    assert "animator_events" not in enabled_modules
    assert "animator_schedule" in enabled_modules
    assert "registry" not in enabled_modules
    assert "workflow" not in enabled_modules


def test_removed_business_profiles_fall_back_to_functional_modules():
    settings = ModuleService.build_workspace_settings(
        existing_settings={"business_profile": "clinic"},
        enabled_modules=None,
    )

    assert settings["module_preset"] == "functional"
    assert "business_profile" not in settings
    assert settings["enabled_modules"] == list(DEFAULT_ENABLED_MODULE_IDS)
    assert "clinic" not in settings["enabled_modules"]
    assert "animator_events" not in settings["enabled_modules"]


def test_explicit_enabled_modules_are_independent_functional_modules():
    settings = ModuleService.build_workspace_settings(
        existing_settings={"business_profile": "education", "enabled_modules": ["education"]},
        enabled_modules=["retail_pos", "animator_events", "animator_schedule"],
    )

    assert settings["module_preset"] == "functional"
    assert "business_profile" not in settings
    assert "retail_pos" not in settings["enabled_modules"]
    assert "education" not in settings["enabled_modules"]
    assert "animator_events" not in settings["enabled_modules"]
    assert settings["enabled_modules"] == ["animator_schedule"]


def test_existing_workspace_enabled_modules_do_not_expand_to_defaults_after_reload():
    settings = ModuleService.get_workspace_module_settings(
        WorkspaceStub(
            settings={
                "module_preset": "functional",
                "enabled_modules": ["workspace_home", "animator_schedule"],
            }
        )
    )

    assert settings["module_preset"] == "functional"
    assert settings["enabled_modules"] == ["workspace_home", "animator_schedule"]
    assert "dashboard" not in settings["enabled_modules"]
    assert "registry" not in settings["enabled_modules"]
    assert "workflow" not in settings["enabled_modules"]


def test_schedule_and_ai_architect_are_core_modules_with_route_metadata():
    definitions = {definition.id: definition for definition in ModuleService.list_module_definitions()}
    schedule = definitions["animator_schedule"]
    architect = definitions["ai_architect"]

    assert schedule.category == "functional"
    assert schedule.route_path == "/animator-schedule"
    assert schedule.default_enabled is True
    assert "schedule" in " ".join(schedule.capabilities).lower()
    assert schedule.dependencies == ()
    assert {synergy.module_id for synergy in schedule.synergies} >= {"registry", "workflow"}

    assert architect.category == "functional"
    assert architect.route_path == "/ai-architect"
    assert architect.default_enabled is True
    assert "blueprint" in " ".join(architect.capabilities).lower()
    assert architect.dependencies == ()
    assert {synergy.module_id for synergy in architect.synergies} >= {"dynamic_forms", "reports", "workflow"}
    assert "animator_events" not in definitions


def test_each_sidebar_item_is_a_default_enabled_functional_module():
    expected_sidebar_modules = {
        "workspace_home": "/home",
        "dashboard": "/dashboard",
        "registry": "/registry",
        "open_requests": "/requests",
        "assigned_work": "/requests/assigned",
        "request_history": "/requests/history",
        "departments": "/departments",
        "animator_schedule": "/animator-schedule",
        "employee_evaluations": "/employee-evaluations",
        "form_templates": "/forms",
        "form_builder": "/forms/new",
        "report_library": "/reports",
        "report_types": "/report-types",
        "profile": "/profile",
        "ai_architect": "/ai-architect",
        "admin_panel": "/admin",
        "superadmin_panel": "/superadmin",
    }

    definitions = {definition.id: definition for definition in ModuleService.list_module_definitions()}

    assert set(expected_sidebar_modules).issubset(definitions)
    for module_id, route_path in expected_sidebar_modules.items():
        definition = definitions[module_id]
        assert definition.category == "functional"
        assert definition.default_enabled is True
        assert definition.route_path == route_path
        assert module_id in DEFAULT_ENABLED_MODULE_IDS


def test_serialized_module_definitions_include_shell_metadata():
    schedule = next(
        definition
        for definition in ModuleService.list_module_definitions()
        if definition.id == "animator_schedule"
    )

    payload = ModuleService.serialize_module_definition(schedule)

    assert payload["category"] == "functional"
    assert payload["route_path"] == "/animator-schedule"
    assert payload["summary"]
    assert "capabilities" in payload
    assert payload["dependencies"] == []
    assert "synergies" in payload
    assert any(synergy["module_id"] == "registry" for synergy in payload["synergies"])
    assert "Schedule" in payload["capabilities"][0]


def test_all_modules_are_functional_and_business_modules_are_removed_from_registry():
    non_functional_module_ids = {
        definition.id
        for definition in ModuleService.list_module_definitions()
        if definition.category != "functional"
    }

    manifests = ModuleService.list_module_manifests()

    assert non_functional_module_ids == set()
    assert manifests == []


def test_current_module_manifests_do_not_use_business_module_contracts():
    enabled_modules = ModuleService.normalize_enabled_modules(["clinic", "retail_pos", "animator_schedule"])

    manifests = ModuleService.list_module_manifests(enabled_modules)

    assert manifests == []


def test_serialized_module_manifest_includes_template_contract():
    assert ModuleService.list_module_manifests(["education"]) == []


def test_installer_builds_dynamic_form_schema_from_manifest_fields():
    from modules.module_registry.definitions import ModuleTemplateDefinition

    template = ModuleTemplateDefinition(
        id="local.visit_note",
        label="Visit Note",
        template_type="form",
        description="Visit note",
        fields=("Patient", "Next visit"),
    )

    schema = ModuleInstallService.build_form_schema(template)

    assert schema[0] == {"key": "patient", "label": "Patient", "type": "text", "required": False}
    assert {"key": "next_visit", "label": "Next visit", "type": "date", "required": False} in schema


def test_installer_builds_report_columns_from_manifest_fields():
    from modules.module_registry.definitions import ModuleTemplateDefinition

    report_template = ModuleTemplateDefinition(
        id="local.sales_margin",
        label="Sales Margin",
        template_type="report",
        description="Sales margin",
        fields=("Store", "Sales amount"),
    )

    columns = ModuleInstallService.build_report_columns(report_template)

    assert columns[0] == {"key": "store", "label": "Store", "formula": None, "format": None}
    assert {"key": "sales_amount", "label": "Sales amount", "formula": None, "format": None} in columns


def test_installer_status_uses_plugin_metadata_without_duplicates():
    from modules.module_registry.definitions import ModuleManifest, ModuleTemplateDefinition

    manifest = ModuleManifest(
        module_id="animator_schedule",
        templates=(
            ModuleTemplateDefinition(
                id="animator_schedule.order",
                label="Order",
                template_type="form",
                description="Order",
                fields=("Client",),
            ),
            ModuleTemplateDefinition(
                id="animator_schedule.report",
                label="Report",
                template_type="report",
                description="Report",
                fields=("Date",),
            ),
            ModuleTemplateDefinition(
                id="animator_schedule.inventory",
                label="Inventory",
                template_type="form",
                description="Inventory",
                fields=("Item",),
            ),
        ),
    )
    installed_items = [
        InstalledItemStub("animator_schedule.order"),
        InstalledItemStub("animator_schedule.order"),
        InstalledItemStub("animator_schedule.report"),
    ]

    status = ModuleInstallService.build_install_status(
        manifest=manifest,
        installed_forms=installed_items,
        installed_reports=installed_items,
    )

    assert status["module_id"] == "animator_schedule"
    assert status["total_templates"] == 3
    assert status["installed_count"] == 2
    assert status["is_installed"] is False
    assert "animator_schedule.order" in status["installed_template_ids"]
    assert "animator_schedule.inventory" in status["missing_template_ids"]


def test_workspace_creation_provisions_enabled_functional_module_templates(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.workspace_management.schemas import WorkspaceCreateSchema
    from modules.workspace_management.service import WorkspaceService

    calls = []

    def fake_install_enabled_modules(db, workspace_id, enabled_modules):
        calls.append((db, workspace_id, enabled_modules))
        return []

    monkeypatch.setattr(
        ModuleInstallService,
        "install_enabled_modules",
        fake_install_enabled_modules,
        raising=False,
    )
    db = DatabaseStub()

    WorkspaceService.create_workspace(
        db,
        WorkspaceCreateSchema(
            workspace_name="CRM Demo",
            subdomain_prefix="crm-demo",
            admin_full_name="CRM Admin",
            admin_email="crm-admin@example.com",
            admin_password="CrmPass123!",
            module_preset="functional",
        ),
    )

    workspace = db.added[0]
    assert calls == [(db, workspace.id, workspace.settings["enabled_modules"])]
    assert workspace.settings["module_preset"] == "functional"
    assert "business_profile" not in workspace.settings
    assert calls[0][2] == list(DEFAULT_ENABLED_MODULE_IDS)
    assert "education" not in calls[0][2]


def test_workspace_module_update_provisions_enabled_functional_module_templates(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.workflow import models as workflow_models  # noqa: F401

    calls = []
    workspace = WorkspaceStub(
        settings={
            "module_preset": "functional",
            "enabled_modules": list(DEFAULT_ENABLED_MODULE_IDS),
        }
    )
    workspace.id = uuid4()

    def fake_install_enabled_modules(db, workspace_id, enabled_modules):
        calls.append((db, workspace_id, enabled_modules))
        return []

    monkeypatch.setattr(
        ModuleInstallService,
        "install_enabled_modules",
        fake_install_enabled_modules,
        raising=False,
    )
    db = DatabaseStub(workspace_result=workspace)

    ModuleService.update_workspace_modules(
        db,
        workspace_id=workspace.id,
        module_preset="functional",
        enabled_modules=["clinic"],
    )

    assert calls == [(db, workspace.id, workspace.settings["enabled_modules"])]
    assert workspace.settings["module_preset"] == "functional"
    assert "business_profile" not in workspace.settings
    assert "clinic" not in calls[0][2]
