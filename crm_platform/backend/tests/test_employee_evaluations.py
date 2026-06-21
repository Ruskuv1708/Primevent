from types import SimpleNamespace
from uuid import uuid4

import pytest


class FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return [item for item in self.items if not getattr(item, "_deleted", False)]

    def first(self):
        items = self.all()
        return items[0] if items else None


class FakeEvaluationSession:
    def __init__(self, evaluations=None, users=None):
        self.evaluations = evaluations or []
        self.users = users or []
        self.committed = False
        self.deleted = []

    def query(self, model):
        from modules.access_control.models import User
        from modules.employee_evaluations.models import EmployeeEvaluation

        if model is EmployeeEvaluation:
            return FakeQuery(self.evaluations)
        if model is User:
            return FakeQuery(self.users)
        raise AssertionError(f"Unexpected model query: {model}")

    def add(self, item):
        from modules.employee_evaluations.models import EmployeeEvaluation

        if getattr(item, "id", None) is None:
            item.id = uuid4()
        if isinstance(item, EmployeeEvaluation):
            self.evaluations.append(item)
            return
        raise AssertionError(f"Unexpected added item: {item}")

    def commit(self):
        self.committed = True

    def refresh(self, item):
        return None

    def delete(self, item):
        item._deleted = True
        self.deleted.append(item)


def test_employee_evaluations_module_is_default_enabled_functional_module():
    from modules.module_registry.definitions import DEFAULT_ENABLED_MODULE_IDS
    from modules.module_registry.service import ModuleService

    definitions = {definition.id: definition for definition in ModuleService.list_module_definitions()}
    module = definitions["employee_evaluations"]

    assert module.category == "functional"
    assert module.route_path == "/employee-evaluations"
    assert module.default_enabled is True
    assert "employee_evaluations" in DEFAULT_ENABLED_MODULE_IDS
    assert "kpi" in " ".join(module.capabilities).lower()
    assert module.dependencies == ()
    assert {synergy.module_id for synergy in module.synergies} >= {"animator_schedule", "reports"}


def test_employee_evaluation_score_must_be_between_one_and_ten():
    from pydantic import ValidationError

    from modules.employee_evaluations.schemas import EmployeeEvaluationCreate

    with pytest.raises(ValidationError):
        EmployeeEvaluationCreate(
            employee_id=uuid4(),
            title="Пунктуальность",
            score=11,
        )


def test_create_employee_evaluation_records_individual_kpi_for_employee(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.employee_evaluations.schemas import EmployeeEvaluationCreate
    from modules.employee_evaluations.service import EmployeeEvaluationService

    workspace_id = uuid4()
    employee_id = uuid4()
    evaluator_id = uuid4()
    employee = SimpleNamespace(id=employee_id, full_name="Azamat Animator", email="azamat@example.com", role="USER", is_active=True)
    evaluator = SimpleNamespace(id=evaluator_id, full_name="Admin", email="admin@example.com", role="ADMIN", is_active=True)
    db = FakeEvaluationSession(users=[employee, evaluator])

    created = EmployeeEvaluationService.create_evaluation(
        db,
        workspace_id,
        evaluator_id,
        EmployeeEvaluationCreate(
            employee_id=employee_id,
            title="Пунктуальность",
            description="Приходит вовремя на заказы и репетиции",
            score=9,
            period_label="Июнь 2026",
            comment="Стабильно вовремя",
        ),
    )

    assert db.committed is True
    assert created["employee"]["full_name"] == "Azamat Animator"
    assert created["evaluator"]["full_name"] == "Admin"
    assert created["title"] == "Пунктуальность"
    assert created["score"] == 9
    assert created["period_label"] == "Июнь 2026"


def test_list_employee_evaluation_summary_calculates_average_score(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.employee_evaluations.models import EmployeeEvaluation
    from modules.employee_evaluations.service import EmployeeEvaluationService

    workspace_id = uuid4()
    employee_id = uuid4()
    other_employee_id = uuid4()
    employee = SimpleNamespace(id=employee_id, full_name="Azamat Animator", email="azamat@example.com", role="USER", is_active=True)
    other_employee = SimpleNamespace(id=other_employee_id, full_name="Other Animator", email="other@example.com", role="USER", is_active=True)
    admin = SimpleNamespace(id=uuid4(), full_name="Admin", email="admin@example.com", role="ADMIN", is_active=True)
    evaluations = [
        EmployeeEvaluation(
            id=uuid4(),
            workspace_id=workspace_id,
            employee_id=employee_id,
            evaluator_id=admin.id,
            title="Пунктуальность",
            score=8,
        ),
        EmployeeEvaluation(
            id=uuid4(),
            workspace_id=workspace_id,
            employee_id=employee_id,
            evaluator_id=admin.id,
            title="Коммуникация",
            score=10,
        ),
    ]
    db = FakeEvaluationSession(evaluations=evaluations, users=[employee, other_employee, admin])

    summary = EmployeeEvaluationService.list_employee_summaries(db, workspace_id)
    by_name = {item["full_name"]: item for item in summary}

    assert by_name["Azamat Animator"]["evaluation_count"] == 2
    assert by_name["Azamat Animator"]["average_score"] == 9
    assert by_name["Other Animator"]["evaluation_count"] == 0
    assert by_name["Other Animator"]["average_score"] is None


def test_employee_evaluation_stats_calculate_team_score_and_rankings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.employee_evaluations.models import EmployeeEvaluation
    from modules.employee_evaluations.service import EmployeeEvaluationService

    workspace_id = uuid4()
    azamat_id = uuid4()
    alexey_id = uuid4()
    empty_id = uuid4()
    admin_id = uuid4()
    users = [
      SimpleNamespace(id=azamat_id, full_name="Azamat", email="azamat@example.com", role="USER", is_active=True),
      SimpleNamespace(id=alexey_id, full_name="Alexey", email="alexey@example.com", role="USER", is_active=True),
      SimpleNamespace(id=empty_id, full_name="No KPI", email="empty@example.com", role="USER", is_active=True),
      SimpleNamespace(id=admin_id, full_name="Admin", email="admin@example.com", role="ADMIN", is_active=True),
    ]
    evaluations = [
        EmployeeEvaluation(id=uuid4(), workspace_id=workspace_id, employee_id=azamat_id, evaluator_id=admin_id, title="Пунктуальность", score=10),
        EmployeeEvaluation(id=uuid4(), workspace_id=workspace_id, employee_id=azamat_id, evaluator_id=admin_id, title="Команда", score=8),
        EmployeeEvaluation(id=uuid4(), workspace_id=workspace_id, employee_id=alexey_id, evaluator_id=admin_id, title="Пунктуальность", score=7),
        EmployeeEvaluation(id=uuid4(), workspace_id=workspace_id, employee_id=alexey_id, evaluator_id=admin_id, title="Команда", score=7),
        EmployeeEvaluation(id=uuid4(), workspace_id=uuid4(), employee_id=alexey_id, evaluator_id=admin_id, title="Other workspace", score=10),
    ]
    db = FakeEvaluationSession(evaluations=evaluations, users=users)

    stats = EmployeeEvaluationService.get_team_stats(db, workspace_id)

    assert stats["team_total_score"] == 32
    assert stats["team_average_score"] == 8
    assert stats["employee_count"] == 4
    assert stats["evaluated_employee_count"] == 2
    assert stats["evaluation_count"] == 4
    assert stats["top_employee"]["full_name"] == "Azamat"
    assert [item["full_name"] for item in stats["rankings"][:3]] == ["Azamat", "Alexey", "Admin"]
    assert stats["rankings"][0]["rank"] == 1
    assert stats["rankings"][0]["total_score"] == 18
    assert stats["rankings"][0]["average_score"] == 9
    assert stats["rankings"][1]["rank"] == 2
    assert stats["rankings"][1]["total_score"] == 14
    assert stats["rankings"][-1]["full_name"] == "No KPI"
    assert stats["rankings"][-1]["rank"] is None


def test_employee_evaluation_router_exposes_admin_mutation_routes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.employee_evaluations.router import router

    routes = {(route.path, method) for route in router.routes for method in route.methods}

    assert ("/employee-evaluations", "GET") in routes
    assert ("/employee-evaluations/employees", "GET") in routes
    assert ("/employee-evaluations", "POST") in routes
    assert ("/employee-evaluations/stats", "GET") in routes
    assert ("/employee-evaluations/{evaluation_id}", "PATCH") in routes
    assert ("/employee-evaluations/{evaluation_id}", "DELETE") in routes
