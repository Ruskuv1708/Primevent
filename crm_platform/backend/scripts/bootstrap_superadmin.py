#!/usr/bin/env python3
from __future__ import annotations

import argparse

from core.database_connector import SessionLocal
from modules.workflow.models import Department  # noqa: F401
from modules.access_control.models import User
from modules.access_control.enums import UserRole
from modules.access_control.service import pwd_context
from sqlalchemy.orm import configure_mappers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or reset a CRM superadmin user.")
    parser.add_argument("--email", required=True, help="Superadmin email.")
    parser.add_argument("--password", required=True, help="Superadmin password.")
    parser.add_argument("--full-name", default="Superadmin", help="Full name to store.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    email = args.email.strip().lower()
    password = args.password
    full_name = args.full_name.strip() or "Superadmin"

    db = SessionLocal()
    try:
        configure_mappers()
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.hashed_password = pwd_context.hash(password)
            user.role = UserRole.SUPERADMIN
            user.is_active = True
            user.workspace_id = None
            user.department_id = None
            if full_name:
                user.full_name = full_name
        else:
            user = User(
                full_name=full_name,
                email=email,
                hashed_password=pwd_context.hash(password),
                role=UserRole.SUPERADMIN,
                is_active=True,
                workspace_id=None,
                department_id=None,
            )
            db.add(user)

        db.commit()
        print("OK:", user.id, user.email, user.role)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
