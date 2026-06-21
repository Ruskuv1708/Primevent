from __future__ import annotations

from modules.ai_architect.models import AIBusinessBlueprint, AIChangeEvent


class AIChangeEventService:
    @classmethod
    def record_applied_change(cls, db, proposal, actor_id=None):
        blueprint = db.query(AIBusinessBlueprint).filter(AIBusinessBlueprint.id == proposal.blueprint_id).first()
        event = AIChangeEvent(
            workspace_id=proposal.workspace_id,
            proposal_id=proposal.id,
            conversation_id=blueprint.conversation_id if blueprint else None,
            actor_id=actor_id,
            operation=proposal.operation,
            affected_artifacts=proposal.applied_artifacts,
            before_state=proposal.before_state or {},
            after_state=proposal.after_state or {},
            rollback_status="available",
        )
        db.add(event)
        db.flush()
        return event

    @staticmethod
    def list_events(db, workspace_id):
        return (
            db.query(AIChangeEvent)
            .filter(AIChangeEvent.workspace_id == workspace_id)
            .order_by(AIChangeEvent.created_at.desc())
            .all()
        )

    @staticmethod
    def get_event(db, event_id, workspace_id):
        return (
            db.query(AIChangeEvent)
            .filter(AIChangeEvent.id == event_id, AIChangeEvent.workspace_id == workspace_id)
            .first()
        )
