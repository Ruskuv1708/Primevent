from typing import List, Optional

from pydantic import BaseModel, Field


class ModuleSynergyResponse(BaseModel):
    module_id: str
    label: str
    description: str


class ModuleDefinitionResponse(BaseModel):
    id: str
    label: str
    category: str
    description: str
    route_path: str = ""
    summary: str = ""
    capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    synergies: list[ModuleSynergyResponse] = Field(default_factory=list)
    default_enabled: bool = False


class ModuleTemplateResponse(BaseModel):
    id: str
    label: str
    template_type: str
    description: str
    fields: list[str] = Field(default_factory=list)
    stages: list[str] = Field(default_factory=list)


class ModuleManifestResponse(BaseModel):
    module_id: str
    label: str
    summary: str = ""
    templates: list[ModuleTemplateResponse] = Field(default_factory=list)


class ModuleInstallStatusResponse(BaseModel):
    module_id: str
    label: str
    total_templates: int
    installed_count: int
    is_installed: bool
    installed_template_ids: list[str] = Field(default_factory=list)
    missing_template_ids: list[str] = Field(default_factory=list)


class ModuleInstallResultResponse(ModuleInstallStatusResponse):
    created_form_template_count: int = 0
    created_report_type_count: int = 0


class WorkspaceModuleSettingsResponse(BaseModel):
    module_preset: str
    enabled_modules: list[str]


class WorkspaceModuleSettingsUpdate(BaseModel):
    module_preset: str = "functional"
    enabled_modules: Optional[List[str]] = None
