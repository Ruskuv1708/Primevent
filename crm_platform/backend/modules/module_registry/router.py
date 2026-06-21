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
from modules.module_registry.schemas import (
    ModuleDefinitionResponse,
    ModuleInstallResultResponse,
    ModuleInstallStatusResponse,
    ModuleManifestResponse,
    WorkspaceModuleSettingsResponse,
    WorkspaceModuleSettingsUpdate,
)
from modules.module_registry.install_service import ModuleInstallService
from modules.module_registry.service import ModuleService

router = APIRouter(tags=["Module Registry"])


def _resolve_enabled_workspace_module(
    db: Session,
    current_user,
    workspace_id: Optional[UUID],
    module_id: str,
) -> UUID:
    target_workspace_id = resolve_workspace_id(current_user, workspace_id)
    workspace = db.query(Workspace).filter(Workspace.id == target_workspace_id).first()
    settings = ModuleService.serialize_workspace_modules(workspace)
    if module_id not in settings["enabled_modules"]:
        raise HTTPException(status_code=403, detail="Module is not enabled for this workspace")
    return target_workspace_id


@router.get("/modules/definitions", response_model=list[ModuleDefinitionResponse])
def list_module_definitions(current_user=Depends(get_current_user)):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    return [
        ModuleService.serialize_module_definition(definition)
        for definition in ModuleService.list_module_definitions()
    ]


@router.get("/modules/current", response_model=WorkspaceModuleSettingsResponse)
def get_current_workspace_modules(
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role == UserRole.SUPERADMIN and current_user.workspace_id is None and workspace_id is None:
        return ModuleService.serialize_workspace_modules(None)

    target_workspace_id = resolve_workspace_id(current_user, workspace_id)
    workspace = db.query(Workspace).filter(Workspace.id == target_workspace_id).first()
    return ModuleService.serialize_workspace_modules(workspace)


@router.get("/modules/manifests/current", response_model=list[ModuleManifestResponse])
def get_current_workspace_module_manifests(
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    if current_user.role == UserRole.SUPERADMIN and current_user.workspace_id is None and workspace_id is None:
        settings = ModuleService.serialize_workspace_modules(None)
    else:
        target_workspace_id = resolve_workspace_id(current_user, workspace_id)
        workspace = db.query(Workspace).filter(Workspace.id == target_workspace_id).first()
        settings = ModuleService.serialize_workspace_modules(workspace)

    return [
        ModuleService.serialize_module_manifest(manifest)
        for manifest in ModuleService.list_module_manifests(settings["enabled_modules"])
    ]


@router.get("/modules/{module_id}/install-status", response_model=ModuleInstallStatusResponse)
def get_module_install_status(
    module_id: str,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.VIEWER)
    target_workspace_id = _resolve_enabled_workspace_module(db, current_user, workspace_id, module_id)
    return ModuleInstallService.get_install_status(db, target_workspace_id, module_id)


@router.post("/modules/{module_id}/install", response_model=ModuleInstallResultResponse)
def install_module_starter_kit(
    module_id: str,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    target_workspace_id = _resolve_enabled_workspace_module(db, current_user, workspace_id, module_id)
    return ModuleInstallService.install_module(db, target_workspace_id, module_id)


@router.put(
    "/superadmin/workspaces/{workspace_id}/modules",
    response_model=WorkspaceModuleSettingsResponse,
)
def update_workspace_modules(
    workspace_id: UUID,
    data: WorkspaceModuleSettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.SUPERADMIN)
    workspace = ModuleService.update_workspace_modules(
        db,
        workspace_id=workspace_id,
        module_preset=data.module_preset,
        enabled_modules=data.enabled_modules,
    )
    return ModuleService.serialize_workspace_modules(workspace)
