from __future__ import annotations

import json
from typing import Literal

import requests
from pydantic import BaseModel, Field, model_validator

from core.config import settings
from modules.ai_architect.provider_base import ArchitectProvider


RUSSIAN_LANGUAGE_INSTRUCTION = (
    "You understand Russian and English CRM owner requests. If the owner writes in Russian, "
    "infer the CRM intent from Russian business vocabulary and write all human-facing titles, "
    "descriptions, rationales, assumptions, department names, form names, report names, and "
    "clarification messages in Russian. Keep JSON keys and enum values exactly as the schema "
    "requires. Return only valid JSON matching the schema.\n\n"
    "DESIGN PRINCIPLES:\n"
    "1. OBJECTS, NOT PROCESSES: Name forms after the entities they represent (e.g., 'Inventory', 'Client') "
    "instead of actions (e.g., 'Inventory Creation', 'Edit Client'). One form per entity is enough.\n"
    "2. NO DUPLICATION: Never create separate forms for 'Creation' and 'Editing' of the same thing. "
    "The system uses one template for both.\n"
    "3. COMPREHENSIVE FIELDS: Always provide a full 'schema_structure' with at least 5-8 relevant fields "
    "for any new form. Do not use placeholders like 'Field 1'. If the owner provides an exact field count "
    "or field names, treat that as a hard requirement and include every requested field. Never cap forms at "
    "three fields because an example contains three fields.\n"
    "4. EXISTING SYSTEM FIRST: Existing pages, modules, mechanisms, methods, forms, departments, and reports "
    "are part of the architecture. Reuse or refine them before creating a duplicate page or mechanism.\n\n"
    "SCHEMA EXAMPLE for 'schema_structure':\n"
    "[\n"
    "  {\"key\": \"full_name\", \"label\": \"Full Name\", \"type\": \"text\", \"required\": true},\n"
    "  {\"key\": \"age\", \"label\": \"Age\", \"type\": \"number\", \"required\": false},\n"
    "  {\"key\": \"birth_date\", \"label\": \"Date of Birth\", \"type\": \"date\", \"required\": false}\n"
    "]\n\n"
    "You have full visibility into existing departments, forms, and reports. Always take them into "
    "account and aim to integrate with or refine existing structures instead of ignoring them."
)


def _contains_cyrillic(value: str) -> bool:
    return any("\u0400" <= char <= "\u04ff" for char in value)


def _blueprint_is_russian(blueprint: dict) -> bool:
    payload = json.dumps(blueprint, ensure_ascii=False)
    return _contains_cyrillic(payload)


class LiveProposalPayload(BaseModel):
    proposal_type: Literal["departments", "forms", "reports"]
    operation: Literal["create", "update"]
    title: str
    description: str
    rationale: str
    generated_artifacts: list[dict] = Field(default_factory=list)
    target_artifacts: list[dict] = Field(default_factory=list)
    before_state: dict = Field(default_factory=dict)
    after_state: dict = Field(default_factory=dict)
    risk_level: Literal["low", "medium", "high"] = "low"


class LiveRefinementPayload(BaseModel):
    kind: Literal["proposal", "clarification"]
    proposal: LiveProposalPayload | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_shape(self):
        if self.kind == "proposal" and self.proposal is None:
            raise ValueError("proposal payload is required")
        if self.kind == "clarification" and not self.message:
            raise ValueError("clarification message is required")
        return self


class LiveBlueprintPayload(BaseModel):
    business_summary: str
    business_profile: str
    departments: list[str]
    roles: list[str]
    entities: list[str]
    forms: list[str]
    reports: list[str]
    assumptions: list[str]


def validate_refinement_payload(payload: dict) -> dict:
    return LiveRefinementPayload.model_validate(payload).model_dump()


def flatten_refinement_payload(payload: dict) -> dict:
    if payload.get("kind") == "clarification":
        return {"kind": "clarification", "message": payload["message"]}
    proposal = payload.get("proposal") or {}
    return {"kind": "proposal", **proposal}


def validate_blueprint_payload(payload: dict) -> dict:
    return LiveBlueprintPayload.model_validate(payload).model_dump()


class LiveBatchProposalsPayload(BaseModel):
    proposals: list[LiveProposalPayload]


class _StructuredLiveArchitectProvider(ArchitectProvider):
    provider_name = "live"

    def __init__(self, *, model: str | None = None, api_key: str | None = None, base_url: str | None = None):
        self.model = model or settings.AI_ARCHITECT_MODEL
        self.api_key = api_key or settings.AI_ARCHITECT_API_KEY
        self.base_url = base_url or settings.AI_ARCHITECT_BASE_URL
        if not self.model:
            raise ValueError("AI_ARCHITECT_MODEL is required for live providers")
        if not self.api_key:
            raise ValueError("AI_ARCHITECT_API_KEY is required for live providers")

    def generate_blueprint(self, owner_messages: list[str]) -> dict:
        prompt = self._prompt_for_blueprint(owner_messages)
        return validate_blueprint_payload(self._request_structured(prompt, self._blueprint_schema()))

    def generate_proposals(self, blueprint: dict) -> list[dict]:
        prompt = self._prompt_for_batch_proposals(blueprint)
        payload = self._request_structured(prompt, LiveBatchProposalsPayload.model_json_schema())
        return [LiveProposalPayload.model_validate(p).model_dump() for p in payload.get("proposals", [])]

    @staticmethod
    def _prompt_for_batch_proposals(blueprint: dict) -> str:
        return (
            f"{RUSSIAN_LANGUAGE_INSTRUCTION}\n\n"
            "Generate a list of initial proposals to implement the provided blueprint. "
            "You should create departments, forms (with full schema_structure), and reports (with full columns). "
            "Follow the DESIGN PRINCIPLES: use object names for forms and provide at least 5-8 fields per form.\n\n"
            f"Blueprint: {json.dumps(blueprint, ensure_ascii=False)}"
        )

    def generate_refinement(
        self,
        message: str,
        artifacts: dict,
        blueprint: dict | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        prompt = self._prompt_for_refinement(message, artifacts, blueprint, history)
        payload = validate_refinement_payload(self._request_structured(prompt, self._refinement_schema()))
        return flatten_refinement_payload(payload)

    @staticmethod
    def _prompt_for_blueprint(owner_messages: list[str]) -> str:
        transcript = "\n".join(owner_messages)
        return (
            f"{RUSSIAN_LANGUAGE_INSTRUCTION}\n\n"
            "Create a CRM business blueprint from the owner's description. "
            "You are starting from scratch or proposing a major overhaul. "
            "Return only the requested structured payload.\n\n"
            f"Owner transcript:\n{transcript}"
        )

    @staticmethod
    def _prompt_for_refinement(message: str, artifacts: dict, blueprint: dict | None, history: list[dict] | None) -> str:
        return (
            f"{RUSSIAN_LANGUAGE_INSTRUCTION}\n\n"
            "Draft one CRM refinement proposal or ask for clarification. "
            "Use only supported operations and never imply that a live change has already happened.\n\n"
            "IMPORTANT: The 'Artifacts' JSON below contains EVERYTHING currently existing in the system. "
            "Take it into account. If the user asks for more fields in a form, provide the full updated 'schema_structure'.\n\n"
            "The Artifacts JSON may include existing_pages, existing_mechanisms, enabled_modules, and module_templates. "
            "Use those entries to decide what should be reused, updated, or connected before proposing anything new.\n\n"
            f"Owner request: {message}\n"
            f"Blueprint: {json.dumps(blueprint or {}, ensure_ascii=False)}\n"
            f"Artifacts: {json.dumps(artifacts, ensure_ascii=False)}\n"
            f"Recent history: {json.dumps(history or [], ensure_ascii=False)}"
        )

    @staticmethod
    def _blueprint_schema() -> dict:
        return LiveBlueprintPayload.model_json_schema()

    @staticmethod
    def _refinement_schema() -> dict:
        return LiveRefinementPayload.model_json_schema()

    def _request_structured(self, prompt: str, schema: dict) -> dict:
        raise NotImplementedError


class GeminiArchitectProvider(_StructuredLiveArchitectProvider):
    provider_name = "gemini"

    def _request_structured(self, prompt: str, schema: dict) -> dict:
        base_url = self.base_url or "https://generativelanguage.googleapis.com/v1beta"
        response = requests.post(
            f"{base_url}/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema,
                },
            },
            timeout=settings.AI_ARCHITECT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)


class GrokArchitectProvider(_StructuredLiveArchitectProvider):
    provider_name = "grok"

    def _request_structured(self, prompt: str, schema: dict) -> dict:
        base_url = self.base_url or "https://api.x.ai/v1"
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": RUSSIAN_LANGUAGE_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "crm_architect_payload", "schema": schema},
                },
            },
            timeout=settings.AI_ARCHITECT_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            print(f"❌ GROK API ERROR: {response.status_code} - {response.text}")
        response.raise_for_status()
        payload = response.json()
        return json.loads(payload["choices"][0]["message"]["content"])


class GroqArchitectProvider(_StructuredLiveArchitectProvider):
    provider_name = "groq"

    def _request_structured(self, prompt: str, schema: dict) -> dict:
        base_url = self.base_url or "https://api.groq.com/openai/v1"
        # Groq doesn't support 'json_schema' yet, but supports 'json_object'.
        # We must instruct the model to follow the schema in the prompt.
        prompt_with_schema = (
            f"{prompt}\n\n"
            f"IMPORTANT: You must return valid JSON that exactly matches this JSON schema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": RUSSIAN_LANGUAGE_INSTRUCTION},
                    {"role": "user", "content": prompt_with_schema},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=settings.AI_ARCHITECT_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            print(f"❌ GROQ API ERROR: {response.status_code} - {response.text}")
        response.raise_for_status()
        payload = response.json()
        return json.loads(payload["choices"][0]["message"]["content"])
