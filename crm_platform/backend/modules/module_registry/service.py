from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from modules.module_registry.definitions import (
    DEFAULT_ENABLED_MODULE_IDS,
    MODULE_DEFINITIONS,
    MODULE_MANIFESTS,
    MODULE_ORDER,
    MODULE_PRESET_DEFAULTS,
    ModuleDefinition,
    ModuleManifest,
)

if TYPE_CHECKING:
    from modules.access_control.models import Workspace


class ModuleService:
    SETTINGS_ENABLED_KEY = "enabled_modules"
    SETTINGS_PRESET_KEY = "module_preset"
    LEGACY_SETTINGS_PROFILE_KEY = "business_profile"
    DEFAULT_PRESET = "functional"

    @staticmethod
    def list_module_definitions() -> list[ModuleDefinition]:
        return [MODULE_DEFINITIONS[module_id] for module_id in MODULE_ORDER]

    @staticmethod
    def list_module_manifests(enabled_module_ids: list[str] | tuple[str, ...] | None = None) -> list[ModuleManifest]:
        if enabled_module_ids is None:
            available_ids = set(MODULE_MANIFESTS)
        else:
            available_ids = set(ModuleService.normalize_enabled_modules(enabled_module_ids))

        return [
            MODULE_MANIFESTS[module_id]
            for module_id in MODULE_ORDER
            if module_id in available_ids and module_id in MODULE_MANIFESTS
        ]

    @staticmethod
    def get_default_enabled_modules(module_preset: str = DEFAULT_PRESET) -> list[str]:
        preset = module_preset if module_preset in MODULE_PRESET_DEFAULTS else ModuleService.DEFAULT_PRESET
        return ModuleService.normalize_enabled_modules(MODULE_PRESET_DEFAULTS[preset])

    @staticmethod
    def normalize_enabled_modules(module_ids: list[str] | tuple[str, ...] | None) -> list[str]:
        requested = set()
        for module_id in module_ids or ():
            normalized = str(module_id or "").strip()
            if normalized in MODULE_DEFINITIONS:
                requested.add(normalized)

        return [module_id for module_id in MODULE_ORDER if module_id in requested]

    @staticmethod
    def build_workspace_settings(
        existing_settings: dict | None,
        module_preset: str | None = None,
        enabled_modules: list[str] | tuple[str, ...] | None = None,
    ) -> dict:
        next_settings = dict(existing_settings or {})
        requested_preset = (
            module_preset
            or next_settings.get(ModuleService.SETTINGS_PRESET_KEY)
            or ModuleService.DEFAULT_PRESET
        )
        preset = requested_preset if requested_preset in MODULE_PRESET_DEFAULTS else ModuleService.DEFAULT_PRESET

        if enabled_modules is None:
            raw_enabled = next_settings.get(ModuleService.SETTINGS_ENABLED_KEY)
            if raw_enabled is None or module_preset:
                enabled = ModuleService.get_default_enabled_modules(preset)
            else:
                enabled = ModuleService.normalize_enabled_modules(raw_enabled)
        else:
            enabled = ModuleService.normalize_enabled_modules(enabled_modules)

        next_settings.pop(ModuleService.LEGACY_SETTINGS_PROFILE_KEY, None)
        next_settings[ModuleService.SETTINGS_PRESET_KEY] = preset
        next_settings[ModuleService.SETTINGS_ENABLED_KEY] = enabled
        return next_settings

    @staticmethod
    def get_workspace_module_settings(workspace: "Workspace | object | None") -> dict:
        settings = getattr(workspace, "settings", None) if workspace is not None else None
        return ModuleService.build_workspace_settings(settings)

    @staticmethod
    def serialize_module_definition(definition: ModuleDefinition) -> dict:
        return {
            "id": definition.id,
            "label": definition.label,
            "category": definition.category,
            "description": definition.description,
            "route_path": definition.route_path,
            "summary": definition.summary,
            "capabilities": list(definition.capabilities),
            "dependencies": list(definition.dependencies),
            "synergies": [
                {
                    "module_id": synergy.module_id,
                    "label": synergy.label,
                    "description": synergy.description,
                }
                for synergy in definition.synergies
            ],
            "default_enabled": definition.default_enabled,
        }

    @staticmethod
    def serialize_module_manifest(manifest: ModuleManifest) -> dict:
        definition = MODULE_DEFINITIONS[manifest.module_id]
        return {
            "module_id": manifest.module_id,
            "label": definition.label,
            "summary": definition.summary,
            "templates": [
                {
                    "id": template.id,
                    "label": template.label,
                    "template_type": template.template_type,
                    "description": template.description,
                    "fields": list(template.fields),
                    "stages": list(template.stages),
                }
                for template in manifest.templates
            ],
        }

    @staticmethod
    def serialize_workspace_modules(workspace: "Workspace | object | None") -> dict:
        return ModuleService.get_workspace_module_settings(workspace)

    @staticmethod
    def update_workspace_modules(
        db: Session,
        workspace_id: UUID,
        enabled_modules: list[str] | None,
        module_preset: str | None = None,
    ) -> "Workspace":
        from modules.access_control.models import Workspace

        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        workspace.settings = ModuleService.build_workspace_settings(
            workspace.settings,
            module_preset=module_preset,
            enabled_modules=enabled_modules,
        )
        db.commit()
        db.refresh(workspace)
        from modules.module_registry.install_service import ModuleInstallService

        ModuleInstallService.install_enabled_modules(
            db,
            workspace.id,
            workspace.settings.get(ModuleService.SETTINGS_ENABLED_KEY) if isinstance(workspace.settings, dict) else None,
        )
        return workspace
