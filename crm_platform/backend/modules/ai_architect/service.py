from __future__ import annotations

from fastapi import HTTPException

from modules.ai_architect.models import (
    AIBusinessBlueprint,
    AIChangeEvent,
    AIChangeProposal,
    AIConversation,
    AIConversationMessage,
)
from modules.ai_architect.change_event_service import AIChangeEventService
from modules.ai_architect.platform_context import build_platform_context
from modules.ai_architect.proposal_install_service import AIProposalInstallService
from modules.ai_architect.proposal_mutation_service import AIProposalMutationService
from modules.ai_architect.provider_factory import build_architect_provider
from modules.ai_architect.refinement_guard import reinforce_requested_form_fields


def _contains_cyrillic(value: str) -> bool:
    return any("\u0400" <= char <= "\u04ff" for char in value)


class AIArchitectService:
    provider = build_architect_provider()

    @classmethod
    def refresh_provider(cls):
        cls.provider = build_architect_provider()
        return cls.provider

    @classmethod
    def create_conversation(cls, db, workspace_id, title: str = "AI CRM Architect"):
        conversation = AIConversation(workspace_id=workspace_id, title=title)
        db.add(conversation)
        db.flush()
        db.commit()
        db.refresh(conversation)
        return conversation

    @classmethod
    def add_owner_message(cls, db, conversation: AIConversation, content: str):
        message = AIConversationMessage(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            sender="owner",
            content=content,
        )
        db.add(message)
        db.flush()
        db.commit()
        db.refresh(message)
        return message

    @classmethod
    def list_messages(cls, db, conversation_id):
        return (
            db.query(AIConversationMessage)
            .filter(AIConversationMessage.conversation_id == conversation_id)
            .order_by(AIConversationMessage.created_at.asc())
            .all()
        )

    @classmethod
    def generate_blueprint(cls, db, conversation: AIConversation):
        messages = cls.list_messages(db, conversation.id)
        owner_messages = [message.content for message in messages if message.sender == "owner"]
        blueprint_payload = cls.provider.generate_blueprint(owner_messages)
        blueprint = AIBusinessBlueprint(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            blueprint=blueprint_payload,
        )
        db.add(blueprint)
        db.flush()

        proposals = []
        for payload in cls.provider.generate_proposals(blueprint_payload):
            proposal = AIChangeProposal(
                workspace_id=conversation.workspace_id,
                blueprint_id=blueprint.id,
                proposal_type=payload["proposal_type"],
                operation=payload.get("operation", "create"),
                title=payload["title"],
                description=payload["description"],
                rationale=payload["rationale"],
                generated_artifacts=payload["generated_artifacts"],
                target_artifacts=payload.get("target_artifacts", []),
                before_state=payload.get("before_state", {}),
                after_state=payload.get("after_state", {}),
                risk_level=payload.get("risk_level", "low"),
            )
            db.add(proposal)
            proposals.append(proposal)

        db.flush()
        db.commit()
        db.refresh(blueprint)
        for proposal in proposals:
            db.refresh(proposal)
        return blueprint, proposals

    @classmethod
    def get_conversation(cls, db, conversation_id):
        return db.query(AIConversation).filter(AIConversation.id == conversation_id).first()

    @classmethod
    def get_latest_blueprint(cls, db, conversation_id):
        return (
            db.query(AIBusinessBlueprint)
            .filter(AIBusinessBlueprint.conversation_id == conversation_id)
            .order_by(AIBusinessBlueprint.created_at.desc())
            .first()
        )

    @classmethod
    def list_proposals(cls, db, blueprint_id):
        return (
            db.query(AIChangeProposal)
            .filter(AIChangeProposal.blueprint_id == blueprint_id)
            .order_by(AIChangeProposal.created_at.asc())
            .all()
        )

    @classmethod
    def _artifact_context(cls, db, workspace_id):
        from modules.dynamic_records.models import FormTemplate
        from modules.reports.models import ReportType
        from modules.workflow.models import Department

        departments = [
            {"id": str(item.id), "name": item.name, "description": item.description}
            for item in db.query(Department).filter(Department.workspace_id == workspace_id).all()
        ]
        forms = [
            {"id": str(item.id), "name": item.name, "schema_structure": item.schema_structure}
            for item in db.query(FormTemplate).filter(FormTemplate.workspace_id == workspace_id).all()
        ]
        reports = [
            {
                "id": str(item.id),
                "name": item.name,
                "description": item.description,
                "columns": item.columns,
            }
            for item in db.query(ReportType).filter(ReportType.workspace_id == workspace_id).all()
        ]
        return {
            "departments": departments,
            "forms": forms,
            "reports": reports,
            **build_platform_context(db, workspace_id),
        }

    @classmethod
    def _recent_history(cls, db, workspace_id):
        events = (
            db.query(AIChangeEvent)
            .filter(AIChangeEvent.workspace_id == workspace_id)
            .order_by(AIChangeEvent.created_at.desc())
            .all()
        )
        return [
            {
                "operation": event.operation,
                "affected_artifacts": event.affected_artifacts,
                "rollback_status": event.rollback_status,
            }
            for event in events[:5]
        ]

    @classmethod
    def generate_refinement(cls, db, conversation: AIConversation):
        messages = cls.list_messages(db, conversation.id)
        owner_messages = [message for message in messages if message.sender == "owner"]
        if not owner_messages:
            raise HTTPException(status_code=400, detail="Owner message is required before refinement")
        latest_owner_message = owner_messages[-1]
        blueprint = cls.get_latest_blueprint(db, conversation.id)
        if not blueprint:
            raise HTTPException(status_code=400, detail="Generate a blueprint before refining it")
        payload = cls.provider.generate_refinement(
            latest_owner_message.content,
            cls._artifact_context(db, conversation.workspace_id),
            blueprint.blueprint,
            cls._recent_history(db, conversation.workspace_id),
        )
        payload = reinforce_requested_form_fields(payload, latest_owner_message.content)

        if payload.get("kind") == "clarification":
            reply = AIConversationMessage(
                conversation_id=conversation.id,
                workspace_id=conversation.workspace_id,
                sender="ai",
                content=payload["message"],
            )
            db.add(reply)
            db.flush()
            db.commit()
            db.refresh(reply)
            return reply, []

        proposal = AIChangeProposal(
            workspace_id=conversation.workspace_id,
            blueprint_id=blueprint.id,
            proposal_type=payload["proposal_type"],
            operation=payload.get("operation", "create"),
            title=payload["title"],
            description=payload["description"],
            rationale=payload["rationale"],
            generated_artifacts=payload.get("generated_artifacts", []),
            target_artifacts=payload.get("target_artifacts", []),
            before_state=payload.get("before_state", {}),
            after_state=payload.get("after_state", {}),
            risk_level=payload.get("risk_level", "low"),
        )
        reply = AIConversationMessage(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            sender="ai",
            content=(
                f"Я подготовил предложение с уровнем риска {proposal.risk_level}: {proposal.title}."
                if _contains_cyrillic(latest_owner_message.content) or _contains_cyrillic(proposal.title)
                else f"I drafted a {proposal.risk_level}-risk proposal: {proposal.title}."
            ),
        )
        db.add(reply)
        db.add(proposal)
        db.flush()
        db.commit()
        db.refresh(reply)
        db.refresh(proposal)
        return reply, [proposal]

    @classmethod
    def apply_proposal(cls, db, proposal: AIChangeProposal, actor_id=None):
        if proposal.operation == "create":
            AIProposalInstallService.apply_proposal(db, proposal)
        elif proposal.operation == "update":
            proposal.applied_artifacts = AIProposalMutationService.apply_update(db, proposal)
        else:
            raise HTTPException(status_code=400, detail="Unsupported proposal operation")
        proposal.status = "applied"
        AIChangeEventService.record_applied_change(db, proposal, actor_id=actor_id)
        db.commit()
        db.refresh(proposal)
        return proposal
