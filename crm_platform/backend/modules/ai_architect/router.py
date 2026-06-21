from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database_connector import get_db
from modules.access_control.permissions import PermissionService
from modules.access_control.security import get_current_user
from modules.ai_architect.models import AIChangeProposal
from modules.ai_architect.schemas import (
    ApplyProposalResponse,
    BlueprintResponse,
    ChangeEventResponse,
    ConversationCreateRequest,
    ConversationMessageCreateRequest,
    ConversationMessageResponse,
    ConversationResponse,
    GenerateBlueprintResponse,
    ProposalResponse,
)
from modules.ai_architect.change_event_service import AIChangeEventService
from modules.ai_architect.rollback_service import AIChangeRollbackService
from modules.ai_architect.service import AIArchitectService


router = APIRouter(prefix="/ai-architect", tags=["AI Architect"])


def _require_ai_architect_access(current_user):
    PermissionService.require_permission(current_user, "use_ai_architect")


def _serialize_conversation(db, conversation):
    messages = AIArchitectService.list_messages(db, conversation.id)
    blueprint = AIArchitectService.get_latest_blueprint(db, conversation.id)
    proposals = AIArchitectService.list_proposals(db, blueprint.id) if blueprint else []
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        messages=[
            ConversationMessageResponse(id=message.id, sender=message.sender, content=message.content)
            for message in messages
        ],
        blueprint=(
            BlueprintResponse(id=blueprint.id, version=blueprint.version, blueprint=blueprint.blueprint)
            if blueprint
            else None
        ),
        proposals=[
            ProposalResponse(
                id=proposal.id,
                proposal_type=proposal.proposal_type,
                operation=proposal.operation,
                title=proposal.title,
                description=proposal.description,
                rationale=proposal.rationale,
                generated_artifacts=proposal.generated_artifacts,
                applied_artifacts=proposal.applied_artifacts,
                target_artifacts=proposal.target_artifacts,
                before_state=proposal.before_state,
                after_state=proposal.after_state,
                risk_level=proposal.risk_level,
                status=proposal.status,
            )
            for proposal in proposals
        ],
    )


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    data: ConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="Workspace is required")
    conversation = AIArchitectService.create_conversation(db, current_user.workspace_id, data.title)
    return _serialize_conversation(db, conversation)


@router.post("/conversations/{conversation_id}/messages", response_model=ConversationMessageResponse)
def add_message(
    conversation_id,
    data: ConversationMessageCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    conversation = AIArchitectService.get_conversation(db, conversation_id)
    if not conversation or conversation.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    message = AIArchitectService.add_owner_message(db, conversation, data.content)
    return ConversationMessageResponse(id=message.id, sender=message.sender, content=message.content)


@router.post("/conversations/{conversation_id}/generate", response_model=GenerateBlueprintResponse)
def generate_blueprint(
    conversation_id,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    conversation = AIArchitectService.get_conversation(db, conversation_id)
    if not conversation or conversation.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    AIArchitectService.generate_blueprint(db, conversation)
    return GenerateBlueprintResponse(conversation=_serialize_conversation(db, conversation))


@router.post("/conversations/{conversation_id}/refine", response_model=GenerateBlueprintResponse)
def refine_conversation(
    conversation_id,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    conversation = AIArchitectService.get_conversation(db, conversation_id)
    if not conversation or conversation.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    AIArchitectService.generate_refinement(db, conversation)
    return GenerateBlueprintResponse(conversation=_serialize_conversation(db, conversation))


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    conversation = AIArchitectService.get_conversation(db, conversation_id)
    if not conversation or conversation.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _serialize_conversation(db, conversation)


@router.post("/proposals/{proposal_id}/apply", response_model=ApplyProposalResponse)
def apply_proposal(
    proposal_id,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    proposal = db.query(AIChangeProposal).filter(AIChangeProposal.id == proposal_id).first()
    if not proposal or proposal.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=404, detail="Proposal not found")
    proposal = AIArchitectService.apply_proposal(db, proposal, actor_id=current_user.id)
    return ApplyProposalResponse(
        proposal=ProposalResponse(
            id=proposal.id,
            proposal_type=proposal.proposal_type,
            operation=proposal.operation,
            title=proposal.title,
            description=proposal.description,
            rationale=proposal.rationale,
            generated_artifacts=proposal.generated_artifacts,
            applied_artifacts=proposal.applied_artifacts,
            target_artifacts=proposal.target_artifacts,
            before_state=proposal.before_state,
            after_state=proposal.after_state,
            risk_level=proposal.risk_level,
            status=proposal.status,
        )
    )


def _serialize_change_event(event):
    return ChangeEventResponse(
        id=event.id,
        operation=event.operation,
        affected_artifacts=event.affected_artifacts,
        before_state=event.before_state,
        after_state=event.after_state,
        rollback_status=event.rollback_status,
        rollback_reason=event.rollback_reason,
        created_at=event.created_at.isoformat() if event.created_at else None,
        rolled_back_at=event.rolled_back_at.isoformat() if event.rolled_back_at else None,
    )


@router.get("/change-events", response_model=list[ChangeEventResponse])
def list_change_events(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    return [
        _serialize_change_event(event)
        for event in AIChangeEventService.list_events(db, current_user.workspace_id)
    ]


@router.get("/change-events/{event_id}", response_model=ChangeEventResponse)
def get_change_event(
    event_id,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    event = AIChangeEventService.get_event(db, event_id, current_user.workspace_id)
    if not event:
        raise HTTPException(status_code=404, detail="Change event not found")
    return _serialize_change_event(event)


@router.post("/change-events/{event_id}/rollback", response_model=ChangeEventResponse)
def rollback_change_event(
    event_id,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_ai_architect_access(current_user)
    event = AIChangeEventService.get_event(db, event_id, current_user.workspace_id)
    if not event:
        raise HTTPException(status_code=404, detail="Change event not found")
    AIChangeRollbackService.rollback(db, event)
    db.commit()
    db.refresh(event)
    return _serialize_change_event(event)
