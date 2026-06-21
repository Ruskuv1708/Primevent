#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from sqlalchemy.orm import Session, configure_mappers

from core.config import settings
from core.database_connector import SessionLocal
from modules.access_control.enums import UserRole, WorkspaceStatus
from modules.access_control.models import User, Workspace, WorkspaceRole
from modules.access_control.permissions import PermissionService
from modules.access_control.service import pwd_context
from modules.ai_architect.models import (
    AIBusinessBlueprint,
    AIChangeEvent,
    AIChangeProposal,
    AIConversation,
    AIConversationMessage,
)
from modules.animator_schedule.models import AnimatorBooking, AnimatorUnavailability
from modules.dynamic_records.models import FormRecord, FormTemplate
from modules.employee_evaluations.models import EmployeeEvaluation
from modules.file_storage.models import FileAttachment
from modules.module_registry.definitions import DEFAULT_ENABLED_MODULE_IDS
from modules.module_registry.install_service import ModuleInstallService
from modules.module_registry.service import ModuleService
from modules.notifications.models import Notification
from modules.registry.models import Client, ClientObject, Company
from modules.reports.models import ReportType
from modules.workflow.enums import RequestPriority, RequestStatus
from modules.workflow.models import Department, Request

DEV_WORKSPACE_EMAIL = "test.crm.admin@example.com"
DEV_WORKSPACE_PASSWORD = "TestCrmDev123!"
DEV_WORKSPACE_NAME = "Test CRM Development"
DEV_WORKSPACE_SUBDOMAIN = "testcrm"

DEV_DEPARTMENT_SPECS = (
    ("Sales", "Lead qualification, pipeline movement, and customer follow-up"),
    ("Operations", "Delivery queue, service ownership, and customer success handoff"),
    ("Finance", "Approvals, payments, billing, and budget checks"),
    ("Development Lab", "Feature testing, QA regression work, and integration checks"),
    ("Support", "Customer support, incident triage, and retention workflows"),
)

DEV_USER_SPECS = (
    ("test.crm.superadmin@example.com", "Test CRM Superadmin", UserRole.SUPERADMIN, None),
    ("test.crm.system@example.com", "Test CRM System Admin", UserRole.SYSTEM_ADMIN, None),
    (DEV_WORKSPACE_EMAIL, "Test CRM Admin", UserRole.ADMIN, None),
    ("test.crm.manager@example.com", "Test CRM Sales Manager", UserRole.MANAGER, "Sales"),
    ("test.crm.operator@example.com", "Test CRM Operator", UserRole.USER, "Operations"),
    ("test.crm.viewer@example.com", "Test CRM Viewer", UserRole.VIEWER, "Support"),
)

DEV_FORM_TEMPLATE_SPECS = (
    (
        "Lead Intake",
        [
            {"key": "customer_name", "label": "Customer Name", "type": "text", "required": True},
            {"key": "phone", "label": "Phone", "type": "text", "required": True},
            {"key": "source", "label": "Lead Source", "type": "text", "required": False},
            {"key": "message_volume", "label": "Monthly Message Volume", "type": "number", "required": False},
        ],
        "Sales",
        "Qualify {customer_name}",
        "Lead came from {source}. Phone: {phone}. Expected monthly messages: {message_volume}.",
    ),
    (
        "Text Campaign Brief",
        [
            {"key": "campaign_name", "label": "Campaign Name", "type": "text", "required": True},
            {"key": "audience", "label": "Audience", "type": "text", "required": True},
            {"key": "send_date", "label": "Send Date", "type": "date", "required": False},
            {"key": "approval_priority", "label": "Approval Priority", "type": "priority_select", "required": False},
        ],
        "Operations",
        "Prepare campaign {campaign_name}",
        "Audience: {audience}. Target send date: {send_date}.",
    ),
    (
        "Support Ticket",
        [
            {"key": "client_name", "label": "Client Name", "type": "text", "required": True},
            {"key": "issue", "label": "Issue", "type": "textarea", "required": True},
            {"key": "severity", "label": "Severity", "type": "priority_select", "required": False},
        ],
        "Support",
        "Support ticket for {client_name}",
        "{issue}",
    ),
    (
        "Feature Request",
        [
            {"key": "feature_name", "label": "Feature Name", "type": "text", "required": True},
            {"key": "business_value", "label": "Business Value", "type": "textarea", "required": True},
            {"key": "owner", "label": "Owner", "type": "text", "required": False},
        ],
        "Development Lab",
        "Evaluate feature {feature_name}",
        "{business_value}",
    ),
)

DEV_REPORT_TYPE_SPECS = (
    (
        "Open Requests",
        "Request queue with owner, status, and priority fields.",
        "requests",
        [
            {"key": "title", "label": "Title"},
            {"key": "status", "label": "Status"},
            {"key": "priority", "label": "Priority"},
            {"key": "assignee_name", "label": "Assignee"},
        ],
    ),
    (
        "Campaign Pipeline",
        "Campaign-oriented form records for launch readiness reviews.",
        "forms",
        [
            {"key": "campaign_name", "label": "Campaign"},
            {"key": "audience", "label": "Audience"},
            {"key": "send_date", "label": "Send Date"},
            {"key": "approval_priority", "label": "Priority"},
        ],
    ),
    (
        "Customer Directory",
        "Companies, clients, and contact fields for CRM development.",
        "clients",
        [
            {"key": "full_name", "label": "Customer"},
            {"key": "email", "label": "Email"},
            {"key": "phone", "label": "Phone"},
            {"key": "company_name", "label": "Company"},
        ],
    ),
    (
        "Employee KPI",
        "Employee evaluation exports for manager and admin flows.",
        "employee_evaluations",
        [
            {"key": "employee_name", "label": "Employee"},
            {"key": "title", "label": "KPI"},
            {"key": "score", "label": "Score"},
            {"key": "period_label", "label": "Period"},
        ],
    ),
)


def development_workspace_summary() -> dict[str, object]:
    return {
        "workspace_name": DEV_WORKSPACE_NAME,
        "subdomain": DEV_WORKSPACE_SUBDOMAIN,
        "admin_email": DEV_WORKSPACE_EMAIL,
        "enabled_modules": list(DEFAULT_ENABLED_MODULE_IDS),
        "department_count": len(DEV_DEPARTMENT_SPECS),
        "user_count": len(DEV_USER_SPECS),
        "form_template_count": len(DEV_FORM_TEMPLATE_SPECS),
        "report_type_count": len(DEV_REPORT_TYPE_SPECS),
    }


def _ensure_dev_target(email: str, subdomain: str) -> None:
    if email.strip().lower() != DEV_WORKSPACE_EMAIL:
        raise ValueError("Refusing to reset a non-development workspace email")
    if subdomain.strip().lower() != DEV_WORKSPACE_SUBDOMAIN:
        raise ValueError("Refusing to reset a non-development workspace subdomain")


def reset_dev_workspace(db: Session, *, admin_email: str = DEV_WORKSPACE_EMAIL, subdomain: str = DEV_WORKSPACE_SUBDOMAIN) -> None:
    _ensure_dev_target(admin_email, subdomain)
    workspace = db.query(Workspace).filter(Workspace.subdomain_prefix == DEV_WORKSPACE_SUBDOMAIN).first()
    if workspace is None:
        return

    template_ids = [item.id for item in db.query(FormTemplate.id).filter(FormTemplate.workspace_id == workspace.id)]
    if template_ids:
        db.query(FormRecord).filter(FormRecord.template_id.in_(template_ids)).delete(synchronize_session=False)

    files = db.query(FileAttachment).filter(FileAttachment.workspace_id == workspace.id).all()
    for file_record in files:
        try:
            if file_record.physical_path and os.path.exists(file_record.physical_path):
                os.remove(file_record.physical_path)
        except OSError:
            pass

    db.query(AIChangeEvent).filter(AIChangeEvent.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AIChangeProposal).filter(AIChangeProposal.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AIBusinessBlueprint).filter(AIBusinessBlueprint.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AIConversationMessage).filter(AIConversationMessage.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AIConversation).filter(AIConversation.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(FileAttachment).filter(FileAttachment.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(EmployeeEvaluation).filter(EmployeeEvaluation.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AnimatorUnavailability).filter(AnimatorUnavailability.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AnimatorBooking).filter(AnimatorBooking.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(ClientObject).filter(ClientObject.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Client).filter(Client.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Company).filter(Company.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Request).filter(Request.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(FormTemplate).filter(FormTemplate.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(ReportType).filter(ReportType.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(User).filter(User.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(WorkspaceRole).filter(WorkspaceRole.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Department).filter(Department.workspace_id == workspace.id).delete(synchronize_session=False)
    db.delete(workspace)
    db.flush()


def _upsert_workspace(db: Session) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.subdomain_prefix == DEV_WORKSPACE_SUBDOMAIN).first()
    workspace_settings = ModuleService.build_workspace_settings(
        existing_settings={},
        module_preset=ModuleService.DEFAULT_PRESET,
        enabled_modules=list(DEFAULT_ENABLED_MODULE_IDS),
    )
    workspace_settings["seed"] = {
        "name": "text_crm_development",
        "purpose": "all_functionality_development",
    }

    if workspace is None:
        workspace = Workspace(
            name=DEV_WORKSPACE_NAME,
            subdomain_prefix=DEV_WORKSPACE_SUBDOMAIN,
            admin_email=DEV_WORKSPACE_EMAIL,
            admin_full_name="Test CRM Admin",
            status=WorkspaceStatus.ACTIVE.value,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            activated_at=datetime.now(timezone.utc),
            settings=workspace_settings,
        )
        db.add(workspace)
        db.flush()
    else:
        workspace.name = DEV_WORKSPACE_NAME
        workspace.admin_email = DEV_WORKSPACE_EMAIL
        workspace.admin_full_name = "Test CRM Admin"
        workspace.status = WorkspaceStatus.ACTIVE.value
        workspace.is_active = True
        workspace.activated_at = workspace.activated_at or datetime.now(timezone.utc)
        workspace.settings = workspace_settings

    ModuleInstallService.install_enabled_modules(
        db,
        workspace.id,
        workspace.settings.get(ModuleService.SETTINGS_ENABLED_KEY) if isinstance(workspace.settings, dict) else None,
    )
    return workspace


def _upsert_department(db: Session, workspace: Workspace, name: str, description: str) -> Department:
    department = (
        db.query(Department)
        .filter(Department.workspace_id == workspace.id, Department.name == name)
        .first()
    )
    if department is None:
        department = Department(name=name, description=description, workspace_id=workspace.id)
        db.add(department)
        db.flush()
    else:
        department.description = description
    return department


def _upsert_workspace_role(db: Session, workspace: Workspace, name: str, description: str, base_role: UserRole) -> WorkspaceRole:
    role = (
        db.query(WorkspaceRole)
        .filter(WorkspaceRole.workspace_id == workspace.id, WorkspaceRole.name == name)
        .first()
    )
    permissions = {
        permission: True
        for permission in PermissionService.PERMISSIONS.get(base_role, [])
    }
    if role is None:
        role = WorkspaceRole(
            workspace_id=workspace.id,
            name=name,
            description=description,
            base_role=base_role,
            permissions=permissions,
        )
        db.add(role)
        db.flush()
    else:
        role.description = description
        role.base_role = base_role
        role.permissions = permissions
    return role


def _upsert_user(
    db: Session,
    *,
    workspace: Workspace,
    email: str,
    full_name: str,
    password: str,
    role: UserRole,
    department: Department | None = None,
) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=pwd_context.hash(password),
            role=role,
            is_active=True,
            workspace_id=workspace.id,
            department_id=department.id if department else None,
            language="en",
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = full_name
        user.hashed_password = pwd_context.hash(password)
        user.role = role
        user.is_active = True
        user.workspace_id = workspace.id
        user.department_id = department.id if department else None
        user.language = "en"
    return user


def _upsert_company(db: Session, workspace: Workspace, *, name: str, email: str, phone: str, address: str) -> Company:
    company = db.query(Company).filter(Company.workspace_id == workspace.id, Company.name == name).first()
    if company is None:
        company = Company(name=name, email=email, phone=phone, address=address, workspace_id=workspace.id)
        db.add(company)
        db.flush()
    else:
        company.email = email
        company.phone = phone
        company.address = address
    return company


def _upsert_client(
    db: Session,
    workspace: Workspace,
    *,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    company: Company | None = None,
    notes: str | None = None,
) -> Client:
    client = db.query(Client).filter(Client.workspace_id == workspace.id, Client.email == email).first()
    if client is None:
        client = Client(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            company_id=company.id if company else None,
            workspace_id=workspace.id,
            notes=notes,
        )
        db.add(client)
        db.flush()
    else:
        client.first_name = first_name
        client.last_name = last_name
        client.phone = phone
        client.company_id = company.id if company else None
        client.notes = notes
    return client


def _upsert_client_object(
    db: Session,
    workspace: Workspace,
    *,
    name: str,
    client: Client | None = None,
    company: Company | None = None,
    attributes: dict | None = None,
) -> ClientObject:
    item = db.query(ClientObject).filter(ClientObject.workspace_id == workspace.id, ClientObject.name == name).first()
    if item is None:
        item = ClientObject(
            name=name,
            client_id=client.id if client else None,
            company_id=company.id if company else None,
            attributes=attributes or {},
            workspace_id=workspace.id,
        )
        db.add(item)
        db.flush()
    else:
        item.client_id = client.id if client else None
        item.company_id = company.id if company else None
        item.attributes = attributes or {}
    return item


def _upsert_template(
    db: Session,
    workspace: Workspace,
    *,
    name: str,
    schema_structure: list[dict],
    request_settings: dict | None = None,
) -> FormTemplate:
    template = db.query(FormTemplate).filter(FormTemplate.workspace_id == workspace.id, FormTemplate.name == name).first()
    if template is None:
        template = FormTemplate(
            name=name,
            schema_structure=schema_structure,
            workspace_id=workspace.id,
            meta_data={"request_settings": request_settings} if request_settings else {},
        )
        db.add(template)
        db.flush()
    else:
        template.schema_structure = schema_structure
        template.meta_data = {"request_settings": request_settings} if request_settings else {}
    return template


def _upsert_report_type(
    db: Session,
    workspace: Workspace,
    *,
    name: str,
    description: str,
    source: str,
    columns: list[dict],
) -> ReportType:
    report = db.query(ReportType).filter(ReportType.workspace_id == workspace.id, ReportType.name == name).first()
    if report is None:
        report = ReportType(
            name=name,
            description=description,
            source=source,
            columns=columns,
            is_active=True,
            workspace_id=workspace.id,
        )
        db.add(report)
        db.flush()
    else:
        report.description = description
        report.source = source
        report.columns = columns
        report.is_active = True
    return report


def _upsert_request(
    db: Session,
    workspace: Workspace,
    *,
    title: str,
    description: str,
    department: Department,
    creator: User,
    assignee: User | None,
    status: RequestStatus,
    priority: RequestPriority,
) -> Request:
    request = db.query(Request).filter(Request.workspace_id == workspace.id, Request.title == title).first()
    if request is None:
        request = Request(
            title=title,
            description=description,
            department_id=department.id,
            workspace_id=workspace.id,
            created_by_id=creator.id,
        )
        db.add(request)
        db.flush()
    request.description = description
    request.department_id = department.id
    request.created_by_id = creator.id
    request.assigned_to_id = assignee.id if assignee else None
    request.status = status
    request.priority = priority
    return request


def _upsert_form_record(
    db: Session,
    template: FormTemplate,
    *,
    seed_key: str,
    entry_data: dict,
    request: Request | None = None,
) -> FormRecord:
    record = next(
        (
            item
            for item in db.query(FormRecord).filter(FormRecord.template_id == template.id).all()
            if (item.meta_data or {}).get("seed_key") == seed_key
        ),
        None,
    )
    meta_data = {"seed_key": seed_key}
    if request is not None:
        meta_data["request_id"] = str(request.id)
    if record is None:
        record = FormRecord(template_id=template.id, entry_data=entry_data, meta_data=meta_data)
        db.add(record)
        db.flush()
    else:
        record.entry_data = entry_data
        record.meta_data = meta_data
    return record


def _upsert_booking(
    db: Session,
    workspace: Workspace,
    *,
    title: str,
    client_name: str,
    event_date: date,
    start_time: time,
    duration_minutes: int,
    assigned_users: list[User],
    program_name: str,
    color: str,
) -> AnimatorBooking:
    booking = db.query(AnimatorBooking).filter(AnimatorBooking.workspace_id == workspace.id, AnimatorBooking.title == title).first()
    assigned_animator_ids = [str(user.id) for user in assigned_users]
    if booking is None:
        booking = AnimatorBooking(
            workspace_id=workspace.id,
            event_type="order",
            title=title,
            client_name=client_name,
            client_phone="+998 90 000 11 22",
            event_date=event_date,
            start_time=start_time,
            duration_minutes=duration_minutes,
            address="Remote / Tashkent",
            program_name=program_name,
            price=1200,
            prepayment=300,
            payment_status="partial",
            inventory_notes="Seeded development booking",
            status="confirmed",
            color=color,
            notes="All-functionality seed event",
            assigned_animator_ids=assigned_animator_ids,
        )
        db.add(booking)
        db.flush()
    else:
        booking.client_name = client_name
        booking.event_date = event_date
        booking.start_time = start_time
        booking.duration_minutes = duration_minutes
        booking.program_name = program_name
        booking.assigned_animator_ids = assigned_animator_ids
        booking.color = color
    return booking


def _upsert_unavailability(
    db: Session,
    workspace: Workspace,
    *,
    animator: User,
    unavailable_date: date,
    start_time: time,
    duration_minutes: int,
    reason: str,
) -> AnimatorUnavailability:
    item = (
        db.query(AnimatorUnavailability)
        .filter(
            AnimatorUnavailability.workspace_id == workspace.id,
            AnimatorUnavailability.animator_id == animator.id,
            AnimatorUnavailability.unavailable_date == unavailable_date,
            AnimatorUnavailability.start_time == start_time,
        )
        .first()
    )
    if item is None:
        item = AnimatorUnavailability(
            workspace_id=workspace.id,
            animator_id=animator.id,
            unavailable_date=unavailable_date,
            start_time=start_time,
            duration_minutes=duration_minutes,
            reason=reason,
            notes="Seeded development availability block",
        )
        db.add(item)
        db.flush()
    else:
        item.duration_minutes = duration_minutes
        item.reason = reason
    return item


def _upsert_evaluation(
    db: Session,
    workspace: Workspace,
    *,
    employee: User,
    evaluator: User,
    title: str,
    score: int,
    period_label: str,
    comment: str,
) -> EmployeeEvaluation:
    evaluation = (
        db.query(EmployeeEvaluation)
        .filter(
            EmployeeEvaluation.workspace_id == workspace.id,
            EmployeeEvaluation.employee_id == employee.id,
            EmployeeEvaluation.title == title,
            EmployeeEvaluation.period_label == period_label,
        )
        .first()
    )
    if evaluation is None:
        evaluation = EmployeeEvaluation(
            workspace_id=workspace.id,
            employee_id=employee.id,
            evaluator_id=evaluator.id,
            title=title,
            description="Seeded development KPI",
            score=score,
            period_label=period_label,
            comment=comment,
        )
        db.add(evaluation)
        db.flush()
    else:
        evaluation.evaluator_id = evaluator.id
        evaluation.score = score
        evaluation.comment = comment
    return evaluation


def _upsert_notification(
    db: Session,
    workspace: Workspace,
    *,
    user: User,
    title: str,
    message: str,
    target_link: str,
    is_read: bool = False,
) -> Notification:
    notification = (
        db.query(Notification)
        .filter(Notification.workspace_id == workspace.id, Notification.user_id == user.id, Notification.title == title)
        .first()
    )
    if notification is None:
        notification = Notification(
            workspace_id=workspace.id,
            user_id=user.id,
            title=title,
            message=message,
            target_link=target_link,
            is_read=is_read,
        )
        db.add(notification)
        db.flush()
    else:
        notification.message = message
        notification.target_link = target_link
        notification.is_read = is_read
    return notification


def _upsert_seed_file(
    db: Session,
    workspace: Workspace,
    *,
    uploader: User,
    request: Request,
) -> FileAttachment:
    workspace_path = os.path.join(settings.FILE_STORAGE_ROOT, str(workspace.id))
    os.makedirs(workspace_path, exist_ok=True)
    physical_path = os.path.join(workspace_path, "development-seed-readme.txt")
    content = "Test CRM development workspace seed attachment.\n"
    with open(physical_path, "w", encoding="utf-8") as handle:
        handle.write(content)

    file_record = (
        db.query(FileAttachment)
        .filter(
            FileAttachment.workspace_id == workspace.id,
            FileAttachment.filename == "development-seed-readme.txt",
        )
        .first()
    )
    if file_record is None:
        file_record = FileAttachment(
            filename="development-seed-readme.txt",
            content_type="text/plain",
            file_size=len(content.encode("utf-8")),
            physical_path=physical_path,
            uploaded_by_id=uploader.id,
            workspace_id=workspace.id,
            entity_id=request.id,
            entity_type="request",
        )
        db.add(file_record)
        db.flush()
    else:
        file_record.file_size = len(content.encode("utf-8"))
        file_record.physical_path = physical_path
        file_record.uploaded_by_id = uploader.id
        file_record.entity_id = request.id
        file_record.entity_type = "request"
    return file_record


def _upsert_ai_story(
    db: Session,
    *,
    workspace: Workspace,
    admin: User,
    campaign_template: FormTemplate,
) -> None:
    conversation = (
        db.query(AIConversation)
        .filter(AIConversation.workspace_id == workspace.id, AIConversation.title == "Test CRM Development Blueprint")
        .first()
    )
    if conversation is None:
        conversation = AIConversation(
            workspace_id=workspace.id,
            title="Test CRM Development Blueprint",
            status="active",
        )
        db.add(conversation)
        db.flush()

    message_specs = (
        ("owner", "Create a CRM workspace where every module can be tested together."),
        ("ai", "I prepared a full-module development seed with forms, reports, requests, schedule, and access data."),
    )
    for sender, content in message_specs:
        message = (
            db.query(AIConversationMessage)
            .filter(
                AIConversationMessage.conversation_id == conversation.id,
                AIConversationMessage.sender == sender,
                AIConversationMessage.content == content,
            )
            .first()
        )
        if message is None:
            db.add(
                AIConversationMessage(
                    conversation_id=conversation.id,
                    workspace_id=workspace.id,
                    sender=sender,
                    content=content,
                )
            )

    blueprint_payload = {
        "business_profile": "text_crm",
        "business_summary": "Development workspace for text campaign CRM functionality.",
        "entities": ["Companies", "Clients", "Campaigns", "Requests", "Reports", "Users"],
        "enabled_modules": list(DEFAULT_ENABLED_MODULE_IDS),
    }
    blueprint = db.query(AIBusinessBlueprint).filter(AIBusinessBlueprint.conversation_id == conversation.id).first()
    if blueprint is None:
        blueprint = AIBusinessBlueprint(
            conversation_id=conversation.id,
            workspace_id=workspace.id,
            version="v1",
            blueprint=blueprint_payload,
        )
        db.add(blueprint)
        db.flush()
    else:
        blueprint.blueprint = blueprint_payload

    artifact = {"type": "form", "id": str(campaign_template.id), "name": campaign_template.name}
    proposal = (
        db.query(AIChangeProposal)
        .filter(AIChangeProposal.workspace_id == workspace.id, AIChangeProposal.blueprint_id == blueprint.id)
        .first()
    )
    if proposal is None:
        proposal = AIChangeProposal(
            workspace_id=workspace.id,
            blueprint_id=blueprint.id,
            proposal_type="forms",
            operation="update",
            title="Refine text campaign approval form",
            description="Add campaign approval fields used by the development workflow.",
            rationale="Campaign launches need consistent owner, audience, and approval data.",
        )
        db.add(proposal)
        db.flush()
    proposal.generated_artifacts = [{"type": "form", "name": campaign_template.name}]
    proposal.applied_artifacts = [artifact]
    proposal.before_state = {"schema_structure": []}
    proposal.after_state = {"schema_structure": campaign_template.schema_structure}
    proposal.risk_level = "low"
    proposal.status = "applied"

    event = db.query(AIChangeEvent).filter(AIChangeEvent.workspace_id == workspace.id, AIChangeEvent.proposal_id == proposal.id).first()
    if event is None:
        event = AIChangeEvent(
            workspace_id=workspace.id,
            proposal_id=proposal.id,
            conversation_id=conversation.id,
            actor_id=admin.id,
            operation="update",
        )
        db.add(event)
        db.flush()
    event.affected_artifacts = [artifact]
    event.before_state = {"schema_structure": []}
    event.after_state = {"schema_structure": campaign_template.schema_structure}
    event.rollback_status = "available"


def seed_dev_workspace(db: Session, *, password: str = DEV_WORKSPACE_PASSWORD) -> Workspace:
    workspace = _upsert_workspace(db)
    departments = {
        name: _upsert_department(db, workspace, name, description)
        for name, description in DEV_DEPARTMENT_SPECS
    }
    _upsert_workspace_role(
        db,
        workspace,
        "Campaign Operator",
        "Can handle day-to-day campaign requests, forms, files, and customer records.",
        UserRole.USER,
    )
    _upsert_workspace_role(
        db,
        workspace,
        "Operations Manager",
        "Can manage request assignment, forms, files, and customer records.",
        UserRole.MANAGER,
    )

    users: dict[str, User] = {}
    for email, full_name, role, department_name in DEV_USER_SPECS:
        users[email] = _upsert_user(
            db,
            workspace=workspace,
            email=email,
            full_name=full_name,
            password=password,
            role=role,
            department=departments.get(department_name) if department_name else None,
        )

    admin = users[DEV_WORKSPACE_EMAIL]
    manager = users["test.crm.manager@example.com"]
    operator = users["test.crm.operator@example.com"]
    viewer = users["test.crm.viewer@example.com"]

    atlas = _upsert_company(
        db,
        workspace,
        name="Atlas Retail",
        email="ops@atlas-retail.example.com",
        phone="+998 71 210 10 10",
        address="Tashkent",
    )
    clinic = _upsert_company(
        db,
        workspace,
        name="City Clinic",
        email="contact@city-clinic.example.com",
        phone="+998 71 220 20 20",
        address="Yunusabad",
    )
    academy = _upsert_company(
        db,
        workspace,
        name="EduPro Academy",
        email="hello@edupro.example.com",
        phone="+998 71 230 30 30",
        address="Mirabad",
    )
    dilnoza = _upsert_client(
        db,
        workspace,
        first_name="Dilnoza",
        last_name="Karimova",
        email="dilnoza.karimova@example.com",
        phone="+998 90 111 22 33",
        company=atlas,
        notes="Interested in segmented text campaigns.",
    )
    sardor = _upsert_client(
        db,
        workspace,
        first_name="Sardor",
        last_name="Nazarov",
        email="sardor.nazarov@example.com",
        phone="+998 90 444 55 66",
        company=clinic,
        notes="Needs appointment reminders and support follow-up.",
    )
    _upsert_client(
        db,
        workspace,
        first_name="Malika",
        last_name="Rakhimova",
        email="malika.rakhimova@example.com",
        phone="+998 90 777 88 99",
        company=academy,
        notes="Evaluating lead nurture automation.",
    )
    _upsert_client_object(
        db,
        workspace,
        name="Atlas VIP Segment",
        company=atlas,
        client=dilnoza,
        attributes={"segment": "vip", "channel": "sms", "monthly_volume": 18000},
    )
    _upsert_client_object(
        db,
        workspace,
        name="Clinic Reminder Program",
        company=clinic,
        client=sardor,
        attributes={"segment": "healthcare", "channel": "sms", "frequency": "daily"},
    )

    templates: dict[str, FormTemplate] = {}
    for name, schema_structure, department_name, title_template, description_template in DEV_FORM_TEMPLATE_SPECS:
        department = departments[department_name]
        templates[name] = _upsert_template(
            db,
            workspace,
            name=name,
            schema_structure=schema_structure,
            request_settings={
                "enabled": True,
                "department_id": str(department.id),
                "priority": "medium",
                "title_template": title_template,
                "description_template": description_template,
            },
        )

    for name, description, source, columns in DEV_REPORT_TYPE_SPECS:
        _upsert_report_type(
            db,
            workspace,
            name=name,
            description=description,
            source=source,
            columns=columns,
        )

    lead_request = _upsert_request(
        db,
        workspace,
        title="Qualify Atlas Retail text CRM lead",
        description="Review contact list volume, segmentation needs, and first campaign goals.",
        department=departments["Sales"],
        creator=admin,
        assignee=manager,
        status=RequestStatus.ASSIGNED,
        priority=RequestPriority.HIGH,
    )
    campaign_request = _upsert_request(
        db,
        workspace,
        title="Prepare VIP reactivation campaign",
        description="Draft audience, approval path, and launch checklist for Atlas Retail.",
        department=departments["Operations"],
        creator=manager,
        assignee=operator,
        status=RequestStatus.IN_PROCESS,
        priority=RequestPriority.CRITICAL,
    )
    _upsert_request(
        db,
        workspace,
        title="Approve June message budget",
        description="Finance approval for estimated monthly text delivery volume.",
        department=departments["Finance"],
        creator=admin,
        assignee=None,
        status=RequestStatus.PENDING,
        priority=RequestPriority.MEDIUM,
    )
    _upsert_request(
        db,
        workspace,
        title="Verify support ticket workflow",
        description="Closed request used for request history and regression testing.",
        department=departments["Support"],
        creator=operator,
        assignee=viewer,
        status=RequestStatus.DONE,
        priority=RequestPriority.LOW,
    )

    _upsert_form_record(
        db,
        templates["Lead Intake"],
        seed_key="atlas-lead-intake",
        entry_data={
            "customer_name": "Atlas Retail",
            "phone": "+998 71 210 10 10",
            "source": "Referral",
            "message_volume": 18000,
        },
        request=lead_request,
    )
    _upsert_form_record(
        db,
        templates["Text Campaign Brief"],
        seed_key="atlas-vip-reactivation",
        entry_data={
            "campaign_name": "Atlas VIP Reactivation",
            "audience": "VIP customers inactive for 60 days",
            "send_date": str(date.today() + timedelta(days=7)),
            "approval_priority": "high",
        },
        request=campaign_request,
    )
    _upsert_form_record(
        db,
        templates["Support Ticket"],
        seed_key="clinic-reminder-delay",
        entry_data={
            "client_name": "City Clinic",
            "issue": "Reminder messages delayed during evening batch.",
            "severity": "medium",
        },
    )

    today = date.today()
    _upsert_booking(
        db,
        workspace,
        title="Atlas campaign kickoff",
        client_name="Atlas Retail",
        event_date=today + timedelta(days=1),
        start_time=time(10, 0),
        duration_minutes=90,
        assigned_users=[manager, operator],
        program_name="Campaign Launch",
        color="#2563eb",
    )
    _upsert_booking(
        db,
        workspace,
        title="City Clinic workflow review",
        client_name="City Clinic",
        event_date=today + timedelta(days=2),
        start_time=time(14, 30),
        duration_minutes=60,
        assigned_users=[operator],
        program_name="Support Review",
        color="#16a34a",
    )
    _upsert_unavailability(
        db,
        workspace,
        animator=operator,
        unavailable_date=today + timedelta(days=3),
        start_time=time(9, 0),
        duration_minutes=120,
        reason="Regression test block",
    )

    _upsert_evaluation(
        db,
        workspace,
        employee=operator,
        evaluator=admin,
        title="Campaign setup accuracy",
        score=9,
        period_label="2026-Q2",
        comment="Seeded KPI for employee evaluation development.",
    )
    _upsert_evaluation(
        db,
        workspace,
        employee=manager,
        evaluator=admin,
        title="Pipeline follow-up discipline",
        score=8,
        period_label="2026-Q2",
        comment="Seeded manager KPI for reporting development.",
    )

    _upsert_notification(
        db,
        workspace,
        user=operator,
        title="Campaign task assigned",
        message="Prepare the Atlas VIP reactivation campaign checklist.",
        target_link="/requests/assigned",
    )
    _upsert_notification(
        db,
        workspace,
        user=admin,
        title="Development workspace ready",
        message="All default CRM modules are enabled for this workspace.",
        target_link="/superadmin",
        is_read=True,
    )

    _upsert_seed_file(db, workspace, uploader=admin, request=campaign_request)
    _upsert_ai_story(db, workspace=workspace, admin=admin, campaign_template=templates["Text Campaign Brief"])

    db.commit()
    db.refresh(workspace)
    return workspace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or reset the all-functionality Test CRM development workspace.")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate the guarded development workspace before seeding.")
    parser.add_argument("--email", default=DEV_WORKSPACE_EMAIL, help="Safety guard for destructive reset.")
    parser.add_argument("--subdomain", default=DEV_WORKSPACE_SUBDOMAIN, help="Safety guard for destructive reset.")
    parser.add_argument("--password", default=DEV_WORKSPACE_PASSWORD, help="Password for seeded development users.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_dev_target(args.email, args.subdomain)

    db = SessionLocal()
    try:
        configure_mappers()
        if args.reset:
            reset_dev_workspace(db, admin_email=args.email, subdomain=args.subdomain)
        workspace = seed_dev_workspace(db, password=args.password)
        summary = development_workspace_summary()
        print(f"OK: seeded development workspace {workspace.name} ({workspace.subdomain_prefix})")
        print(f"Admin login: {DEV_WORKSPACE_EMAIL}")
        print(f"Default password: {args.password}")
        print(f"Enabled modules: {len(summary['enabled_modules'])}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
