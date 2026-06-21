from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="AI CRM Architect")


class ConversationMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)


class ConversationMessageResponse(BaseModel):
    id: UUID
    sender: str
    content: str


class ProposalResponse(BaseModel):
    id: UUID
    proposal_type: str
    operation: str
    title: str
    description: str
    rationale: str
    generated_artifacts: list[dict[str, Any]]
    applied_artifacts: list[dict[str, Any]]
    target_artifacts: list[dict[str, Any]]
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    risk_level: str
    status: str


class BlueprintResponse(BaseModel):
    id: UUID
    version: str
    blueprint: dict[str, Any]


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    status: str
    messages: list[ConversationMessageResponse] = Field(default_factory=list)
    blueprint: BlueprintResponse | None = None
    proposals: list[ProposalResponse] = Field(default_factory=list)


class GenerateBlueprintResponse(BaseModel):
    conversation: ConversationResponse


class ApplyProposalResponse(BaseModel):
    proposal: ProposalResponse


class ChangeEventResponse(BaseModel):
    id: UUID
    operation: str
    affected_artifacts: list[dict[str, Any]]
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    rollback_status: str
    rollback_reason: str | None = None
    created_at: str | None = None
    rolled_back_at: str | None = None
