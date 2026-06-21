from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database_connector import get_db
from core.workspace_resolver import resolve_workspace_id
from modules.access_control.enums import UserRole
from modules.access_control.models import Workspace
from modules.access_control.permissions import PermissionService
from modules.access_control.security import get_current_user
from modules.employee_evaluations.schemas import EmployeeEvaluationCreate, EmployeeEvaluationUpdate
from modules.employee_evaluations.service import EmployeeEvaluationService
from modules.module_registry.service import ModuleService

router = APIRouter(prefix="/employee-evaluations", tags=["Employee Evaluations"])


def _resolve_evaluation_workspace(db: Session, current_user, workspace_id: Optional[UUID]) -> UUID:
    target_workspace_id = resolve_workspace_id(current_user, workspace_id)
    workspace = db.query(Workspace).filter(Workspace.id == target_workspace_id).first()
    settings = ModuleService.serialize_workspace_modules(workspace)
    if "employee_evaluations" not in settings["enabled_modules"]:
        raise HTTPException(status_code=403, detail="Employee evaluations module is not enabled for this workspace")
    return target_workspace_id


def _can_manage_evaluations(current_user) -> bool:
    try:
        PermissionService.require_role(current_user, UserRole.ADMIN)
        return True
    except HTTPException:
        return False


@router.get("/employees")
def list_employee_summaries(
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    target_workspace_id = _resolve_evaluation_workspace(db, current_user, workspace_id)
    summaries = EmployeeEvaluationService.list_employee_summaries(db, target_workspace_id)
    if _can_manage_evaluations(current_user):
        return summaries
    return [item for item in summaries if item["id"] == str(current_user.id)]


@router.get("/stats")
def get_team_stats(
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    target_workspace_id = _resolve_evaluation_workspace(db, current_user, workspace_id)
    return EmployeeEvaluationService.get_team_stats(db, target_workspace_id)


@router.get("")
def list_evaluations(
    employee_id: Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    target_workspace_id = _resolve_evaluation_workspace(db, current_user, workspace_id)
    if _can_manage_evaluations(current_user):
        target_employee_id = employee_id
    else:
        if employee_id and str(employee_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Employees can only view their own evaluations")
        target_employee_id = current_user.id
    return EmployeeEvaluationService.list_evaluations(db, target_workspace_id, target_employee_id)


@router.post("")
def create_evaluation(
    data: EmployeeEvaluationCreate,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    target_workspace_id = _resolve_evaluation_workspace(db, current_user, workspace_id)
    return EmployeeEvaluationService.create_evaluation(db, target_workspace_id, current_user.id, data)


@router.patch("/{evaluation_id}")
def update_evaluation(
    evaluation_id: UUID,
    data: EmployeeEvaluationUpdate,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    target_workspace_id = _resolve_evaluation_workspace(db, current_user, workspace_id)
    return EmployeeEvaluationService.update_evaluation(db, target_workspace_id, evaluation_id, data)


@router.delete("/{evaluation_id}")
def delete_evaluation(
    evaluation_id: UUID,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    target_workspace_id = _resolve_evaluation_workspace(db, current_user, workspace_id)
    return EmployeeEvaluationService.delete_evaluation(db, target_workspace_id, evaluation_id)
