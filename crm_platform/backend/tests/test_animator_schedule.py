from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

import pytest


class FakeAnimatorBookingQuery:
    def __init__(self, bookings):
        self.bookings = bookings

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.bookings)

    def first(self):
        return self.bookings[0] if self.bookings else None


class FakeUserQuery:
    def __init__(self, users):
        self.users = users

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.users)


class FakeScheduleSession:
    def __init__(self, bookings, users=None, unavailability=None):
        self.bookings = bookings
        self.users = users or []
        self.unavailability = unavailability or []
        self.committed = False
        self.deleted = []

    def query(self, model):
        from modules.access_control.models import User
        from modules.animator_schedule.models import AnimatorBooking, AnimatorUnavailability

        if model is AnimatorBooking:
            return FakeAnimatorBookingQuery([booking for booking in self.bookings if booking not in self.deleted])
        if model is AnimatorUnavailability:
            return FakeAnimatorBookingQuery([item for item in self.unavailability if item not in self.deleted])
        if model is User:
            return FakeUserQuery(self.users)
        raise AssertionError(f"Unexpected model query: {model}")

    def commit(self):
        self.committed = True

    def add(self, item):
        from modules.animator_schedule.models import AnimatorBooking, AnimatorUnavailability

        if getattr(item, "id", None) is None:
            item.id = uuid4()
        if isinstance(item, AnimatorBooking):
            self.bookings.append(item)
            return
        if isinstance(item, AnimatorUnavailability):
            self.unavailability.append(item)
            return
        raise AssertionError(f"Unexpected added item: {item}")

    def refresh(self, booking):
        return None

    def delete(self, booking):
        self.deleted.append(booking)


def test_animator_schedule_marks_parallel_orders_and_animator_conflicts(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.animator_schedule.models import AnimatorBooking
    from modules.animator_schedule.service import AnimatorScheduleService

    workspace_id = uuid4()
    animator_id = uuid4()
    other_animator_id = uuid4()

    first = AnimatorBooking(
        id=uuid4(),
        workspace_id=workspace_id,
        title="Spider-Man party",
        client_name="Aziz",
        client_phone="+998901112233",
        event_date=date(2026, 6, 1),
        start_time=time(10, 0),
        duration_minutes=90,
        address="Tashkent",
        program_name="Spider-Man",
        assigned_animator_ids=[str(animator_id)],
    )
    second = AnimatorBooking(
        id=uuid4(),
        workspace_id=workspace_id,
        title="Princess party",
        client_name="Malika",
        client_phone="+998901112244",
        event_date=date(2026, 6, 1),
        start_time=time(10, 30),
        duration_minutes=60,
        address="Yunusabad",
        program_name="Princess",
        assigned_animator_ids=[str(animator_id), str(other_animator_id)],
    )
    parallel_only = AnimatorBooking(
        id=uuid4(),
        workspace_id=workspace_id,
        title="Bubble show",
        client_name="Nodir",
        client_phone="+998901112255",
        event_date=date(2026, 6, 1),
        start_time=time(10, 45),
        duration_minutes=45,
        address="Chilanzar",
        program_name="Bubble show",
        assigned_animator_ids=[str(uuid4())],
    )

    users = [
        SimpleNamespace(id=animator_id, full_name="Alex Animator", role="USER"),
        SimpleNamespace(id=other_animator_id, full_name="Masha Animator", role="USER"),
    ]

    serialized = AnimatorScheduleService.serialize_bookings(
        [first, second, parallel_only],
        users,
    )

    by_title = {item["title"]: item for item in serialized}
    assert by_title["Spider-Man party"]["parallel_count"] == 2
    assert by_title["Spider-Man party"]["has_conflict"] is True
    assert by_title["Princess party"]["conflict_animator_ids"] == [str(animator_id)]
    assert by_title["Bubble show"]["parallel_count"] == 2
    assert by_title["Bubble show"]["has_conflict"] is False


def test_update_animator_booking_changes_fields_and_recalculates_conflict(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.animator_schedule.models import AnimatorBooking
    from modules.animator_schedule.schemas import AnimatorBookingUpdate
    from modules.animator_schedule.service import AnimatorScheduleService

    workspace_id = uuid4()
    animator_id = uuid4()
    booking_id = uuid4()

    editable = AnimatorBooking(
        id=booking_id,
        workspace_id=workspace_id,
        title="Spider-Man party",
        client_name="Aziz",
        event_date=date(2026, 6, 1),
        start_time=time(10, 0),
        duration_minutes=60,
        assigned_animator_ids=[str(animator_id)],
    )
    existing = AnimatorBooking(
        id=uuid4(),
        workspace_id=workspace_id,
        title="Princess party",
        client_name="Malika",
        event_date=date(2026, 6, 1),
        start_time=time(12, 0),
        duration_minutes=60,
        assigned_animator_ids=[str(animator_id)],
    )
    db = FakeScheduleSession(
        [editable, existing],
        [SimpleNamespace(id=animator_id, full_name="Alex Animator", role="USER")],
    )

    updated = AnimatorScheduleService.update_booking(
        db,
        workspace_id,
        booking_id,
        AnimatorBookingUpdate(start_time=time(11, 30), duration_minutes=90, title="Updated party"),
    )

    assert db.committed is True
    assert editable.title == "Updated party"
    assert editable.start_time == time(11, 30)
    assert editable.duration_minutes == 90
    assert updated["has_conflict"] is True
    assert updated["conflict_animator_ids"] == [str(animator_id)]
    assert updated["end_time"] == "13:00"


def test_delete_animator_booking_removes_booking(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.animator_schedule.models import AnimatorBooking
    from modules.animator_schedule.service import AnimatorScheduleService

    workspace_id = uuid4()
    booking_id = uuid4()
    booking = AnimatorBooking(
        id=booking_id,
        workspace_id=workspace_id,
        title="Bubble show",
        client_name="Nodir",
        event_date=date(2026, 6, 1),
        start_time=time(14, 0),
        duration_minutes=45,
        assigned_animator_ids=[],
    )
    db = FakeScheduleSession([booking])

    result = AnimatorScheduleService.delete_booking(db, workspace_id, booking_id)

    assert result == {"deleted": True, "id": str(booking_id)}
    assert db.deleted == [booking]
    assert db.committed is True


def test_animator_schedule_router_exposes_update_and_delete_routes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.animator_schedule.router import router

    routes = {(route.path, method) for route in router.routes for method in route.methods}

    assert ("/animator-schedule/bookings/{booking_id}", "PATCH") in routes
    assert ("/animator-schedule/bookings/{booking_id}", "DELETE") in routes


def test_create_rehearsal_booking_assigns_animators_and_blocks_availability(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.animator_schedule.schemas import AnimatorBookingCreate
    from modules.animator_schedule.service import AnimatorScheduleService

    workspace_id = uuid4()
    animator_id = uuid4()
    db = FakeScheduleSession(
        [],
        [SimpleNamespace(id=animator_id, full_name="Alex Animator", email="alex@example.com", role="USER")],
    )

    created = AnimatorScheduleService.create_booking(
        db,
        workspace_id,
        AnimatorBookingCreate(
            event_type="rehearsal",
            title="Репетиция нового шоу",
            client_name="Prime Event",
            event_date=date(2026, 6, 1),
            start_time=time(9, 0),
            duration_minutes=120,
            program_name="Репетиция",
            assigned_animator_ids=[animator_id],
        ),
    )

    assert created["event_type"] == "rehearsal"
    assert created["assigned_animator_ids"] == [str(animator_id)]
    assert created["assigned_animators"][0]["full_name"] == "Alex Animator"

    availability = AnimatorScheduleService.list_animator_availability(
        db,
        workspace_id,
        date(2026, 6, 1),
        time(10, 0),
        60,
    )

    assert availability[0]["is_available"] is False
    assert availability[0]["conflicting_bookings"][0]["event_type"] == "rehearsal"
    assert availability[0]["conflicting_bookings"][0]["title"] == "Репетиция нового шоу"


def test_animator_availability_marks_busy_and_ignores_current_booking(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.animator_schedule.models import AnimatorBooking
    from modules.animator_schedule.service import AnimatorScheduleService

    workspace_id = uuid4()
    busy_animator_id = uuid4()
    free_animator_id = uuid4()
    current_booking_id = uuid4()

    current_booking = AnimatorBooking(
        id=current_booking_id,
        workspace_id=workspace_id,
        title="Current edited order",
        client_name="Current client",
        event_date=date(2026, 6, 1),
        start_time=time(9, 0),
        duration_minutes=60,
        assigned_animator_ids=[str(busy_animator_id)],
    )
    blocking_booking = AnimatorBooking(
        id=uuid4(),
        workspace_id=workspace_id,
        title="Blocking order",
        client_name="Aziz",
        event_date=date(2026, 6, 1),
        start_time=time(10, 30),
        duration_minutes=90,
        assigned_animator_ids=[str(busy_animator_id)],
    )
    adjacent_booking = AnimatorBooking(
        id=uuid4(),
        workspace_id=workspace_id,
        title="Adjacent order",
        client_name="Malika",
        event_date=date(2026, 6, 1),
        start_time=time(12, 0),
        duration_minutes=60,
        assigned_animator_ids=[str(free_animator_id)],
    )
    db = FakeScheduleSession(
        [current_booking, blocking_booking, adjacent_booking],
        [
            SimpleNamespace(id=busy_animator_id, full_name="Alex Animator", email="alex@example.com", role="USER"),
            SimpleNamespace(id=free_animator_id, full_name="Masha Animator", email="masha@example.com", role="USER"),
        ],
    )

    availability = AnimatorScheduleService.list_animator_availability(
        db,
        workspace_id,
        date(2026, 6, 1),
        time(10, 0),
        60,
        current_booking_id,
    )

    by_name = {item["full_name"]: item for item in availability}
    assert by_name["Alex Animator"]["is_available"] is False
    assert by_name["Alex Animator"]["conflict_count"] == 1
    assert by_name["Alex Animator"]["conflicting_bookings"][0]["title"] == "Blocking order"
    assert by_name["Masha Animator"]["is_available"] is True
    assert by_name["Masha Animator"]["conflict_count"] == 0


def test_animator_availability_marks_personal_unavailability(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.workflow import models as workflow_models  # noqa: F401
    from modules.animator_schedule.models import AnimatorUnavailability
    from modules.animator_schedule.service import AnimatorScheduleService

    workspace_id = uuid4()
    animator_id = uuid4()
    free_animator_id = uuid4()
    unavailability = AnimatorUnavailability(
        id=uuid4(),
        workspace_id=workspace_id,
        animator_id=animator_id,
        unavailable_date=date(2026, 6, 1),
        start_time=time(10, 0),
        duration_minutes=120,
        reason="Личные дела",
        notes="Недоступен до обеда",
    )
    db = FakeScheduleSession(
        [],
        [
            SimpleNamespace(id=animator_id, full_name="Alex Animator", email="alex@example.com", role="USER"),
            SimpleNamespace(id=free_animator_id, full_name="Masha Animator", email="masha@example.com", role="USER"),
        ],
        [unavailability],
    )

    availability = AnimatorScheduleService.list_animator_availability(
        db,
        workspace_id,
        date(2026, 6, 1),
        time(11, 0),
        60,
    )

    by_name = {item["full_name"]: item for item in availability}
    assert by_name["Alex Animator"]["is_available"] is False
    assert by_name["Alex Animator"]["conflict_count"] == 1
    assert by_name["Alex Animator"]["conflicting_unavailability"][0]["reason"] == "Личные дела"
    assert by_name["Masha Animator"]["is_available"] is True


def test_animator_unavailability_target_permissions(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from fastapi import HTTPException
    from modules.access_control.enums import UserRole
    from modules.animator_schedule.router import _ensure_unavailability_target_allowed

    own_id = uuid4()
    other_id = uuid4()

    animator_user = SimpleNamespace(id=own_id, role=UserRole.USER, email="animator@example.com")
    manager_user = SimpleNamespace(id=uuid4(), role=UserRole.MANAGER, email="manager@example.com")

    _ensure_unavailability_target_allowed(animator_user, own_id)
    _ensure_unavailability_target_allowed(manager_user, other_id)

    with pytest.raises(HTTPException) as error:
        _ensure_unavailability_target_allowed(animator_user, other_id)
    assert error.value.status_code == 403


def test_animator_schedule_router_exposes_availability_route(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.animator_schedule.router import router

    routes = {(route.path, method) for route in router.routes for method in route.methods}

    assert ("/animator-schedule/animators/availability", "GET") in routes


def test_animator_schedule_router_exposes_unavailability_routes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.animator_schedule.router import router

    routes = {(route.path, method) for route in router.routes for method in route.methods}

    assert ("/animator-schedule/unavailability", "GET") in routes
    assert ("/animator-schedule/unavailability", "POST") in routes
    assert ("/animator-schedule/unavailability/{unavailability_id}", "DELETE") in routes


def test_list_animators_serializes_active_workspace_users(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from modules.animator_schedule.service import AnimatorScheduleService

    workspace_id = uuid4()
    animator_id = uuid4()
    db = FakeScheduleSession(
        [],
        [SimpleNamespace(id=animator_id, full_name="Alex Animator", email="alex@example.com", role="USER")],
    )

    assert AnimatorScheduleService.list_animators(db, workspace_id) == [
        {
            "id": str(animator_id),
            "full_name": "Alex Animator",
            "email": "alex@example.com",
            "role": "USER",
        }
    ]


def test_animator_schedule_mutations_require_admin_role(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("SECRET_KEY", "test")
    from fastapi import HTTPException
    from modules.access_control.enums import UserRole
    from modules.animator_schedule.router import create_booking, delete_booking, update_booking
    from modules.animator_schedule.schemas import AnimatorBookingCreate, AnimatorBookingUpdate

    current_user = SimpleNamespace(role=UserRole.MANAGER, email="manager@example.com")
    create_data = AnimatorBookingCreate(
        title="Test order",
        client_name="Client",
        event_date=date(2026, 6, 1),
        start_time=time(10, 0),
        duration_minutes=60,
    )

    with pytest.raises(HTTPException) as create_error:
        create_booking(create_data, db=object(), current_user=current_user)
    assert create_error.value.status_code == 403

    with pytest.raises(HTTPException) as update_error:
        update_booking(uuid4(), AnimatorBookingUpdate(title="Updated"), db=object(), current_user=current_user)
    assert update_error.value.status_code == 403

    with pytest.raises(HTTPException) as delete_error:
        delete_booking(uuid4(), db=object(), current_user=current_user)
    assert delete_error.value.status_code == 403


def test_animator_schedule_is_default_enabled_functional_module():
    from modules.module_registry.definitions import DEFAULT_ENABLED_MODULE_IDS
    from modules.module_registry.service import ModuleService

    assert "animator_schedule" in DEFAULT_ENABLED_MODULE_IDS

    definition = next(item for item in ModuleService.list_module_definitions() if item.id == "animator_schedule")
    assert definition.category == "functional"
    assert definition.route_path == "/animator-schedule"
    assert "schedule" in " ".join(definition.capabilities).lower()
    assert definition.dependencies == ()
    assert {synergy.module_id for synergy in definition.synergies} >= {"registry", "workflow"}

    assert ModuleService.list_module_manifests(["animator_events", "animator_schedule"]) == []
