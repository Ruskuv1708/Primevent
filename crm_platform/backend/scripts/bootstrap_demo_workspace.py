#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from sqlalchemy.orm import Session, configure_mappers

from core.database_connector import SessionLocal
from modules.access_control.enums import UserRole, WorkspaceStatus
from modules.access_control.models import User, Workspace
from modules.access_control.service import pwd_context
from modules.ai_architect.models import (
    AIBusinessBlueprint,
    AIChangeEvent,
    AIChangeProposal,
    AIConversation,
    AIConversationMessage,
)
from modules.dynamic_records.models import FormRecord, FormTemplate
from modules.registry.models import Client, ClientObject, Company
from modules.reports.models import ReportType
from modules.workflow.enums import RequestPriority, RequestStatus
from modules.workflow.models import Department, Request

DEMO_WORKSPACE_EMAIL = "demo.admin@example.com"
DEMO_WORKSPACE_PASSWORD = "DemoPass123!"
DEMO_WORKSPACE_NAME = "Demo Workspace"
DEMO_WORKSPACE_SUBDOMAIN = "demo"

DEMO_FORM_RECORD_SPECS = (
    {
        "seed_key": "lead-dilnoza",
        "template": "Lead Intake",
        "entry_data": {
            "customer_name": "Dilnoza Yuldasheva",
            "phone": "+998 90 111 22 33",
            "source": "Referral",
        },
    },
    {
        "seed_key": "purchase-label-printer",
        "template": "Purchase Approval",
        "entry_data": {
            "item": "Label printer",
            "amount": 850,
            "priority": "low",
        },
    },
)

DEMO_AI_HISTORY_STATUSES = {"available", "rolled_back"}


def demo_story_summary() -> dict[str, object]:
    return {
        "form_record_count": len(DEMO_FORM_RECORD_SPECS),
        "ai_history_statuses": set(DEMO_AI_HISTORY_STATUSES),
    }


def _upsert_workspace(db: Session) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.subdomain_prefix == DEMO_WORKSPACE_SUBDOMAIN).first()
    if workspace is None:
        workspace = Workspace(
            name=DEMO_WORKSPACE_NAME,
            subdomain_prefix=DEMO_WORKSPACE_SUBDOMAIN,
            admin_email=DEMO_WORKSPACE_EMAIL,
            admin_full_name="Demo Admin",
            status=WorkspaceStatus.ACTIVE.value,
            is_active=True,
            settings={
                "business_profile": "general",
                "enabled_modules": ["registry", "workflow", "reports", "forms", "files", "ai_architect"],
            },
        )
        db.add(workspace)
        db.flush()
    else:
        workspace.name = DEMO_WORKSPACE_NAME
        workspace.admin_email = DEMO_WORKSPACE_EMAIL
        workspace.admin_full_name = "Demo Admin"
        workspace.status = WorkspaceStatus.ACTIVE.value
        workspace.is_active = True
    return workspace


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
    return user


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


def _upsert_company(db: Session, workspace: Workspace, *, name: str, email: str, phone: str) -> Company:
    company = (
        db.query(Company)
        .filter(Company.workspace_id == workspace.id, Company.name == name)
        .first()
    )
    if company is None:
        company = Company(
            name=name,
            email=email,
            phone=phone,
            address="Tashkent",
            workspace_id=workspace.id,
        )
        db.add(company)
        db.flush()
    else:
        company.email = email
        company.phone = phone
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
        )
        db.add(client)
        db.flush()
    else:
        client.first_name = first_name
        client.last_name = last_name
        client.phone = phone
        client.company_id = company.id if company else None
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
    item = (
        db.query(ClientObject)
        .filter(ClientObject.workspace_id == workspace.id, ClientObject.name == name)
        .first()
    )
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
    template = (
        db.query(FormTemplate)
        .filter(FormTemplate.workspace_id == workspace.id, FormTemplate.name == name)
        .first()
    )
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
    report = (
        db.query(ReportType)
        .filter(ReportType.workspace_id == workspace.id, ReportType.name == name)
        .first()
    )
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


def _upsert_message(
    db: Session,
    conversation: AIConversation,
    *,
    sender: str,
    content: str,
) -> AIConversationMessage:
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
        message = AIConversationMessage(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            sender=sender,
            content=content,
        )
        db.add(message)
        db.flush()
    return message


def _upsert_ai_proposal(
    db: Session,
    *,
    workspace: Workspace,
    blueprint: AIBusinessBlueprint,
    title: str,
    proposal_type: str,
    operation: str,
    description: str,
    rationale: str,
    generated_artifacts: list[dict],
    applied_artifacts: list[dict],
    before_state: dict,
    after_state: dict,
) -> AIChangeProposal:
    proposal = (
        db.query(AIChangeProposal)
        .filter(
            AIChangeProposal.workspace_id == workspace.id,
            AIChangeProposal.blueprint_id == blueprint.id,
            AIChangeProposal.title == title,
        )
        .first()
    )
    if proposal is None:
        proposal = AIChangeProposal(
            workspace_id=workspace.id,
            blueprint_id=blueprint.id,
            proposal_type=proposal_type,
            operation=operation,
            title=title,
            description=description,
            rationale=rationale,
        )
        db.add(proposal)
        db.flush()

    proposal.generated_artifacts = generated_artifacts
    proposal.applied_artifacts = applied_artifacts
    proposal.before_state = before_state
    proposal.after_state = after_state
    proposal.status = "applied"
    return proposal


def _upsert_ai_change_event(
    db: Session,
    *,
    workspace: Workspace,
    conversation: AIConversation,
    proposal: AIChangeProposal,
    actor: User,
    operation: str,
    affected_artifacts: list[dict],
    before_state: dict,
    after_state: dict,
    rollback_status: str,
) -> AIChangeEvent:
    event = (
        db.query(AIChangeEvent)
        .filter(AIChangeEvent.workspace_id == workspace.id, AIChangeEvent.proposal_id == proposal.id)
        .first()
    )
    if event is None:
        event = AIChangeEvent(
            workspace_id=workspace.id,
            proposal_id=proposal.id,
            conversation_id=conversation.id,
            actor_id=actor.id,
            operation=operation,
        )
        db.add(event)
        db.flush()

    event.operation = operation
    event.affected_artifacts = affected_artifacts
    event.before_state = before_state
    event.after_state = after_state
    event.rollback_status = rollback_status
    event.rollback_reason = None
    event.rolled_back_at = datetime.now(timezone.utc) if rollback_status == "rolled_back" else None
    return event


def _upsert_ai_story(
    db: Session,
    *,
    workspace: Workspace,
    admin: User,
    student_intake: FormTemplate,
) -> None:
    conversation = (
        db.query(AIConversation)
        .filter(
            AIConversation.workspace_id == workspace.id,
            AIConversation.title == "CRM Intake Refinement",
        )
        .first()
    )
    if conversation is None:
        conversation = AIConversation(
            workspace_id=workspace.id,
            title="CRM Intake Refinement",
            status="active",
        )
        db.add(conversation)
        db.flush()

    _upsert_message(
        db,
        conversation,
        sender="owner",
        content="We run a CRM workspace with clients, orders, assignments, payments, and reports.",
    )
    _upsert_message(
        db,
        conversation,
        sender="ai",
        content="I drafted a starter CRM structure with intake, reporting, and follow-up flows.",
    )

    blueprint_payload = {
        "business_profile": "general",
        "business_summary": "General CRM workspace with intake, operations, reporting, and follow-up.",
        "entities": ["Clients", "Orders", "Assignments", "Payments", "Reports"],
    }
    blueprint = (
        db.query(AIBusinessBlueprint)
        .filter(AIBusinessBlueprint.conversation_id == conversation.id)
        .first()
    )
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

    before_schema = [
        {"key": "student_name", "label": "Student Name", "type": "text", "required": True},
        {"key": "course_interest", "label": "Course Interest", "type": "text", "required": True},
    ]
    after_schema = [
        *before_schema,
        {"key": "parent_phone", "label": "Parent Phone", "type": "text", "required": True},
    ]
    artifact = {"type": "form", "id": str(student_intake.id), "name": student_intake.name}

    create_proposal = _upsert_ai_proposal(
        db,
        workspace=workspace,
        blueprint=blueprint,
        title="Create student intake form",
        proposal_type="forms",
        operation="create",
        description="Create a starter form for student onboarding.",
        rationale="CRM teams need a consistent way to capture new client details.",
        generated_artifacts=[{"type": "form", "name": student_intake.name}],
        applied_artifacts=[artifact],
        before_state={},
        after_state={"schema_structure": before_schema},
    )
    _upsert_ai_change_event(
        db,
        workspace=workspace,
        conversation=conversation,
        proposal=create_proposal,
        actor=admin,
        operation="create",
        affected_artifacts=[artifact],
        before_state={},
        after_state={"schema_structure": before_schema},
        rollback_status="available",
    )

    update_proposal = _upsert_ai_proposal(
        db,
        workspace=workspace,
        blueprint=blueprint,
        title="Add parent phone to student intake",
        proposal_type="forms",
        operation="update",
        description="Capture a parent contact number during intake.",
        rationale="Primary contacts need to be reachable for follow-up.",
        generated_artifacts=[{"type": "form", "name": student_intake.name}],
        applied_artifacts=[artifact],
        before_state={"schema_structure": before_schema},
        after_state={"schema_structure": after_schema},
    )
    _upsert_ai_change_event(
        db,
        workspace=workspace,
        conversation=conversation,
        proposal=update_proposal,
        actor=admin,
        operation="update",
        affected_artifacts=[artifact],
        before_state={"schema_structure": before_schema},
        after_state={"schema_structure": after_schema},
        rollback_status="rolled_back",
    )


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


def seed_demo_workspace(db: Session) -> Workspace:
    workspace = _upsert_workspace(db)
    sales = _upsert_department(db, workspace, "Sales", "Leads, quotations, and customer follow-up")
    operations = _upsert_department(db, workspace, "Operations", "Order processing and service delivery")
    finance = _upsert_department(db, workspace, "Finance", "Invoices, approvals, and cash control")

    admin = _upsert_user(
        db,
        workspace=workspace,
        email=DEMO_WORKSPACE_EMAIL,
        full_name="Demo Admin",
        password=DEMO_WORKSPACE_PASSWORD,
        role=UserRole.ADMIN,
    )
    sales_manager = _upsert_user(
        db,
        workspace=workspace,
        email="sales.manager@example.com",
        full_name="Malika Karimova",
        password=DEMO_WORKSPACE_PASSWORD,
        role=UserRole.MANAGER,
        department=sales,
    )
    operator = _upsert_user(
        db,
        workspace=workspace,
        email="ops.user@example.com",
        full_name="Aziz Rahimov",
        password=DEMO_WORKSPACE_PASSWORD,
        role=UserRole.USER,
        department=operations,
    )

    silk_road = _upsert_company(
        db,
        workspace,
        name="Silk Road Retail",
        email="office@silkroad-retail.example.com",
        phone="+998 71 200 10 10",
    )
    orion = _upsert_company(
        db,
        workspace,
        name="Orion Services",
        email="hello@orion-services.example.com",
        phone="+998 71 200 20 20",
    )
    dilnoza = _upsert_client(
        db,
        workspace,
        first_name="Dilnoza",
        last_name="Yuldasheva",
        email="dilnoza@example.com",
        phone="+998 90 111 22 33",
        company=silk_road,
    )
    jamshid = _upsert_client(
        db,
        workspace,
        first_name="Jamshid",
        last_name="Nazarov",
        email="jamshid@example.com",
        phone="+998 90 444 55 66",
        company=orion,
    )
    _upsert_client_object(
        db,
        workspace,
        name="Main Store",
        company=silk_road,
        attributes={"segment": "retail", "city": "Tashkent"},
    )
    _upsert_client_object(
        db,
        workspace,
        name="VIP Account",
        client=dilnoza,
        attributes={"tier": "gold"},
    )
    _upsert_client_object(
        db,
        workspace,
        name="Regional Office",
        company=orion,
        client=jamshid,
        attributes={"segment": "services", "city": "Samarkand"},
    )

    lead_intake = _upsert_template(
        db,
        workspace,
        name="Lead Intake",
        schema_structure=[
            {"key": "customer_name", "label": "Customer Name", "type": "text", "required": True},
            {"key": "phone", "label": "Phone", "type": "text", "required": True},
            {"key": "source", "label": "Lead Source", "type": "text", "required": False},
        ],
        request_settings={
            "enabled": True,
            "department_id": str(sales.id),
            "priority": "medium",
            "title_template": "Follow up with {customer_name}",
            "description_template": "Lead came from {source}. Phone: {phone}",
        },
    )
    purchase_approval = _upsert_template(
        db,
        workspace,
        name="Purchase Approval",
        schema_structure=[
            {"key": "item", "label": "Item", "type": "text", "required": True},
            {"key": "amount", "label": "Amount", "type": "number", "required": True},
            {"key": "priority", "label": "Priority", "type": "priority_select", "required": False},
        ],
        request_settings={
            "enabled": True,
            "department_id": str(finance.id),
            "priority": "medium",
            "title_template": "Purchase approval for {item}",
            "description_template": "Requested amount: {amount}",
        },
    )
    student_intake = _upsert_template(
        db,
        workspace,
        name="Student Intake",
        schema_structure=[
            {"key": "student_name", "label": "Student Name", "type": "text", "required": True},
            {"key": "course_interest", "label": "Course Interest", "type": "text", "required": True},
        ],
    )
    student_intake.meta_data = {
        **(student_intake.meta_data or {}),
        "ai_architect": {
            "proposal_title": "Create student intake form",
            "source": "demo_seed",
        },
    }

    _upsert_report_type(
        db,
        workspace,
        name="Open Requests",
        description="Operational queue grouped by owner and priority",
        source="requests",
        columns=[
            {"key": "title", "label": "Title"},
            {"key": "status", "label": "Status"},
            {"key": "priority", "label": "Priority"},
            {"key": "assignee_name", "label": "Assigned To"},
        ],
    )
    _upsert_report_type(
        db,
        workspace,
        name="Customer Directory",
        description="Presentation-ready customer list",
        source="clients",
        columns=[
            {"key": "full_name", "label": "Customer"},
            {"key": "email", "label": "Email"},
            {"key": "phone", "label": "Phone"},
            {"key": "company_name", "label": "Company"},
        ],
    )

    lead_request = _upsert_request(
        db,
        workspace,
        title="Follow up with Dilnoza Yuldasheva",
        description="Lead asked for a retail CRM demo next week.",
        department=sales,
        creator=admin,
        assignee=sales_manager,
        status=RequestStatus.ASSIGNED,
        priority=RequestPriority.HIGH,
    )
    _upsert_request(
        db,
        workspace,
        title="Prepare Orion Clinic onboarding",
        description="Collect departments, staff roles, and first reports.",
        department=operations,
        creator=admin,
        assignee=operator,
        status=RequestStatus.PENDING,
        priority=RequestPriority.MEDIUM,
    )
    purchase_request = _upsert_request(
        db,
        workspace,
        title="Approve label printer purchase",
        description="Needed for the warehouse receiving station.",
        department=finance,
        creator=admin,
        assignee=None,
        status=RequestStatus.NEW,
        priority=RequestPriority.LOW,
    )

    _upsert_form_record(
        db,
        lead_intake,
        seed_key=DEMO_FORM_RECORD_SPECS[0]["seed_key"],
        entry_data=DEMO_FORM_RECORD_SPECS[0]["entry_data"],
        request=lead_request,
    )
    _upsert_form_record(
        db,
        purchase_approval,
        seed_key=DEMO_FORM_RECORD_SPECS[1]["seed_key"],
        entry_data=DEMO_FORM_RECORD_SPECS[1]["entry_data"],
        request=purchase_request,
    )
    _upsert_ai_story(
        db,
        workspace=workspace,
        admin=admin,
        student_intake=student_intake,
    )

    db.commit()
    db.refresh(workspace)
    return workspace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or refresh the presentable CRM demo workspace.")
    parser.add_argument("--password", default=DEMO_WORKSPACE_PASSWORD, help="Password for seeded demo users.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global DEMO_WORKSPACE_PASSWORD
    DEMO_WORKSPACE_PASSWORD = args.password

    db = SessionLocal()
    try:
        configure_mappers()
        workspace = seed_demo_workspace(db)
        print(f"OK: seeded demo workspace {workspace.name} ({workspace.subdomain_prefix})")
        print(f"Demo admin: {DEMO_WORKSPACE_EMAIL}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
