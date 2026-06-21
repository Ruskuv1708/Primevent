import pytest

from modules.ai_architect.deterministic_provider import DeterministicArchitectProvider


def service_with_deterministic_provider():
    from modules.ai_architect.service import AIArchitectService

    AIArchitectService.provider = DeterministicArchitectProvider()
    return AIArchitectService


def test_provider_builds_education_blueprint_from_owner_text():
    provider = DeterministicArchitectProvider()

    blueprint = provider.generate_blueprint(
        [
            "We run an education center with students, parents, groups, teachers, attendance, and monthly fees.",
        ]
    )

    assert blueprint["business_profile"] == "general"
    assert blueprint["business_summary"].startswith("Education center")
    assert "Students" in blueprint["entities"]
    assert "Attendance" in blueprint["entities"]


def test_provider_generates_installable_proposals_with_rationales():
    provider = DeterministicArchitectProvider()

    blueprint = provider.generate_blueprint(
        [
            "We run an education center with students, parents, groups, teachers, attendance, and monthly fees.",
        ]
    )
    proposals = provider.generate_proposals(blueprint)

    proposal_types = {proposal["proposal_type"] for proposal in proposals}
    assert {"departments", "forms", "reports"}.issubset(proposal_types)
    assert all(proposal["rationale"] for proposal in proposals)
    assert all(proposal["generated_artifacts"] for proposal in proposals)


def test_provider_falls_back_to_general_blueprint():
    provider = DeterministicArchitectProvider()

    blueprint = provider.generate_blueprint(["We manage customers and recurring internal work."])

    assert blueprint["business_profile"] == "general"
    assert blueprint["entities"] == ["Customers", "Requests"]


def test_provider_understands_russian_event_business():
    provider = DeterministicArchitectProvider()

    blueprint = provider.generate_blueprint(
        [
            "У нас ивент-агентство: аниматоры, шоу, квесты, выпускные, ведущие и тимбилдинги.",
        ]
    )
    proposals = provider.generate_proposals(blueprint)

    assert blueprint["business_profile"] == "general"
    assert "Заказы" in blueprint["entities"]
    assert "Координация" in blueprint["departments"]
    assert proposals[0]["title"] == "Создать стартовые отделы"
    assert proposals[1]["generated_artifacts"][0]["name"] == "Заявка на праздник"
    assert len(proposals[1]["generated_artifacts"][0]["schema_structure"]) >= 10


def test_service_creates_conversation_and_persists_owner_message(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4

    AIArchitectService = service_with_deterministic_provider()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self):
            self.items = []
            self.committed = False

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def commit(self):
            self.committed = True

        def refresh(self, item):
            return None

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    db = DatabaseStub()
    workspace_id = uuid4()

    conversation = AIArchitectService.create_conversation(db, workspace_id, title="Setup")
    message = AIArchitectService.add_owner_message(db, conversation, "We run a clinic.")

    assert conversation.workspace_id == workspace_id
    assert conversation.title == "Setup"
    assert message.sender == "owner"
    assert message.content == "We run a clinic."
    assert db.committed is True


def test_service_generates_blueprint_and_proposals(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4

    AIArchitectService = service_with_deterministic_provider()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def commit(self):
            return None

        def refresh(self, item):
            return None

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    db = DatabaseStub()
    workspace_id = uuid4()
    conversation = AIArchitectService.create_conversation(db, workspace_id, title="Setup")
    AIArchitectService.add_owner_message(
        db,
        conversation,
        "We run an education center with students, groups, attendance, and monthly fees.",
    )

    blueprint, proposals = AIArchitectService.generate_blueprint(db, conversation)

    assert blueprint.blueprint["business_profile"] == "general"
    assert len(proposals) == 3
    assert {proposal.proposal_type for proposal in proposals} == {"departments", "forms", "reports"}


def test_service_applies_proposal_status(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow import models as workflow_models  # noqa: F401

    AIArchitectService = service_with_deterministic_provider()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def commit(self):
            return None

        def refresh(self, item):
            return None

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    db = DatabaseStub()
    workspace_id = uuid4()
    conversation = AIArchitectService.create_conversation(db, workspace_id)
    AIArchitectService.add_owner_message(db, conversation, "We run a shop with products and stock.")
    _, proposals = AIArchitectService.generate_blueprint(db, conversation)

    proposal = AIArchitectService.apply_proposal(db, proposals[0])

    assert proposal.status == "applied"


def test_installer_creates_departments_and_is_idempotent(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.ai_architect.proposal_install_service import AIProposalInstallService
    from modules.ai_architect.models import AIChangeProposal
    from modules.workflow.models import Department

    workspace_id = uuid4()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    proposal = AIChangeProposal(
        id=uuid4(),
        workspace_id=workspace_id,
        blueprint_id=uuid4(),
        proposal_type="departments",
        title="Create departments",
        description="desc",
        rationale="why",
        generated_artifacts=[
            {"type": "department", "name": "Admissions"},
            {"type": "department", "name": "Finance"},
        ],
        applied_artifacts=[],
    )
    db = DatabaseStub()

    first = AIProposalInstallService.apply_proposal(db, proposal)
    second = AIProposalInstallService.apply_proposal(db, proposal)

    assert [item.name for item in db.items if isinstance(item, Department)] == ["Admissions", "Finance"]
    assert len(first) == 2
    assert len(second) == 2
    assert all(item["id"] != "None" for item in first)


def test_installer_creates_forms_and_reports_with_ai_metadata(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.ai_architect.proposal_install_service import AIProposalInstallService
    from modules.ai_architect.models import AIChangeProposal
    from modules.dynamic_records.models import FormTemplate
    from modules.reports.models import ReportType

    workspace_id = uuid4()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    db = DatabaseStub()
    form_proposal = AIChangeProposal(
        id=uuid4(),
        workspace_id=workspace_id,
        blueprint_id=uuid4(),
        proposal_type="forms",
        title="Create forms",
        description="desc",
        rationale="why",
        generated_artifacts=[{"type": "form", "name": "Payment record"}],
        applied_artifacts=[],
    )
    report_proposal = AIChangeProposal(
        id=uuid4(),
        workspace_id=workspace_id,
        blueprint_id=uuid4(),
        proposal_type="reports",
        title="Create reports",
        description="desc",
        rationale="why",
        generated_artifacts=[{"type": "report", "name": "Overdue fees"}],
        applied_artifacts=[],
    )

    form_artifacts = AIProposalInstallService.apply_proposal(db, form_proposal)
    report_artifacts = AIProposalInstallService.apply_proposal(db, report_proposal)

    form = next(item for item in db.items if isinstance(item, FormTemplate))
    report = next(item for item in db.items if isinstance(item, ReportType))
    assert form.meta_data["ai_architect"]["proposal_id"] == str(form_proposal.id)
    assert any(field["key"] == "amount" for field in form.schema_structure)
    assert report.meta_data["ai_architect"]["proposal_id"] == str(report_proposal.id)
    assert any(column["key"] == "due_date" for column in report.columns)
    assert form_artifacts[0]["id"] != "None"
    assert report_artifacts[0]["id"] != "None"


def test_installer_reuses_existing_named_ai_form_across_proposals(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.ai_architect.proposal_install_service import AIProposalInstallService
    from modules.ai_architect.models import AIChangeProposal
    from modules.dynamic_records.models import FormTemplate

    workspace_id = uuid4()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    db = DatabaseStub()
    existing = FormTemplate(
        workspace_id=workspace_id,
        name="Student intake",
        schema_structure=[],
        meta_data={"ai_architect": {"proposal_id": str(uuid4()), "artifact_name": "Student intake"}},
    )
    db.add(existing)
    db.flush()
    proposal = AIChangeProposal(
        id=uuid4(),
        workspace_id=workspace_id,
        blueprint_id=uuid4(),
        proposal_type="forms",
        title="Create forms",
        description="desc",
        rationale="why",
        generated_artifacts=[{"type": "form", "name": "Student intake"}],
        applied_artifacts=[],
    )

    applied = AIProposalInstallService.apply_proposal(db, proposal)

    assert len([item for item in db.items if isinstance(item, FormTemplate)]) == 1
    assert applied[0]["id"] == str(existing.id)


def test_refinement_provider_adds_parent_phone_field():
    from modules.ai_architect.refinement_provider import DeterministicRefinementProvider

    provider = DeterministicRefinementProvider()
    proposal = provider.generate_refinement(
        message="Add parent phone number to student intake",
        artifacts={
            "forms": [
                {
                    "id": "form-1",
                    "name": "Student intake",
                    "schema_structure": [
                        {"key": "name", "label": "Name", "type": "text", "required": False},
                    ],
                }
            ],
            "departments": [],
            "reports": [],
        },
    )

    assert proposal["operation"] == "update"
    assert proposal["proposal_type"] == "forms"
    assert proposal["target_artifacts"][0]["name"] == "Student intake"
    assert proposal["after_state"]["schema_structure"][-1]["key"] == "parent_phone"


def test_refinement_provider_returns_clarification_for_unknown_request():
    from modules.ai_architect.refinement_provider import DeterministicRefinementProvider

    provider = DeterministicRefinementProvider()
    proposal = provider.generate_refinement(
        message="Make everything better",
        artifacts={"forms": [], "departments": [], "reports": []},
    )

    assert proposal["kind"] == "clarification"
    assert "more specific" in proposal["message"].lower()


def test_service_creates_ai_reply_and_refinement_proposal(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.dynamic_records.models import FormTemplate
    from modules.ai_architect.models import AIBusinessBlueprint

    AIArchitectService = service_with_deterministic_provider()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def commit(self):
            return None

        def refresh(self, item):
            return None

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    db = DatabaseStub()
    workspace_id = uuid4()
    conversation = AIArchitectService.create_conversation(db, workspace_id, title="Setup")
    db.add(
        AIBusinessBlueprint(
            conversation_id=conversation.id,
            workspace_id=workspace_id,
            blueprint={"business_profile": "general"},
        )
    )
    db.add(
        FormTemplate(
            workspace_id=workspace_id,
            name="Student intake",
            schema_structure=[{"key": "name", "label": "Name", "type": "text", "required": False}],
            meta_data={"ai_architect": {"proposal_id": str(uuid4())}},
        )
    )
    db.flush()
    AIArchitectService.add_owner_message(db, conversation, "Add parent phone number to student intake")

    reply, proposals = AIArchitectService.generate_refinement(db, conversation)

    assert reply.sender == "ai"
    assert "parent phone" in reply.content.lower()
    assert proposals[0].operation == "update"
    assert proposals[0].target_artifacts[0]["name"] == "Student intake"


def test_service_refinement_preserves_all_requested_form_fields(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.ai_architect.models import AIBusinessBlueprint

    AIArchitectService = service_with_deterministic_provider()

    class TruncatingProvider:
        def generate_refinement(self, message, artifacts, blueprint=None, history=None):
            return {
                "kind": "proposal",
                "proposal_type": "forms",
                "operation": "create",
                "title": "Создать форму Заявка на праздник",
                "description": "Создать форму для заявок.",
                "rationale": "Заявки нужно вести структурированно.",
                "generated_artifacts": [
                    {
                        "type": "form",
                        "name": "Заявка на праздник",
                        "schema_structure": [
                            {"key": "name", "label": "Name", "type": "text", "required": False},
                            {"key": "details", "label": "Details", "type": "text", "required": False},
                            {"key": "notes", "label": "Notes", "type": "text", "required": False},
                        ],
                    }
                ],
                "target_artifacts": [],
                "before_state": {},
                "after_state": {},
                "risk_level": "low",
            }

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def commit(self):
            return None

        def refresh(self, item):
            return None

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    db = DatabaseStub()
    workspace_id = uuid4()
    conversation = AIArchitectService.create_conversation(db, workspace_id, title="Setup")
    db.add(
        AIBusinessBlueprint(
            conversation_id=conversation.id,
            workspace_id=workspace_id,
            blueprint={"business_profile": "general"},
        )
    )
    db.flush()
    AIArchitectService.provider = TruncatingProvider()
    AIArchitectService.add_owner_message(
        db,
        conversation,
        (
            "Создай форму Заявка на праздник с 8 полями: Дата мероприятия, Имя клиента, "
            "Телефон клиента, Адрес, Программа, Аниматор, Стоимость, Статус"
        ),
    )

    _, proposals = AIArchitectService.generate_refinement(db, conversation)

    schema = proposals[0].generated_artifacts[0]["schema_structure"]
    assert [field["label"] for field in schema] == [
        "Дата мероприятия",
        "Имя клиента",
        "Телефон клиента",
        "Адрес",
        "Программа",
        "Аниматор",
        "Стоимость",
        "Статус",
    ]


def test_artifact_context_includes_existing_crm_pages_modules_and_mechanisms(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from modules.access_control import models as access_models  # noqa: F401
    from modules.access_control.models import Workspace

    AIArchitectService = service_with_deterministic_provider()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self, items):
            self.items = items

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    workspace_id = uuid4()
    db = DatabaseStub(
        [
            Workspace(
                id=workspace_id,
                name="Prime Event",
                subdomain_prefix="prime",
                admin_email="admin@example.com",
                admin_full_name="Admin",
                settings={"business_profile": "general", "enabled_modules": ["workflow", "dynamic_forms"]},
            )
        ]
    )

    context = AIArchitectService._artifact_context(db, workspace_id)

    assert any(page["route"] == "/forms" for page in context["existing_pages"])
    assert any(mechanism["id"] == "dynamic_forms" for mechanism in context["existing_mechanisms"])
    assert any(module["id"] == "workflow" for module in context["enabled_modules"])


def test_mutation_service_updates_only_ai_authored_form(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from fastapi import HTTPException
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.dynamic_records.models import FormTemplate
    from modules.ai_architect.models import AIChangeProposal
    from modules.ai_architect.proposal_mutation_service import AIProposalMutationService

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    workspace_id = uuid4()
    db = DatabaseStub()
    ai_template = FormTemplate(
        workspace_id=workspace_id,
        name="Student intake",
        schema_structure=[{"key": "name", "label": "Name", "type": "text", "required": False}],
        meta_data={"ai_architect": {"proposal_id": str(uuid4())}},
    )
    db.add(ai_template)
    db.flush()
    proposal = AIChangeProposal(
        id=uuid4(),
        workspace_id=workspace_id,
        blueprint_id=uuid4(),
        proposal_type="forms",
        operation="update",
        title="Add parent phone",
        description="desc",
        rationale="why",
        generated_artifacts=[],
        applied_artifacts=[],
        target_artifacts=[{"type": "form", "id": str(ai_template.id), "name": ai_template.name}],
        before_state={"schema_structure": ai_template.schema_structure},
        after_state={
            "schema_structure": [
                *ai_template.schema_structure,
                {"key": "parent_phone", "label": "Parent phone", "type": "text", "required": False},
            ]
        },
    )

    applied = AIProposalMutationService.apply_update(db, proposal)
    assert ai_template.schema_structure[-1]["key"] == "parent_phone"
    assert applied[0]["id"] == str(ai_template.id)

    user_template = FormTemplate(
        workspace_id=workspace_id,
        name="Manual form",
        schema_structure=[],
        meta_data={},
    )
    db = DatabaseStub()
    db.add(user_template)
    db.flush()
    proposal.target_artifacts = [{"type": "form", "id": str(user_template.id), "name": user_template.name}]
    with pytest.raises(HTTPException):
        AIProposalMutationService.apply_update(db, proposal)


def test_apply_proposal_records_change_event_and_rolls_back(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from uuid import uuid4
    from modules.access_control import models as access_models  # noqa: F401
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.dynamic_records.models import FormTemplate
    from modules.ai_architect.models import AIChangeEvent, AIChangeProposal
    from modules.ai_architect.rollback_service import AIChangeRollbackService

    AIArchitectService = service_with_deterministic_provider()

    class QueryStub:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

        def first(self):
            return self.items[0] if self.items else None

    class DatabaseStub:
        def __init__(self):
            self.items = []

        def add(self, item):
            self.items.append(item)

        def flush(self):
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid4()

        def commit(self):
            return None

        def refresh(self, item):
            return None

        def query(self, model):
            return QueryStub([item for item in self.items if isinstance(item, model)])

    workspace_id = uuid4()
    actor_id = uuid4()
    db = DatabaseStub()
    template = FormTemplate(
        workspace_id=workspace_id,
        name="Student intake",
        schema_structure=[{"key": "name", "label": "Name", "type": "text", "required": False}],
        meta_data={"ai_architect": {"proposal_id": str(uuid4())}},
    )
    db.add(template)
    db.flush()
    proposal = AIChangeProposal(
        id=uuid4(),
        workspace_id=workspace_id,
        blueprint_id=uuid4(),
        proposal_type="forms",
        operation="update",
        title="Add parent phone",
        description="desc",
        rationale="why",
        generated_artifacts=[],
        applied_artifacts=[],
        target_artifacts=[{"type": "form", "id": str(template.id), "name": template.name}],
        before_state={"schema_structure": list(template.schema_structure)},
        after_state={
            "schema_structure": [
                *template.schema_structure,
                {"key": "parent_phone", "label": "Parent phone", "type": "text", "required": False},
            ]
        },
    )

    AIArchitectService.apply_proposal(db, proposal, actor_id=actor_id)
    event = next(item for item in db.items if isinstance(item, AIChangeEvent))
    assert event.before_state["schema_structure"][0]["key"] == "name"
    assert event.after_state["schema_structure"][-1]["key"] == "parent_phone"

    AIChangeRollbackService.rollback(db, event)
    assert template.schema_structure == proposal.before_state["schema_structure"]
    assert event.rollback_status == "rolled_back"


def test_provider_factory_defaults_to_deterministic(monkeypatch):
    monkeypatch.delenv("AI_ARCHITECT_PROVIDER", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.ai_architect import provider_factory

    monkeypatch.setattr(provider_factory.settings, "AI_ARCHITECT_PROVIDER", "")
    provider = provider_factory.build_architect_provider()

    assert provider.__class__.__name__ == "DeterministicArchitectProvider"


def test_live_provider_validates_structured_payload(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.ai_architect.provider_adapters import flatten_refinement_payload, validate_refinement_payload

    payload = validate_refinement_payload(
        {
            "kind": "proposal",
            "proposal": {
                "proposal_type": "forms",
                "operation": "update",
                "title": "Add parent phone",
                "description": "desc",
                "rationale": "why",
                "generated_artifacts": [],
                "target_artifacts": [{"type": "form", "id": "form-1", "name": "Student intake"}],
                "before_state": {"schema_structure": []},
                "after_state": {"schema_structure": [{"key": "parent_phone"}]},
                "risk_level": "low",
            },
        }
    )

    flattened = flatten_refinement_payload(payload)

    assert flattened["operation"] == "update"
    assert flattened["kind"] == "proposal"
