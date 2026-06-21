from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException


class AIChangeRollbackService:
    @staticmethod
    def _mark_unavailable(event, reason: str):
        event.rollback_status = "unavailable"
        event.rollback_reason = reason

    @classmethod
    def rollback(cls, db, event):
        if event.rollback_status == "rolled_back":
            return event
        if not event.affected_artifacts:
            cls._mark_unavailable(event, "No affected artifacts were recorded")
            raise HTTPException(status_code=400, detail=event.rollback_reason)

        artifact = event.affected_artifacts[0]
        artifact_type = artifact.get("type")

        if event.operation == "update":
            if artifact_type == "form":
                from modules.dynamic_records.models import FormTemplate

                item = db.query(FormTemplate).filter(
                    FormTemplate.id == artifact["id"],
                    FormTemplate.workspace_id == event.workspace_id,
                ).first()
                if not item:
                    cls._mark_unavailable(event, "Form template no longer exists")
                    raise HTTPException(status_code=404, detail=event.rollback_reason)
                expected = event.after_state.get("schema_structure")
                if expected is not None and item.schema_structure != expected:
                    cls._mark_unavailable(event, "Form changed after the AI update")
                    raise HTTPException(status_code=400, detail=event.rollback_reason)
                item.schema_structure = event.before_state.get("schema_structure", item.schema_structure)
            elif artifact_type == "report":
                from modules.reports.models import ReportType

                item = db.query(ReportType).filter(
                    ReportType.id == artifact["id"],
                    ReportType.workspace_id == event.workspace_id,
                ).first()
                if not item:
                    cls._mark_unavailable(event, "Report type no longer exists")
                    raise HTTPException(status_code=404, detail=event.rollback_reason)
                for field in ("name", "description", "columns"):
                    expected = event.after_state.get(field)
                    if expected is not None and getattr(item, field) != expected:
                        cls._mark_unavailable(event, "Report changed after the AI update")
                        raise HTTPException(status_code=400, detail=event.rollback_reason)
                for field in ("name", "description", "columns"):
                    if field in event.before_state:
                        setattr(item, field, event.before_state[field])
            elif artifact_type == "department":
                from modules.workflow.models import Department

                item = db.query(Department).filter(
                    Department.id == artifact["id"],
                    Department.workspace_id == event.workspace_id,
                ).first()
                if not item:
                    cls._mark_unavailable(event, "Department no longer exists")
                    raise HTTPException(status_code=404, detail=event.rollback_reason)
                for field in ("name", "description"):
                    expected = event.after_state.get(field)
                    if expected is not None and getattr(item, field) != expected:
                        cls._mark_unavailable(event, "Department changed after the AI update")
                        raise HTTPException(status_code=400, detail=event.rollback_reason)
                for field in ("name", "description"):
                    if field in event.before_state:
                        setattr(item, field, event.before_state[field])
            else:
                cls._mark_unavailable(event, "Unsupported rollback artifact")
                raise HTTPException(status_code=400, detail=event.rollback_reason)
        elif event.operation == "create":
            cls._rollback_create(db, event, artifact)
        else:
            cls._mark_unavailable(event, "Unsupported rollback operation")
            raise HTTPException(status_code=400, detail=event.rollback_reason)

        event.rollback_status = "rolled_back"
        event.rollback_reason = None
        event.rolled_back_at = datetime.now(timezone.utc)
        db.flush()
        return event

    @classmethod
    def _rollback_create(cls, db, event, artifact):
        artifact_type = artifact.get("type")
        if artifact_type == "report":
            from modules.reports.models import ReportType

            item = db.query(ReportType).filter(
                ReportType.id == artifact["id"],
                ReportType.workspace_id == event.workspace_id,
            ).first()
            if item:
                item.is_active = False
            return

        if artifact_type == "form":
            from modules.dynamic_records.models import FormRecord, FormTemplate

            item = db.query(FormTemplate).filter(
                FormTemplate.id == artifact["id"],
                FormTemplate.workspace_id == event.workspace_id,
            ).first()
            if not item:
                return
            has_records = db.query(FormRecord).filter(FormRecord.template_id == item.id).first() is not None
            if has_records:
                cls._mark_unavailable(event, "Form already has submitted records")
                raise HTTPException(status_code=400, detail=event.rollback_reason)
            db.delete(item)
            return

        if artifact_type == "department":
            from modules.access_control.models import User
            from modules.workflow.models import Department, Request

            item = db.query(Department).filter(
                Department.id == artifact["id"],
                Department.workspace_id == event.workspace_id,
            ).first()
            if not item:
                return
            if db.query(Request).filter(
                Request.department_id == item.id,
                Request.workspace_id == event.workspace_id,
            ).first() is not None:
                cls._mark_unavailable(event, "Department already has requests")
                raise HTTPException(status_code=400, detail=event.rollback_reason)
            if db.query(User).filter(
                User.department_id == item.id,
                User.workspace_id == event.workspace_id,
            ).first() is not None:
                cls._mark_unavailable(event, "Department already has assigned users")
                raise HTTPException(status_code=400, detail=event.rollback_reason)
            db.delete(item)
            return

        cls._mark_unavailable(event, "Unsupported rollback artifact")
        raise HTTPException(status_code=400, detail=event.rollback_reason)
