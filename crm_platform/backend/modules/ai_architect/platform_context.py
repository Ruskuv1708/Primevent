from __future__ import annotations


EXISTING_CRM_PAGES = [
    {"id": "home", "name": "Home", "route": "/home", "purpose": "Workspace overview and quick actions."},
    {"id": "people", "name": "People", "route": "/people", "purpose": "People-oriented market section."},
    {"id": "work", "name": "Work", "route": "/work", "purpose": "Operational market section."},
    {"id": "money", "name": "Money", "route": "/money", "purpose": "Finance-oriented market section."},
    {"id": "settings", "name": "Settings", "route": "/settings", "purpose": "Workspace settings entry point."},
    {"id": "dashboard", "name": "Dashboard", "route": "/dashboard", "purpose": "Workspace request dashboard."},
    {"id": "requests", "name": "Requests", "route": "/requests", "purpose": "Create, view, assign, and track requests."},
    {"id": "assigned_requests", "name": "Assigned Requests", "route": "/requests/assigned", "purpose": "User assignment queue."},
    {"id": "request_history", "name": "Requests History", "route": "/requests/history", "purpose": "Completed request history."},
    {"id": "request_details", "name": "Request Details", "route": "/requests/:id", "purpose": "Single request detail view."},
    {"id": "departments", "name": "Departments", "route": "/departments", "purpose": "Workflow department management."},
    {"id": "registry", "name": "Registry", "route": "/registry", "purpose": "Companies, clients, and client objects."},
    {"id": "forms", "name": "Form Templates", "route": "/forms", "purpose": "Dynamic form template list."},
    {"id": "form_builder", "name": "Form Builder", "route": "/forms/new", "purpose": "Create dynamic form templates."},
    {"id": "form_editor", "name": "Form Editor", "route": "/forms/:id/edit", "purpose": "Edit dynamic form templates."},
    {"id": "form_fill", "name": "Form Fill", "route": "/forms/:id/fill", "purpose": "Submit records through a template."},
    {"id": "form_records", "name": "Form Records", "route": "/forms/:id/records", "purpose": "Review submitted form records."},
    {"id": "form_queue", "name": "Form Queue", "route": "/forms/:id/queue", "purpose": "Queue generated workflow requests."},
    {"id": "files", "name": "Files", "route": "/files", "purpose": "Workspace file attachments."},
    {"id": "reports", "name": "Reports", "route": "/reports", "purpose": "Run and export reports."},
    {"id": "report_types", "name": "Report Types", "route": "/report-types", "purpose": "Configure report templates."},
    {"id": "modules", "name": "CRM Modules", "route": "/modules", "purpose": "Inspect enabled core CRM modules."},
    {"id": "module_detail", "name": "CRM Module Detail", "route": "/modules/:moduleId", "purpose": "Core module details."},
    {"id": "ai_architect", "name": "AI Architect", "route": "/ai-architect", "purpose": "AI CRM blueprint and refinement flow."},
    {"id": "admin", "name": "Admin Panel", "route": "/admin", "purpose": "Users, roles, and workspace administration."},
    {"id": "superadmin", "name": "Workspace Management", "route": "/superadmin", "purpose": "System workspace management."},
]


EXISTING_CRM_MECHANISMS = [
    {
        "id": "workflow",
        "name": "Workflow requests",
        "methods": ["create requests", "assign users", "track status", "track priority", "route by department"],
    },
    {
        "id": "dynamic_forms",
        "name": "Dynamic forms",
        "methods": ["create templates", "edit templates", "submit records", "generate workflow requests", "review queues"],
    },
    {
        "id": "registry",
        "name": "Registry",
        "methods": ["manage companies", "manage clients", "manage client objects", "autocomplete client data"],
    },
    {
        "id": "reports",
        "name": "Reports",
        "methods": ["configure report types", "run reports", "export reports", "build analytics columns"],
    },
    {
        "id": "files",
        "name": "Files",
        "methods": ["attach workspace files", "link files to requests", "link files to users"],
    },
    {
        "id": "notifications",
        "name": "Notifications",
        "methods": ["store in-app notifications", "mark notifications read", "notify workspace activity"],
    },
    {
        "id": "module_registry",
        "name": "Module registry",
        "methods": ["list modules", "install module templates", "track installed templates"],
    },
    {
        "id": "access_control",
        "name": "Access control",
        "methods": ["manage users", "manage roles", "check permissions", "scope data by workspace"],
    },
]


def build_platform_context(db, workspace_id) -> dict:
    from modules.access_control.models import Workspace
    from modules.module_registry.service import ModuleService

    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    module_settings = ModuleService.serialize_workspace_modules(workspace)
    enabled_module_ids = module_settings.get("enabled_modules", [])
    enabled_set = set(enabled_module_ids)

    enabled_modules = [
        ModuleService.serialize_module_definition(definition)
        for definition in ModuleService.list_module_definitions()
        if definition.id in enabled_set
    ]
    module_templates = [
        ModuleService.serialize_module_manifest(manifest)
        for manifest in ModuleService.list_module_manifests(enabled_module_ids)
    ]

    return {
        "existing_pages": EXISTING_CRM_PAGES,
        "existing_mechanisms": EXISTING_CRM_MECHANISMS,
        "workspace_modules": module_settings,
        "enabled_modules": enabled_modules,
        "module_templates": module_templates,
    }
