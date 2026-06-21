from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ReportSource = Literal["requests", "users", "clients", "companies", "custom"]


class ReportTypeColumnSchema(BaseModel):
    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    formula: Optional[str] = Field(None, max_length=1000)
    format: Optional[str] = Field(None, max_length=120)


class ReportTypeCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    source: ReportSource = "requests"
    columns: list[ReportTypeColumnSchema] = Field(default_factory=list)
    is_active: bool = True


class ReportTypeUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    source: Optional[ReportSource] = None
    columns: Optional[list[ReportTypeColumnSchema]] = None
    is_active: Optional[bool] = None


class ReportTypeResponseSchema(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    source: ReportSource
    columns: list[ReportTypeColumnSchema]
    is_active: bool
    workspace_id: UUID
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ReportTypeGoogleImportSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    google_sheet_url: str = Field(..., min_length=10, max_length=5000)
    description: Optional[str] = Field(None, max_length=2000)
    source: Optional[ReportSource] = None
    is_active: bool = True
    header_row: int = Field(1, ge=1, le=100)
    worksheet_gid: Optional[str] = Field(None, max_length=120)
