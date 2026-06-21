#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
import os

# Add current directory to path to resolve 'core' and 'modules'
sys.path.append(os.getcwd())

from core.database_connector import SessionLocal
from modules.access_control.models import User, Workspace
from modules.access_control.enums import UserRole, WorkspaceStatus
from modules.access_control.service import pwd_context
from modules.workflow.models import Department  # noqa: F401
from sqlalchemy.orm import configure_mappers
from datetime import datetime, timezone

def main() -> int:
    parser = argparse.ArgumentParser(description="Create a workspace and superadmin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", default=os.getenv("CRM_BOOTSTRAP_PASSWORD"))
    parser.add_argument("--workspace-name", default="Main Workspace")
    parser.add_argument("--subdomain", default="main")
    args = parser.parse_args()
    if not args.password:
        parser.error("password is required via --password or CRM_BOOTSTRAP_PASSWORD")

    db = SessionLocal()
    try:
        configure_mappers()
        
        # 1. Create Workspace if not exists
        workspace = db.query(Workspace).filter(Workspace.subdomain_prefix == args.subdomain).first()
        if not workspace:
            workspace = Workspace(
                name=args.workspace_name,
                subdomain_prefix=args.subdomain,
                admin_email=args.email,
                admin_full_name="Superadmin",
                status=WorkspaceStatus.ACTIVE.value,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                activated_at=datetime.now(timezone.utc),
                settings={}
            )
            db.add(workspace)
            db.flush()
            print(f"Created workspace: {workspace.name} ({workspace.subdomain_prefix})")
        else:
            print(f"Workspace {args.subdomain} already exists")

        # 2. Create/Update Superadmin
        user = db.query(User).filter(User.email == args.email).first()
        if user:
            user.hashed_password = pwd_context.hash(args.password)
            user.role = UserRole.SUPERADMIN
            user.workspace_id = workspace.id
            user.is_active = True
            print(f"Updated user: {user.email}")
        else:
            user = User(
                full_name="Superadmin",
                email=args.email,
                hashed_password=pwd_context.hash(args.password),
                role=UserRole.SUPERADMIN,
                is_active=True,
                workspace_id=workspace.id
            )
            db.add(user)
            print(f"Created user: {user.email}")
        
        db.commit()
        print(f"OK: {user.id} {user.email} {user.role} in workspace {workspace.subdomain_prefix}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
