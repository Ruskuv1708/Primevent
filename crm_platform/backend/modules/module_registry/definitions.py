from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSynergy:
    module_id: str
    label: str
    description: str


@dataclass(frozen=True)
class ModuleDefinition:
    id: str
    label: str
    category: str
    description: str
    route_path: str = ""
    summary: str = ""
    capabilities: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    synergies: tuple[ModuleSynergy, ...] = ()
    default_enabled: bool = False


@dataclass(frozen=True)
class ModuleTemplateDefinition:
    id: str
    label: str
    template_type: str
    description: str
    fields: tuple[str, ...]
    stages: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModuleManifest:
    module_id: str
    templates: tuple[ModuleTemplateDefinition, ...]


MODULE_ORDER = (
    "workspace_home",
    "dashboard",
    "registry",
    "workflow",
    "open_requests",
    "assigned_work",
    "request_history",
    "departments",
    "animator_schedule",
    "employee_evaluations",
    "dynamic_forms",
    "form_templates",
    "form_builder",
    "files",
    "reports",
    "report_library",
    "report_types",
    "notifications",
    "profile",
    "ai_architect",
    "admin_panel",
    "superadmin_panel",
)

DEFAULT_ENABLED_MODULE_IDS = MODULE_ORDER

MODULE_DEFINITIONS: dict[str, ModuleDefinition] = {
    "workspace_home": ModuleDefinition(
        id="workspace_home",
        label="Главная",
        category="functional",
        description="Стартовая страница рабочей области.",
        route_path="/home",
        summary="Workspace landing page with enabled sections and operational context.",
        capabilities=("Workspace overview", "Quick navigation"),
        default_enabled=True,
    ),
    "dashboard": ModuleDefinition(
        id="dashboard",
        label="Дашборд",
        category="functional",
        description="Операционная панель с быстрыми действиями и текущими показателями.",
        route_path="/dashboard",
        summary="Dashboard for request activity, forms, and workspace shortcuts.",
        capabilities=("Workspace metrics", "Quick request actions"),
        default_enabled=True,
    ),
    "registry": ModuleDefinition(
        id="registry",
        label="Клиенты",
        category="functional",
        description="Companies, clients, and client objects shared by CRM modules.",
        route_path="/registry",
        summary="Client and company registry.",
        capabilities=("Client records", "Company records", "Client objects"),
        default_enabled=True,
    ),
    "workflow": ModuleDefinition(
        id="workflow",
        label="Workflow Engine",
        category="functional",
        description="Internal request lifecycle, assignments, departments, and priorities engine.",
        default_enabled=True,
    ),
    "open_requests": ModuleDefinition(
        id="open_requests",
        label="Открыть заявки",
        category="functional",
        description="Список открытых заявок рабочей области.",
        route_path="/requests",
        summary="Open request list with status, assignee, priority, and lifecycle controls.",
        capabilities=("Request list", "Request status tracking"),
        synergies=(
            ModuleSynergy(
                module_id="notifications",
                label="Уведомления по заявкам",
                description="Если включить Notifications, новые и просроченные заявки смогут давать счетчики и системные уведомления.",
            ),
            ModuleSynergy(
                module_id="reports",
                label="Отчеты по заявкам",
                description="Если включить Reports, заявки можно использовать как источник для отчетов по статусам и нагрузке.",
            ),
        ),
        default_enabled=True,
    ),
    "assigned_work": ModuleDefinition(
        id="assigned_work",
        label="Открыть назначенную работу",
        category="functional",
        description="Заявки, назначенные текущему пользователю.",
        route_path="/requests/assigned",
        summary="Assigned work queue for performers and managers.",
        capabilities=("Assigned request queue", "Personal workload tracking"),
        synergies=(
            ModuleSynergy(
                module_id="notifications",
                label="Уведомления исполнителям",
                description="Если включить Notifications, назначенные исполнители смогут видеть новые назначения и изменения.",
            ),
        ),
        default_enabled=True,
    ),
    "request_history": ModuleDefinition(
        id="request_history",
        label="История заявок",
        category="functional",
        description="Архив и история обработанных заявок.",
        route_path="/requests/history",
        summary="Request history and lifecycle audit trail.",
        capabilities=("Request archive", "Lifecycle history"),
        synergies=(
            ModuleSynergy(
                module_id="reports",
                label="Исторические отчеты",
                description="Если включить Reports, история заявок сможет участвовать в отчетах по срокам и закрытию работ.",
            ),
        ),
        default_enabled=True,
    ),
    "departments": ModuleDefinition(
        id="departments",
        label="Отделы",
        category="functional",
        description="Отделы, рейтинги и назначение ответственных.",
        route_path="/departments",
        summary="Department management for request routing and rankings.",
        capabilities=("Department management", "Routing ownership"),
        synergies=(
            ModuleSynergy(
                module_id="workflow",
                label="Маршрутизация заявок",
                description="Если включить Workflow Engine, отделы можно использовать для распределения заявок и ответственности.",
            ),
        ),
        default_enabled=True,
    ),
    "animator_schedule": ModuleDefinition(
        id="animator_schedule",
        label="График",
        category="functional",
        description="Заказы аниматоров, занятость, назначения и пересечения по времени.",
        route_path="/animator-schedule",
        summary="Schedule orders on a calendar grid, assign animators, track personal busy time, and spot overlaps.",
        capabilities=(
            "Schedule grid with readable time blocks",
            "Animator assignment and overlap visibility",
            "Personal unavailability and manager-entered busy time",
            "Order intake with client, program, date, time, duration, and payment fields",
        ),
        synergies=(
            ModuleSynergy(
                module_id="registry",
                label="Связь с клиентами",
                description="Если включить Клиенты, события графика можно привязывать к существующим клиентам и контактам.",
            ),
            ModuleSynergy(
                module_id="workflow",
                label="Заявки из событий",
                description="Если включить Workflow Engine, заказ или репетиция смогут создавать рабочие заявки и назначения.",
            ),
            ModuleSynergy(
                module_id="employee_evaluations",
                label="Оценка по событиям",
                description="Если включить Оценку сотрудников, менеджер сможет учитывать участие аниматора в заказах и репетициях.",
            ),
            ModuleSynergy(
                module_id="reports",
                label="Отчеты по графику",
                description="Если включить Reports, график можно использовать в отчетах по загрузке, накладкам и оплатам.",
            ),
        ),
        default_enabled=True,
    ),
    "employee_evaluations": ModuleDefinition(
        id="employee_evaluations",
        label="Оценка сотрудников",
        category="functional",
        description="Индивидуальные KPI-пункты сотрудников с оценками от 1 до 10.",
        route_path="/employee-evaluations",
        summary="Employee KPI evaluation list with per-person criteria, scores, comments, and manager review context.",
        capabilities=(
            "Individual KPI criteria per employee",
            "Score each KPI from 1 to 10",
            "Admin-managed employee performance notes",
            "Employee self-view for assigned evaluation items",
        ),
        synergies=(
            ModuleSynergy(
                module_id="animator_schedule",
                label="KPI по событиям",
                description="Если включить График, оценки можно сверять с участием сотрудника в заказах и репетициях.",
            ),
            ModuleSynergy(
                module_id="reports",
                label="KPI-отчеты",
                description="Если включить Reports, оценки сотрудников можно выводить в отчеты по эффективности.",
            ),
        ),
        default_enabled=True,
    ),
    "dynamic_forms": ModuleDefinition(
        id="dynamic_forms",
        label="Dynamic Forms Engine",
        category="functional",
        description="Internal form templates, records, queues, and generated workflow request engine.",
        synergies=(
            ModuleSynergy(
                module_id="workflow",
                label="Заявки из форм",
                description="Если включить Workflow Engine, заполненная форма сможет создавать заявку и запускать обработку.",
            ),
            ModuleSynergy(
                module_id="reports",
                label="Отчеты по формам",
                description="Если включить Reports, записи форм можно использовать как источник отчетов.",
            ),
        ),
        default_enabled=True,
    ),
    "form_templates": ModuleDefinition(
        id="form_templates",
        label="Открыть формы",
        category="functional",
        description="Список шаблонов динамических форм.",
        route_path="/forms",
        summary="Dynamic form template library.",
        capabilities=("Form template list", "Form records access"),
        synergies=(
            ModuleSynergy(
                module_id="form_builder",
                label="Создание шаблонов",
                description="Если включить Новый шаблон, список форм можно пополнять новыми шаблонами из интерфейса.",
            ),
        ),
        default_enabled=True,
    ),
    "form_builder": ModuleDefinition(
        id="form_builder",
        label="Новый шаблон",
        category="functional",
        description="Создание новых шаблонов динамических форм.",
        route_path="/forms/new",
        summary="Form builder for new request and record templates.",
        capabilities=("Template builder", "Field configuration"),
        synergies=(
            ModuleSynergy(
                module_id="form_templates",
                label="Библиотека форм",
                description="Если включить Открыть формы, созданные шаблоны сразу доступны в библиотеке и очередях записей.",
            ),
        ),
        default_enabled=True,
    ),
    "files": ModuleDefinition(
        id="files",
        label="Files",
        category="functional",
        description="Workspace file attachments for requests, users, and CRM records.",
        default_enabled=True,
    ),
    "reports": ModuleDefinition(
        id="reports",
        label="Reports Engine",
        category="functional",
        description="Internal report exports, report type templates, and workspace analytics engine.",
        default_enabled=True,
    ),
    "report_library": ModuleDefinition(
        id="report_library",
        label="Открыть отчеты",
        category="functional",
        description="Библиотека отчетов и выгрузок.",
        route_path="/reports",
        summary="Stored reports and exports for the workspace.",
        capabilities=("Report library", "Generated exports"),
        synergies=(
            ModuleSynergy(
                module_id="report_types",
                label="Настройка типов",
                description="Если включить Типы отчетов, библиотека сможет использовать настраиваемые колонки и типы выгрузок.",
            ),
        ),
        default_enabled=True,
    ),
    "report_types": ModuleDefinition(
        id="report_types",
        label="Типы отчетов",
        category="functional",
        description="Настройка типов и колонок отчетов.",
        route_path="/report-types",
        summary="Report type builder and report column configuration.",
        capabilities=("Report type templates", "Report column configuration"),
        synergies=(
            ModuleSynergy(
                module_id="report_library",
                label="Библиотека отчетов",
                description="Если включить Открыть отчеты, настроенные типы можно использовать для создания отчетов.",
            ),
        ),
        default_enabled=True,
    ),
    "notifications": ModuleDefinition(
        id="notifications",
        label="Notifications",
        category="functional",
        description="In-app and future external notifications for workspace activity.",
        default_enabled=True,
    ),
    "profile": ModuleDefinition(
        id="profile",
        label="Профиль",
        category="functional",
        description="Профиль пользователя и персональные настройки.",
        route_path="/profile",
        summary="User profile, account settings, and language preferences.",
        capabilities=("Profile preferences", "Account information"),
        default_enabled=True,
    ),
    "ai_architect": ModuleDefinition(
        id="ai_architect",
        label="AI Архитектор",
        category="functional",
        description="AI-assisted CRM blueprint generation, refinement, application, and rollback.",
        route_path="/ai-architect",
        summary="Generate CRM blueprints, refine forms and reports, apply changes, and roll them back when needed.",
        capabilities=(
            "CRM blueprint generation",
            "Form and report refinement proposals",
            "Change application history",
            "Rollback of applied AI changes",
        ),
        synergies=(
            ModuleSynergy(
                module_id="dynamic_forms",
                label="Проектирование форм",
                description="Если включить Dynamic Forms Engine, AI Архитектор сможет предлагать и применять шаблоны форм.",
            ),
            ModuleSynergy(
                module_id="reports",
                label="Проектирование отчетов",
                description="Если включить Reports Engine, AI Архитектор сможет предлагать типы отчетов и аналитику.",
            ),
            ModuleSynergy(
                module_id="workflow",
                label="Проектирование процессов",
                description="Если включить Workflow Engine, AI Архитектор сможет учитывать жизненный цикл заявок и роли.",
            ),
        ),
        default_enabled=True,
    ),
    "admin_panel": ModuleDefinition(
        id="admin_panel",
        label="Админ",
        category="functional",
        description="Управление пользователями, ролями и настройками рабочей области.",
        route_path="/admin",
        summary="Workspace administration for users, roles, and permissions.",
        capabilities=("User management", "Role management", "Workspace permissions"),
        default_enabled=True,
    ),
    "superadmin_panel": ModuleDefinition(
        id="superadmin_panel",
        label="Суперадмин",
        category="functional",
        description="Системное управление рабочими областями и глобальными настройками.",
        route_path="/superadmin",
        summary="System-level workspace, module, AI provider, and password administration.",
        capabilities=("Workspace management", "Module management", "AI provider settings"),
        default_enabled=True,
    ),
}

MODULE_PRESET_DEFAULTS: dict[str, tuple[str, ...]] = {
    "functional": DEFAULT_ENABLED_MODULE_IDS,
}

MODULE_MANIFESTS: dict[str, ModuleManifest] = {}
