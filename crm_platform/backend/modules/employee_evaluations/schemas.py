from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class EmployeeEvaluationCreate(BaseModel):
    employee_id: UUID
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    score: int = Field(ge=1, le=10)
    period_label: str | None = Field(default=None, max_length=80)
    comment: str | None = None


class EmployeeEvaluationUpdate(BaseModel):
    employee_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    score: int | None = Field(default=None, ge=1, le=10)
    period_label: str | None = Field(default=None, max_length=80)
    comment: str | None = None
