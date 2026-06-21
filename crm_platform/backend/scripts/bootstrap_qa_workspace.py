#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
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
from modules.file_storage.models import FileAttachment
from modules.notifications.models import Notification
from modules.registry.models import Client, ClientObject, Company
from modules.reports.models import ReportType
from modules.workflow.models import Department, Request

QA_WORKSPACE_EMAIL = "qa.admin@example.com"
QA_WORKSPACE_PASSWORD = "QaPass123!"
QA_WORKSPACE_NAME = "QA Workspace"
QA_WORKSPACE_SUBDOMAIN = "qa"


def _ensure_qa_target(email: str) -> None:
    if email.strip().lower() != QA_WORKSPACE_EMAIL:
        raise ValueError("Refusing to reset a non-QA workspace")


def reset_qa_workspace(db: Session, *, admin_email: str = QA_WORKSPACE_EMAIL) -> None:
    _ensure_qa_target(admin_email)
    workspace = db.query(Workspace).filter(Workspace.subdomain_prefix == QA_WORKSPACE_SUBDOMAIN).first()
    if workspace is None:
        return

    template_ids = [item.id for item in db.query(FormTemplate.id).filter(FormTemplate.workspace_id == workspace.id)]
    if template_ids:
        db.query(FormRecord).filter(FormRecord.template_id.in_(template_ids)).delete(synchronize_session=False)

    db.query(AIChangeEvent).filter(AIChangeEvent.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AIChangeProposal).filter(AIChangeProposal.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AIBusinessBlueprint).filter(AIBusinessBlueprint.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AIConversationMessage).filter(AIConversationMessage.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(AIConversation).filter(AIConversation.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(FileAttachment).filter(FileAttachment.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(ClientObject).filter(ClientObject.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Client).filter(Client.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Company).filter(Company.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Request).filter(Request.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(FormTemplate).filter(FormTemplate.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(ReportType).filter(ReportType.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(User).filter(User.workspace_id == workspace.id).delete(synchronize_session=False)
    db.query(Department).filter(Department.workspace_id == workspace.id).delete(synchronize_session=False)
    db.delete(workspace)
    db.flush()


def seed_qa_workspace(db: Session, *, password: str = QA_WORKSPACE_PASSWORD) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.subdomain_prefix == QA_WORKSPACE_SUBDOMAIN).first()
    if workspace is None:
        workspace = Workspace(
            name=QA_WORKSPACE_NAME,
            subdomain_prefix=QA_WORKSPACE_SUBDOMAIN,
            admin_email=QA_WORKSPACE_EMAIL,
            admin_full_name="QA Admin",
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
        workspace.name = QA_WORKSPACE_NAME
        workspace.admin_email = QA_WORKSPACE_EMAIL
        workspace.admin_full_name = "QA Admin"
        workspace.status = WorkspaceStatus.ACTIVE.value
        workspace.is_active = True

    department = (
        db.query(Department)
        .filter(Department.workspace_id == workspace.id, Department.name == "QA Operations")
        .first()
    )
    if department is None:
        department = Department(
            name="QA Operations",
            description="Stable department for automated regression journeys",
            workspace_id=workspace.id,
        )
        db.add(department)
        db.flush()

    user = db.query(User).filter(User.email == QA_WORKSPACE_EMAIL).first()
    if user is None:
        user = User(
            full_name="QA Admin",
            email=QA_WORKSPACE_EMAIL,
            hashed_password=pwd_context.hash(password),
            role=UserRole.ADMIN,
            is_active=True,
            workspace_id=workspace.id,
        )
        db.add(user)
    else:
        user.full_name = "QA Admin"
        user.hashed_password = pwd_context.hash(password)
        user.role = UserRole.ADMIN
        user.is_active = True
        user.workspace_id = workspace.id
        user.department_id = None

    db.commit()
    db.refresh(workspace)
    return workspace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or reset the dedicated CRM QA workspace.")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate the QA workspace before seeding.")
    parser.add_argument("--email", default=QA_WORKSPACE_EMAIL, help="Safety guard for destructive reset.")
    parser.add_argument("--password", default=QA_WORKSPACE_PASSWORD, help="Password for the QA admin user.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_qa_target(args.email)

    db = SessionLocal()
    try:
        configure_mappers()
        if args.reset:
            reset_qa_workspace(db, admin_email=args.email)
        workspace = seed_qa_workspace(db, password=args.password)
        print(f"OK: seeded QA workspace {workspace.name} ({workspace.subdomain_prefix})")
        print(f"QA admin: {QA_WORKSPACE_EMAIL}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
