from __future__ import annotations

from fastapi import HTTPException


class AIProposalMutationService:
    META_KEY = "ai_architect"

    @classmethod
    def _is_ai_authored(cls, artifact) -> bool:
        meta_data = getattr(artifact, "meta_data", None) or {}
        return isinstance(meta_data, dict) and isinstance(meta_data.get(cls.META_KEY), dict)

    @classmethod
    def _target(cls, proposal) -> dict:
        if not proposal.target_artifacts:
            raise HTTPException(status_code=400, detail="Proposal has no target artifacts")
        return proposal.target_artifacts[0]

    @classmethod
    def apply_update(cls, db, proposal):
        target = cls._target(proposal)

        if proposal.proposal_type == "forms" and target.get("type") == "form":
            from modules.dynamic_records.models import FormTemplate

            artifact = db.query(FormTemplate).filter(FormTemplate.id == target["id"]).first()
            if not artifact or artifact.workspace_id != proposal.workspace_id:
                raise HTTPException(status_code=404, detail="Form template not found")
            if not cls._is_ai_authored(artifact):
                raise HTTPException(status_code=403, detail="AI can only update AI-authored form templates")
            artifact.schema_structure = proposal.after_state.get("schema_structure", artifact.schema_structure)
            return [{"type": "form", "name": artifact.name, "id": str(artifact.id)}]

        if proposal.proposal_type == "reports" and target.get("type") == "report":
            from modules.reports.models import ReportType

            artifact = db.query(ReportType).filter(ReportType.id == target["id"]).first()
            if not artifact or artifact.workspace_id != proposal.workspace_id:
                raise HTTPException(status_code=404, detail="Report type not found")
            if not cls._is_ai_authored(artifact):
                raise HTTPException(status_code=403, detail="AI can only update AI-authored report types")
            if "name" in proposal.after_state:
                artifact.name = proposal.after_state["name"]
            if "description" in proposal.after_state:
                artifact.description = proposal.after_state["description"]
            if "columns" in proposal.after_state:
                artifact.columns = proposal.after_state["columns"]
            return [{"type": "report", "name": artifact.name, "id": str(artifact.id)}]

        if proposal.proposal_type == "departments" and target.get("type") == "department":
            from modules.workflow.models import Department

            artifact = db.query(Department).filter(Department.id == target["id"]).first()
            if not artifact or artifact.workspace_id != proposal.workspace_id:
                raise HTTPException(status_code=404, detail="Department not found")
            if not cls._is_ai_authored(artifact):
                raise HTTPException(status_code=403, detail="AI can only update AI-authored departments")
            if "name" in proposal.after_state:
                artifact.name = proposal.after_state["name"]
            if "description" in proposal.after_state:
                artifact.description = proposal.after_state["description"]
            return [{"type": "department", "name": artifact.name, "id": str(artifact.id)}]

        raise HTTPException(status_code=400, detail="Unsupported proposal update")
