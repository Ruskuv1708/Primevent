from __future__ import annotations

from datetime import date, time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database_connector import get_db
from core.workspace_resolver import resolve_workspace_id
from modules.access_control.enums import UserRole
from modules.access_control.models import Workspace
from modules.access_control.permissions import PermissionService
from modules.access_control.security import get_current_user
from modules.animator_schedule.schemas import (
    AnimatorBookingCreate,
    AnimatorBookingUpdate,
    AnimatorUnavailabilityCreate,
    AnimatorUnavailabilityUpdate,
)
from modules.animator_schedule.service import AnimatorScheduleService
from modules.module_registry.service import ModuleService

router = APIRouter(prefix="/animator-schedule", tags=["Animator Schedule"])


def _resolve_animator_workspace(db: Session, current_user, workspace_id: Optional[UUID]) -> UUID:
    target_workspace_id = resolve_workspace_id(current_user, workspace_id)
    workspace = db.query(Workspace).filter(Workspace.id == target_workspace_id).first()
    settings = ModuleService.serialize_workspace_modules(workspace)
    if "animator_schedule" not in settings["enabled_modules"]:
        raise HTTPException(status_code=403, detail="Animator schedule module is not enabled for this workspace")
    return target_workspace_id


def _ensure_unavailability_target_allowed(current_user, animator_id: UUID) -> None:
    if str(getattr(current_user, "id", "")) == str(animator_id):
        return
    PermissionService.require_role(current_user, UserRole.MANAGER)


def _can_manage_unavailability(current_user) -> bool:
    role_hierarchy = {
        UserRole.SUPERADMIN: 6,
        UserRole.SYSTEM_ADMIN: 5,
        UserRole.ADMIN: 4,
        UserRole.MANAGER: 3,
        UserRole.USER: 2,
        UserRole.VIEWER: 1,
    }
    role = getattr(current_user, "role", UserRole.VIEWER)
    if isinstance(role, str):
        try:
            role = UserRole(role)
        except ValueError:
            return False
    return role_hierarchy.get(role, 0) >= role_hierarchy[UserRole.MANAGER]


@router.get("/animators")
def list_animators(
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    return AnimatorScheduleService.list_animators(db, target_workspace_id)


@router.get("/animators/availability")
def list_animator_availability(
    event_date: date,
    start_time: time,
    duration_minutes: int = Query(ge=15, le=720),
    exclude_booking_id: Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    return AnimatorScheduleService.list_animator_availability(
        db,
        target_workspace_id,
        event_date,
        start_time,
        duration_minutes,
        exclude_booking_id,
    )


@router.get("/bookings")
def list_bookings(
    workspace_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    return AnimatorScheduleService.list_bookings(db, target_workspace_id, date_from, date_to)


@router.get("/unavailability")
def list_unavailability(
    workspace_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    animator_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    if animator_id:
        _ensure_unavailability_target_allowed(current_user, animator_id)
        target_animator_id = animator_id
    elif _can_manage_unavailability(current_user):
        target_animator_id = None
    else:
        target_animator_id = current_user.id
    return AnimatorScheduleService.list_unavailability(
        db,
        target_workspace_id,
        date_from,
        date_to,
        target_animator_id,
    )


@router.post("/unavailability")
def create_unavailability(
    data: AnimatorUnavailabilityCreate,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.USER)
    _ensure_unavailability_target_allowed(current_user, data.animator_id)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    return AnimatorScheduleService.create_unavailability(db, target_workspace_id, data)


@router.patch("/unavailability/{unavailability_id}")
def update_unavailability(
    unavailability_id: UUID,
    data: AnimatorUnavailabilityUpdate,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.USER)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    existing = AnimatorScheduleService._get_unavailability(db, target_workspace_id, unavailability_id)
    _ensure_unavailability_target_allowed(current_user, data.animator_id or existing.animator_id)
    _ensure_unavailability_target_allowed(current_user, existing.animator_id)
    return AnimatorScheduleService.update_unavailability(db, target_workspace_id, unavailability_id, data)


@router.delete("/unavailability/{unavailability_id}")
def delete_unavailability(
    unavailability_id: UUID,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.USER)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    existing = AnimatorScheduleService._get_unavailability(db, target_workspace_id, unavailability_id)
    _ensure_unavailability_target_allowed(current_user, existing.animator_id)
    return AnimatorScheduleService.delete_unavailability(db, target_workspace_id, unavailability_id)


@router.post("/bookings")
def create_booking(
    data: AnimatorBookingCreate,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    return AnimatorScheduleService.create_booking(db, target_workspace_id, data)


@router.patch("/bookings/{booking_id}")
def update_booking(
    booking_id: UUID,
    data: AnimatorBookingUpdate,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    return AnimatorScheduleService.update_booking(db, target_workspace_id, booking_id, data)


@router.delete("/bookings/{booking_id}")
def delete_booking(
    booking_id: UUID,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    target_workspace_id = _resolve_animator_workspace(db, current_user, workspace_id)
    return AnimatorScheduleService.delete_booking(db, target_workspace_id, booking_id)
