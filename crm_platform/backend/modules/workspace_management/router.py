from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone
import logging
import os
from typing import List, Optional
from pydantic import BaseModel
from core.database_connector import get_db
from modules.access_control.security import get_current_user
from modules.access_control.models import User, SystemSetting
from modules.access_control.enums import UserRole
from modules.access_control.permissions import PermissionService
from core.config import settings
from modules.workspace_management.schemas import (
    WorkspaceCreateSchema,
    WorkspaceUpdateSchema,
    WorkspaceResponseSchema,
)
from modules.workspace_management.service import WorkspaceService

# Настройка логгирования
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/superadmin",
    tags=["Workspace Management (Superadmin Only)"]
)


AI_SETTINGS_KEY = "ai_settings"
SUPPORTED_AI_PROVIDERS = {"deterministic", "gemini", "grok", "groq"}
LIVE_AI_PROVIDERS = {"gemini", "grok", "groq"}


class AISettingsUpdateSchema(BaseModel):
    provider: str = "deterministic"
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class AISettingsResponseSchema(BaseModel):
    provider: str
    model: str
    base_url: str
    api_key_configured: bool
    api_key_preview: Optional[str] = None


def _normalize_ai_provider(provider: Optional[str]) -> str:
    normalized = (provider or "deterministic").strip().lower() or "deterministic"
    if normalized not in SUPPORTED_AI_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported AI provider: {normalized}")
    return normalized


def _preview_api_key(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    return f"••••{api_key[-4:]}"


def _serialize_ai_settings(value: Optional[dict]) -> dict:
    data = value if isinstance(value, dict) else {}
    api_key = data.get("api_key") or ""
    provider = data.get("provider") or "deterministic"
    if provider not in SUPPORTED_AI_PROVIDERS:
        provider = "deterministic"
    return {
        "provider": provider,
        "model": data.get("model") or "",
        "base_url": data.get("base_url") or "",
        "api_key_configured": bool(api_key),
        "api_key_preview": _preview_api_key(api_key),
    }


def _build_ai_settings_value(data: AISettingsUpdateSchema, existing: dict) -> dict:
    provider = _normalize_ai_provider(data.provider)
    api_key = existing.get("api_key") or ""
    if data.api_key is not None:
        api_key = data.api_key.strip()

    next_value = {
        "provider": provider,
        "model": (data.model or "").strip(),
        "base_url": (data.base_url or "").strip(),
        "api_key": api_key,
    }

    if provider in LIVE_AI_PROVIDERS and (not next_value["model"] or not next_value["api_key"]):
        raise HTTPException(status_code=400, detail="Model and API key are required for live AI providers")

    return next_value


def apply_ai_settings_to_runtime(value: Optional[dict]) -> None:
    data = value if isinstance(value, dict) else {}
    runtime_value = {
        "AI_ARCHITECT_PROVIDER": _normalize_ai_provider(data.get("provider")),
        "AI_ARCHITECT_MODEL": (data.get("model") or "").strip(),
        "AI_ARCHITECT_API_KEY": (data.get("api_key") or "").strip(),
        "AI_ARCHITECT_BASE_URL": (data.get("base_url") or "").strip(),
    }

    settings.AI_ARCHITECT_PROVIDER = runtime_value["AI_ARCHITECT_PROVIDER"]
    settings.AI_ARCHITECT_MODEL = runtime_value["AI_ARCHITECT_MODEL"]
    settings.AI_ARCHITECT_API_KEY = runtime_value["AI_ARCHITECT_API_KEY"]
    settings.AI_ARCHITECT_BASE_URL = runtime_value["AI_ARCHITECT_BASE_URL"]

    for key, value in runtime_value.items():
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)

    from modules.ai_architect.service import AIArchitectService

    AIArchitectService.refresh_provider()


def apply_saved_ai_settings(db: Session) -> bool:
    setting = db.query(SystemSetting).filter(SystemSetting.key == AI_SETTINGS_KEY).first()
    if not setting:
        return False
    apply_ai_settings_to_runtime(setting.value)
    return True


def update_ai_settings(
    data: AISettingsUpdateSchema,
    db: Session,
    current_user,
) -> dict:
    PermissionService.require_role(current_user, UserRole.SUPERADMIN)

    setting = db.query(SystemSetting).filter(SystemSetting.key == AI_SETTINGS_KEY).first()
    existing = setting.value if setting and isinstance(setting.value, dict) else {}
    next_value = _build_ai_settings_value(data, existing)

    if setting is None:
        setting = SystemSetting(key=AI_SETTINGS_KEY, value=next_value)
        db.add(setting)
    else:
        setting.value = next_value

    db.commit()
    db.refresh(setting)
    apply_ai_settings_to_runtime(setting.value)
    return _serialize_ai_settings(setting.value)

# ========================================
# WORKSPACE MANAGEMENT ENDPOINTS
# ========================================

@router.get("/ai-settings", response_model=AISettingsResponseSchema)
def get_ai_settings(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_role(current_user, UserRole.SUPERADMIN)
    setting = db.query(SystemSetting).filter(SystemSetting.key == AI_SETTINGS_KEY).first()
    return _serialize_ai_settings(setting.value if setting else None)


@router.put("/ai-settings", response_model=AISettingsResponseSchema)
def save_ai_settings(
    data: AISettingsUpdateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return update_ai_settings(data, db, current_user)

@router.post("/workspaces", response_model=dict)
async def create_workspace(
    data: WorkspaceCreateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Создание новой рабочей области (только для суперадмина)
    """
    PermissionService.require_role(current_user, UserRole.SUPERADMIN)
    try:
        result = WorkspaceService.create_workspace(db, data)
        
        logger.info(
            f"✅ AUDIT: Рабочая область создана пользователем {current_user.email}\n"
            f"   Название: {data.workspace_name}\n"
            f"   Субдомен: {data.subdomain_prefix}\n"
            f"   Время: {datetime.now(timezone.utc)}"
        )
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка при создании рабочей области: {e}")
        raise

@router.get("/workspaces", response_model=List[WorkspaceResponseSchema])
async def list_workspaces(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    skip: int = 0,
    limit: int = settings.DEFAULT_PAGE_SIZE
):
    """
    Список всех рабочих областей (только для суперадмина)
    """
    PermissionService.require_role(current_user, UserRole.SUPERADMIN)
    logger.info(f"✅ Получение списка рабочих областей пользователем {current_user.email}")
    limit = max(1, min(limit, settings.MAX_PAGE_SIZE))
    skip = max(skip, 0)
    return WorkspaceService.list_workspaces(db, skip=skip, limit=limit)

@router.get("/workspaces/{workspace_id}", response_model=dict)
async def get_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Детали конкретной рабочей области
    """
    from modules.access_control.models import Workspace
    if current_user.role != UserRole.SUPERADMIN and current_user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Нет доступа к другим рабочим областям")
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Рабочая область не найдена")
    return {
        "id": str(workspace.id),
        "name": workspace.name,
        "is_active": workspace.is_active,
        "created_at": workspace.created_at
    }

@router.post("/workspaces/{workspace_id}/suspend", deprecated=True)
async def suspend_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Приостанавливает рабочую область (только для суперадмина)
    Deprecated: use PUT /superadmin/workspaces/{workspace_id}/suspend
    """
    PermissionService.require_role(current_user, UserRole.SUPERADMIN)
    logger.warning(
        f"🚨 CRITICAL: Приостановка рабочей области пользователем {current_user.email}\n"
        f"   Идентификатор рабочей области: {workspace_id}\n"
        f"   Время: {datetime.now(timezone.utc)}"
    )
    return WorkspaceService.suspend_workspace(db, workspace_id)

# ======================================================
# Новый роут для получения списка рабочих областей с количеством пользователей
# ======================================================

@router.get("/workspaces-with-user-count", response_model=List[dict])
def get_all_workspaces_with_user_count(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    skip: int = 0,
    limit: int = settings.DEFAULT_PAGE_SIZE
):
    """
    Получить все рабочие области с указанием количества пользователей (только для суперадмина)
    """
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Только суперадмин может просматривать все рабочие области")
    from modules.access_control.models import Workspace
    from sqlalchemy import func
    limit = max(1, min(limit, settings.MAX_PAGE_SIZE))
    skip = max(skip, 0)
    workspaces = db.query(
        Workspace.id,
        Workspace.name,
        Workspace.is_active,
        func.count(User.id).label('user_count')
    ).outerjoin(User).group_by(Workspace.id).offset(skip).limit(limit).all()
    return [
        {
            "id": str(ws.id),
            "name": ws.name,
            "is_active": ws.is_active,
            "user_count": ws.user_count
        }
        for ws in workspaces
    ]

@router.put("/workspaces/{workspace_id}/suspend")
def suspend_workspace_put(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Приостановка рабочей области (только для суперадмина)
    """
    PermissionService.require_role(current_user, UserRole.SUPERADMIN)
    return WorkspaceService.suspend_workspace(db, workspace_id)

@router.put("/workspaces/{workspace_id}/activate")
def activate_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Активация рабочей области (только для суперадмина)
    """
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Только суперадмин может активировать рабочую область")
    return WorkspaceService.activate_workspace(db, workspace_id)

@router.put("/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Обновляет детали рабочей области (только для суперадмина)
    """
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Только суперадмин может обновить рабочую область")
    workspace = WorkspaceService.update_workspace(
        db,
        workspace_id,
        workspace_name=data.workspace_name,
        status=data.status,
        settings=data.settings
    )
    return {"message": f"Рабочая область '{workspace.name}' успешно обновлена"}
