from __future__ import annotations

from fastapi import HTTPException


class AIProposalInstallService:
    META_KEY = "ai_architect"

    @classmethod
    def _meta(cls, proposal, artifact_name: str) -> dict:
        return {
            cls.META_KEY: {
                "proposal_id": str(proposal.id),
                "proposal_type": proposal.proposal_type,
                "blueprint_id": str(proposal.blueprint_id),
                "artifact_name": artifact_name,
            }
        }

    @staticmethod
    def _normalized(value: str) -> str:
        return value.strip().lower()

    @classmethod
    def _existing_ai_item(cls, items, proposal, artifact_name: str):
        for item in items:
            meta_data = getattr(item, "meta_data", None) or {}
            meta = meta_data.get(cls.META_KEY) if isinstance(meta_data, dict) else None
            if (
                isinstance(meta, dict)
                and meta.get("proposal_id") == str(proposal.id)
                and meta.get("artifact_name") == artifact_name
            ):
                return item
        return None

    @classmethod
    def _existing_ai_named_item(cls, items, artifact_name: str):
        expected = cls._normalized(artifact_name)
        for item in items:
            meta_data = getattr(item, "meta_data", None) or {}
            meta = meta_data.get(cls.META_KEY) if isinstance(meta_data, dict) else None
            if isinstance(meta, dict) and cls._normalized(getattr(item, "name", "")) == expected:
                return item
        return None

    @staticmethod
    def _form_schema(name: str) -> list[dict]:
        normalized = name.lower()
        if "payment" in normalized:
            labels = [("payer", "Payer", "text"), ("amount", "Amount", "number"), ("payment_date", "Payment date", "date"), ("notes", "Notes", "text")]
        elif "attendance" in normalized:
            labels = [("person", "Person", "text"), ("date", "Date", "date"), ("status", "Status", "text"), ("notes", "Notes", "text")]
        elif "intake" in normalized:
            labels = [("name", "Name", "text"), ("phone", "Phone", "text"), ("notes", "Notes", "text")]
        else:
            labels = [("name", "Name", "text"), ("details", "Details", "text"), ("notes", "Notes", "text")]
        return [{"key": key, "label": label, "type": field_type, "required": False} for key, label, field_type in labels]

    @staticmethod
    def _report_columns(name: str) -> list[dict]:
        normalized = name.lower()
        if "overdue" in normalized:
            keys = [("name", "Name"), ("amount", "Amount"), ("due_date", "Due date"), ("status", "Status")]
        elif "revenue" in normalized or "payment" in normalized:
            keys = [("name", "Name"), ("amount", "Amount"), ("date", "Date")]
        else:
            keys = [("name", "Name"), ("value", "Value"), ("date", "Date")]
        return [{"key": key, "label": label, "formula": None, "format": None} for key, label in keys]

    @classmethod
    def apply_departments(cls, db, proposal):
        from modules.workflow.models import Department

        existing = db.query(Department).filter(Department.workspace_id == proposal.workspace_id).all()
        by_name = {cls._normalized(item.name): item for item in existing}
        installed = []
        for artifact in proposal.generated_artifacts or []:
            name = artifact["name"]
            department = by_name.get(cls._normalized(name))
            if not department:
                department = Department(
                    name=name,
                    description="Created by AI CRM Architect",
                    workspace_id=proposal.workspace_id,
                    meta_data=cls._meta(proposal, name),
                )
                db.add(department)
                by_name[cls._normalized(name)] = department
            installed.append((name, department))
        db.flush()
        return [{"type": "department", "name": name, "id": str(department.id)} for name, department in installed]

    @classmethod
    def apply_forms(cls, db, proposal):
        from modules.dynamic_records.models import FormTemplate

        existing = db.query(FormTemplate).filter(FormTemplate.workspace_id == proposal.workspace_id).all()
        installed = []
        for artifact in proposal.generated_artifacts or []:
            name = artifact["name"]
            # Allow AI to provide custom schema structure in the artifact
            custom_schema = artifact.get("schema_structure")
            template = cls._existing_ai_item(existing, proposal, name) or cls._existing_ai_named_item(existing, name)
            if not template:
                template = FormTemplate(
                    name=name,
                    schema_structure=custom_schema if custom_schema else cls._form_schema(name),
                    workspace_id=proposal.workspace_id,
                    meta_data=cls._meta(proposal, name),
                )
                db.add(template)
                existing.append(template)
            installed.append((name, template))
        db.flush()
        return [{"type": "form", "name": name, "id": str(template.id)} for name, template in installed]

    @classmethod
    def apply_reports(cls, db, proposal):
        from modules.reports.models import ReportType

        existing = db.query(ReportType).filter(ReportType.workspace_id == proposal.workspace_id).all()
        installed = []
        for artifact in proposal.generated_artifacts or []:
            name = artifact["name"]
            # Allow AI to provide custom columns in the artifact
            custom_columns = artifact.get("columns")
            report = cls._existing_ai_item(existing, proposal, name) or cls._existing_ai_named_item(existing, name)
            if not report:
                report = ReportType(
                    name=name,
                    description="Created by AI CRM Architect",
                    source="custom",
                    columns=custom_columns if custom_columns else cls._report_columns(name),
                    is_active=True,
                    workspace_id=proposal.workspace_id,
                    meta_data=cls._meta(proposal, name),
                )
                db.add(report)
                existing.append(report)
            installed.append((name, report))
        db.flush()
        return [{"type": "report", "name": name, "id": str(report.id)} for name, report in installed]

    @classmethod
    def apply_proposal(cls, db, proposal):
        if not proposal.generated_artifacts:
            raise HTTPException(status_code=400, detail="Proposal has no generated artifacts")
        if proposal.proposal_type == "departments":
            applied = cls.apply_departments(db, proposal)
        elif proposal.proposal_type == "forms":
            applied = cls.apply_forms(db, proposal)
        elif proposal.proposal_type == "reports":
            applied = cls.apply_reports(db, proposal)
        else:
            raise HTTPException(status_code=400, detail="Unsupported proposal type")
        proposal.applied_artifacts = applied
        return applied
