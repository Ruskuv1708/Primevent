from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.base_models import CRMBasedModel


class AIConversation(CRMBasedModel):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        Index("ix_ai_conversations_workspace_id", "workspace_id"),
    )

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)
    title = Column(String, nullable=False, default="AI CRM Architect")
    status = Column(String, nullable=False, default="active")


class AIConversationMessage(CRMBasedModel):
    __tablename__ = "ai_conversation_messages"
    __table_args__ = (
        Index("ix_ai_conversation_messages_conversation_id", "conversation_id"),
    )

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)
    sender = Column(String, nullable=False)
    content = Column(Text, nullable=False)


class AIBusinessBlueprint(CRMBasedModel):
    __tablename__ = "ai_business_blueprints"
    __table_args__ = (
        Index("ix_ai_business_blueprints_workspace_id", "workspace_id"),
        Index("ix_ai_business_blueprints_conversation_id", "conversation_id"),
    )

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)
    version = Column(String, nullable=False, default="v1")
    blueprint = Column(JSONB, nullable=False, default=dict)


class AIChangeProposal(CRMBasedModel):
    __tablename__ = "ai_change_proposals"
    __table_args__ = (
        Index("ix_ai_change_proposals_workspace_id", "workspace_id"),
        Index("ix_ai_change_proposals_blueprint_id", "blueprint_id"),
    )

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)
    blueprint_id = Column(UUID(as_uuid=True), ForeignKey("ai_business_blueprints.id"), nullable=False)
    proposal_type = Column(String, nullable=False)
    operation = Column(String, nullable=False, default="create")
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    generated_artifacts = Column(JSONB, nullable=False, default=list)
    applied_artifacts = Column(JSONB, nullable=False, default=list)
    target_artifacts = Column(JSONB, nullable=False, default=list)
    before_state = Column(JSONB, nullable=False, default=dict)
    after_state = Column(JSONB, nullable=False, default=dict)
    risk_level = Column(String, nullable=False, default="low")
    status = Column(String, nullable=False, default="proposed")


class AIChangeEvent(CRMBasedModel):
    __tablename__ = "ai_change_events"
    __table_args__ = (
        Index("ix_ai_change_events_workspace_id", "workspace_id"),
        Index("ix_ai_change_events_proposal_id", "proposal_id"),
        Index("ix_ai_change_events_conversation_id", "conversation_id"),
    )

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)
    proposal_id = Column(UUID(as_uuid=True), ForeignKey("ai_change_proposals.id"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id"), nullable=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("access_users.id"), nullable=True)
    operation = Column(String, nullable=False)
    affected_artifacts = Column(JSONB, nullable=False, default=list)
    before_state = Column(JSONB, nullable=False, default=dict)
    after_state = Column(JSONB, nullable=False, default=dict)
    rollback_status = Column(String, nullable=False, default="available")
    rollback_reason = Column(Text, nullable=True)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
