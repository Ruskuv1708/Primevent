from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from modules.module_registry.definitions import MODULE_DEFINITIONS, ModuleManifest, ModuleTemplateDefinition
from modules.module_registry.service import ModuleService


class ModuleInstallService:
    PLUGIN_META_KEY = "module_plugin"

    @staticmethod
    def _field_key(label: str, fallback: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", label.strip().lower()).strip("_")
        return (normalized or fallback)[:120]

    @staticmethod
    def _field_type(label: str) -> str:
        normalized = label.strip().lower()
        date_words = ("appointment", "birth", "date", "deadline", "expiry", "renewal", "time", "visit")
        if any(word in normalized for word in date_words):
            return "date"
        number_words = (
            "amount",
            "allowance",
            "bonus",
            "cost",
            "count",
            "days",
            "deduction",
            "margin",
            "price",
            "quantity",
            "rate",
            "revenue",
            "score",
            "slots",
            "stock",
            "students",
            "total",
            "value",
        )
        if any(word in normalized for word in number_words):
            return "number"
        return "text"

    @staticmethod
    def build_form_schema(template: ModuleTemplateDefinition) -> list[dict]:
        schema: list[dict] = []
        used_keys: set[str] = set()
        for index, field_label in enumerate(template.fields, start=1):
            base_key = ModuleInstallService._field_key(field_label, f"field_{index}")
            key = base_key
            suffix = 2
            while key in used_keys:
                key = f"{base_key}_{suffix}"[:120]
                suffix += 1
            used_keys.add(key)
            schema.append(
                {
                    "key": key,
                    "label": field_label,
                    "type": ModuleInstallService._field_type(field_label),
                    "required": False,
                }
            )
        return schema

    @staticmethod
    def build_report_columns(template: ModuleTemplateDefinition) -> list[dict]:
        return [
            {
                "key": field["key"],
                "label": field["label"],
                "formula": None,
                "format": None,
            }
            for field in ModuleInstallService.build_form_schema(template)
        ]

    @staticmethod
    def _plugin_meta(module_id: str, template: ModuleTemplateDefinition) -> dict:
        return {
            ModuleInstallService.PLUGIN_META_KEY: {
                "module_id": module_id,
                "template_id": template.id,
                "template_type": template.template_type,
                "label": template.label,
            }
        }

    @staticmethod
    def _installed_template_ids(items: list[object], module_id: str) -> set[str]:
        installed: set[str] = set()
        for item in items:
            meta_data = getattr(item, "meta_data", None) or {}
            plugin_meta = meta_data.get(ModuleInstallService.PLUGIN_META_KEY) if isinstance(meta_data, dict) else None
            if not isinstance(plugin_meta, dict):
                continue
            template_id = plugin_meta.get("template_id")
            if isinstance(template_id, str) and template_id:
                plugin_module_id = plugin_meta.get("module_id")
                if plugin_module_id and plugin_module_id != module_id:
                    continue
                if not plugin_module_id and not template_id.startswith(f"{module_id}."):
                    continue
                installed.add(template_id)
        return installed

    @staticmethod
    def build_install_status(
        manifest: ModuleManifest,
        installed_forms: list[object],
        installed_reports: list[object],
    ) -> dict:
        template_ids = [template.id for template in manifest.templates]
        installed_ids = ModuleInstallService._installed_template_ids(installed_forms, manifest.module_id)
        installed_ids.update(ModuleInstallService._installed_template_ids(installed_reports, manifest.module_id))
        known_installed_ids = [template_id for template_id in template_ids if template_id in installed_ids]
        missing_ids = [template_id for template_id in template_ids if template_id not in installed_ids]
        definition = MODULE_DEFINITIONS[manifest.module_id]
        return {
            "module_id": manifest.module_id,
            "label": definition.label,
            "total_templates": len(template_ids),
            "installed_count": len(known_installed_ids),
            "is_installed": len(missing_ids) == 0,
            "installed_template_ids": known_installed_ids,
            "missing_template_ids": missing_ids,
        }

    @staticmethod
    def _get_manifest(module_id: str) -> ModuleManifest:
        manifest = next(
            (item for item in ModuleService.list_module_manifests([module_id]) if item.module_id == module_id),
            None,
        )
        if not manifest:
            raise HTTPException(status_code=404, detail="Module manifest not found")
        return manifest

    @staticmethod
    def _list_plugin_forms(db: Session, workspace_id: UUID, module_id: str) -> list[FormTemplate]:
        from modules.dynamic_records.models import FormTemplate

        items = db.query(FormTemplate).filter(FormTemplate.workspace_id == workspace_id).all()
        return [item for item in items if ModuleInstallService._installed_template_ids([item], module_id)]

    @staticmethod
    def _list_plugin_reports(db: Session, workspace_id: UUID, module_id: str) -> list[ReportType]:
        from modules.reports.models import ReportType

        items = db.query(ReportType).filter(ReportType.workspace_id == workspace_id).all()
        return [item for item in items if ModuleInstallService._installed_template_ids([item], module_id)]

    @staticmethod
    def get_install_status(db: Session, workspace_id: UUID, module_id: str) -> dict:
        manifest = ModuleInstallService._get_manifest(module_id)
        return ModuleInstallService.build_install_status(
            manifest=manifest,
            installed_forms=ModuleInstallService._list_plugin_forms(db, workspace_id, module_id),
            installed_reports=ModuleInstallService._list_plugin_reports(db, workspace_id, module_id),
        )

    @staticmethod
    def install_module(db: Session, workspace_id: UUID, module_id: str) -> dict:
        from modules.dynamic_records.models import FormTemplate
        from modules.reports.models import ReportType

        manifest = ModuleInstallService._get_manifest(module_id)
        installed_forms = ModuleInstallService._list_plugin_forms(db, workspace_id, module_id)
        installed_reports = ModuleInstallService._list_plugin_reports(db, workspace_id, module_id)
        installed_ids = ModuleInstallService._installed_template_ids(installed_forms, module_id)
        installed_ids.update(ModuleInstallService._installed_template_ids(installed_reports, module_id))

        created_forms = 0
        created_reports = 0
        definition = MODULE_DEFINITIONS[module_id]
        for template in manifest.templates:
            if template.id in installed_ids:
                continue
            name = f"{definition.label}: {template.label}"
            meta_data = ModuleInstallService._plugin_meta(module_id, template)
            if template.template_type == "report":
                db.add(
                    ReportType(
                        name=name,
                        description=template.description,
                        source="custom",
                        columns=ModuleInstallService.build_report_columns(template),
                        is_active=True,
                        workspace_id=workspace_id,
                        meta_data=meta_data,
                    )
                )
                created_reports += 1
            else:
                db.add(
                    FormTemplate(
                        name=name,
                        schema_structure=ModuleInstallService.build_form_schema(template),
                        workspace_id=workspace_id,
                        meta_data=meta_data,
                    )
                )
                created_forms += 1

        db.commit()
        status = ModuleInstallService.get_install_status(db, workspace_id, module_id)
        return {
            **status,
            "created_form_template_count": created_forms,
            "created_report_type_count": created_reports,
        }

    @staticmethod
    def install_enabled_modules(
        db: Session,
        workspace_id: UUID,
        enabled_modules: list[str] | tuple[str, ...] | None,
    ) -> list[dict]:
        results: list[dict] = []
        for manifest in ModuleService.list_module_manifests(enabled_modules):
            results.append(ModuleInstallService.install_module(db, workspace_id, manifest.module_id))
        return results
