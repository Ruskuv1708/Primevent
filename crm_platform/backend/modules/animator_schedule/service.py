from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from modules.access_control.enums import UserRole
from modules.access_control.models import User
from modules.animator_schedule.models import AnimatorBooking, AnimatorUnavailability
from modules.animator_schedule.schemas import (
    AnimatorBookingCreate,
    AnimatorBookingUpdate,
    AnimatorUnavailabilityCreate,
    AnimatorUnavailabilityUpdate,
)


class AnimatorScheduleService:
    DEFAULT_COLORS = ("#4f6df5", "#22a06b", "#d9485f", "#d69e2e", "#805ad5", "#0f766e")

    @staticmethod
    def _combine(event_date: date, start_time: time) -> datetime:
        return datetime.combine(event_date, start_time)

    @classmethod
    def _interval(cls, booking: AnimatorBooking) -> tuple[datetime, datetime]:
        start = cls._combine(booking.event_date, booking.start_time)
        return start, start + timedelta(minutes=booking.duration_minutes)

    @classmethod
    def _overlaps(cls, first: AnimatorBooking, second: AnimatorBooking) -> bool:
        first_start, first_end = cls._interval(first)
        second_start, second_end = cls._interval(second)
        return first_start < second_end and first_end > second_start

    @staticmethod
    def _animator_ids(booking: AnimatorBooking) -> set[str]:
        return {str(item) for item in (booking.assigned_animator_ids or []) if item}

    @staticmethod
    def _serialize_user(user: User | object) -> dict:
        role = getattr(user, "role", "")
        return {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": getattr(user, "email", None),
            "role": getattr(role, "value", role),
        }

    @staticmethod
    def _animator_map(users: Iterable[User | object]) -> dict[str, dict]:
        return {str(user.id): AnimatorScheduleService._serialize_user(user) for user in users}

    @classmethod
    def _intervals_overlap(
        cls,
        event_date: date,
        start_time: time,
        duration_minutes: int,
        booking: AnimatorBooking,
    ) -> bool:
        first_start = cls._combine(event_date, start_time)
        first_end = first_start + timedelta(minutes=duration_minutes)
        second_start, second_end = cls._interval(booking)
        return first_start < second_end and first_end > second_start

    @classmethod
    def _booking_brief(cls, booking: AnimatorBooking) -> dict:
        start, end = cls._interval(booking)
        return {
            "id": str(booking.id),
            "event_type": getattr(booking, "event_type", None) or "order",
            "title": booking.title,
            "client_name": booking.client_name,
            "event_date": booking.event_date.isoformat(),
            "start_time": booking.start_time.strftime("%H:%M"),
            "end_time": end.time().strftime("%H:%M"),
            "program_name": booking.program_name,
        }

    @classmethod
    def _unavailability_interval(cls, item: AnimatorUnavailability) -> tuple[datetime, datetime]:
        start = cls._combine(item.unavailable_date, item.start_time)
        return start, start + timedelta(minutes=item.duration_minutes)

    @classmethod
    def _unavailability_overlaps(
        cls,
        event_date: date,
        start_time: time,
        duration_minutes: int,
        item: AnimatorUnavailability,
    ) -> bool:
        first_start = cls._combine(event_date, start_time)
        first_end = first_start + timedelta(minutes=duration_minutes)
        second_start, second_end = cls._unavailability_interval(item)
        return first_start < second_end and first_end > second_start

    @classmethod
    def _unavailability_brief(cls, item: AnimatorUnavailability) -> dict:
        start, end = cls._unavailability_interval(item)
        return {
            "id": str(item.id),
            "animator_id": str(item.animator_id),
            "unavailable_date": item.unavailable_date.isoformat(),
            "start_time": item.start_time.strftime("%H:%M"),
            "end_time": end.time().strftime("%H:%M"),
            "duration_minutes": item.duration_minutes,
            "reason": item.reason,
            "notes": item.notes,
        }

    @classmethod
    def _serialize_unavailability(cls, item: AnimatorUnavailability, user_map: dict[str, dict]) -> dict:
        brief = cls._unavailability_brief(item)
        return {
            **brief,
            "animator": user_map.get(str(item.animator_id)),
        }

    @classmethod
    def serialize_bookings(cls, bookings: list[AnimatorBooking], users: Iterable[User | object]) -> list[dict]:
        user_map = cls._animator_map(users)
        serialized = []
        for index, booking in enumerate(bookings):
            start, end = cls._interval(booking)
            assigned_ids = cls._animator_ids(booking)
            parallel = [
                other
                for other in bookings
                if other.id != booking.id and other.event_date == booking.event_date and cls._overlaps(booking, other)
            ]
            conflict_animator_ids = sorted(
                {
                    animator_id
                    for other in parallel
                    for animator_id in assigned_ids.intersection(cls._animator_ids(other))
                }
            )
            serialized.append(
                {
                    "id": str(booking.id),
                    "event_type": getattr(booking, "event_type", None) or "order",
                    "title": booking.title,
                    "client_name": booking.client_name,
                    "client_phone": booking.client_phone,
                    "event_date": booking.event_date.isoformat(),
                    "start_time": booking.start_time.strftime("%H:%M"),
                    "end_time": end.time().strftime("%H:%M"),
                    "duration_minutes": booking.duration_minutes,
                    "address": booking.address,
                    "program_name": booking.program_name,
                    "price": booking.price,
                    "prepayment": booking.prepayment,
                    "payment_status": booking.payment_status,
                    "inventory_notes": booking.inventory_notes,
                    "status": booking.status,
                    "color": booking.color or cls.DEFAULT_COLORS[index % len(cls.DEFAULT_COLORS)],
                    "notes": booking.notes,
                    "assigned_animator_ids": sorted(assigned_ids),
                    "assigned_animators": [
                        user_map[animator_id]
                        for animator_id in sorted(assigned_ids)
                        if animator_id in user_map
                    ],
                    "parallel_count": len(parallel),
                    "has_conflict": bool(conflict_animator_ids),
                    "conflict_animator_ids": conflict_animator_ids,
                    "starts_at_minutes": start.hour * 60 + start.minute,
                    "ends_at_minutes": end.hour * 60 + end.minute,
                }
            )
        return serialized

    @classmethod
    def list_animators(cls, db: Session, workspace_id: UUID) -> list[dict]:
        users = (
            db.query(User)
            .filter(
                User.workspace_id == workspace_id,
                User.is_active.is_(True),
                User.role != UserRole.SUPERADMIN,
            )
            .order_by(User.full_name.asc())
            .all()
        )
        return [
            cls._serialize_user(user)
            for user in users
        ]

    @classmethod
    def list_animator_availability(
        cls,
        db: Session,
        workspace_id: UUID,
        event_date: date,
        start_time: time,
        duration_minutes: int,
        exclude_booking_id: UUID | None = None,
    ) -> list[dict]:
        if duration_minutes < 15:
            raise HTTPException(status_code=422, detail="Duration must be at least 15 minutes")

        users = (
            db.query(User)
            .filter(
                User.workspace_id == workspace_id,
                User.is_active.is_(True),
                User.role != UserRole.SUPERADMIN,
            )
            .order_by(User.full_name.asc())
            .all()
        )
        bookings = (
            db.query(AnimatorBooking)
            .filter(AnimatorBooking.workspace_id == workspace_id, AnimatorBooking.event_date == event_date)
            .order_by(AnimatorBooking.start_time.asc())
            .all()
        )
        unavailable_items = (
            db.query(AnimatorUnavailability)
            .filter(
                AnimatorUnavailability.workspace_id == workspace_id,
                AnimatorUnavailability.unavailable_date == event_date,
            )
            .order_by(AnimatorUnavailability.start_time.asc())
            .all()
        )
        excluded_id = str(exclude_booking_id) if exclude_booking_id else None
        availability = []
        for user in users:
            user_id = str(user.id)
            conflicts = [
                booking
                for booking in bookings
                if str(booking.id) != excluded_id
                and user_id in cls._animator_ids(booking)
                and cls._intervals_overlap(event_date, start_time, duration_minutes, booking)
            ]
            unavailability_conflicts = [
                item
                for item in unavailable_items
                if str(item.animator_id) == user_id
                and cls._unavailability_overlaps(event_date, start_time, duration_minutes, item)
            ]
            availability.append(
                {
                    **cls._serialize_user(user),
                    "is_available": not conflicts and not unavailability_conflicts,
                    "conflict_count": len(conflicts) + len(unavailability_conflicts),
                    "conflicting_bookings": [cls._booking_brief(booking) for booking in conflicts],
                    "conflicting_unavailability": [
                        cls._unavailability_brief(item)
                        for item in unavailability_conflicts
                    ],
                }
            )
        return availability

    @classmethod
    def list_bookings(
        cls,
        db: Session,
        workspace_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        query = db.query(AnimatorBooking).filter(AnimatorBooking.workspace_id == workspace_id)
        if date_from:
            query = query.filter(AnimatorBooking.event_date >= date_from)
        if date_to:
            query = query.filter(AnimatorBooking.event_date <= date_to)
        bookings = query.order_by(AnimatorBooking.event_date.asc(), AnimatorBooking.start_time.asc()).all()
        users = db.query(User).filter(User.workspace_id == workspace_id).all()
        return cls.serialize_bookings(bookings, users)

    @classmethod
    def list_unavailability(
        cls,
        db: Session,
        workspace_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        animator_id: UUID | None = None,
    ) -> list[dict]:
        query = db.query(AnimatorUnavailability).filter(AnimatorUnavailability.workspace_id == workspace_id)
        if date_from:
            query = query.filter(AnimatorUnavailability.unavailable_date >= date_from)
        if date_to:
            query = query.filter(AnimatorUnavailability.unavailable_date <= date_to)
        if animator_id:
            query = query.filter(AnimatorUnavailability.animator_id == animator_id)

        items = query.order_by(AnimatorUnavailability.unavailable_date.asc(), AnimatorUnavailability.start_time.asc()).all()
        users = db.query(User).filter(User.workspace_id == workspace_id).all()
        user_map = cls._animator_map(users)
        return [cls._serialize_unavailability(item, user_map) for item in items]

    @staticmethod
    def _ensure_animator_exists(db: Session, workspace_id: UUID, animator_id: UUID) -> None:
        user = (
            db.query(User)
            .filter(User.workspace_id == workspace_id, User.id == animator_id, User.is_active.is_(True))
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="Animator was not found")

    @classmethod
    def create_unavailability(
        cls,
        db: Session,
        workspace_id: UUID,
        data: AnimatorUnavailabilityCreate,
    ) -> dict:
        cls._ensure_animator_exists(db, workspace_id, data.animator_id)
        item = AnimatorUnavailability(
            workspace_id=workspace_id,
            animator_id=data.animator_id,
            unavailable_date=data.unavailable_date,
            start_time=data.start_time,
            duration_minutes=data.duration_minutes,
            reason=data.reason,
            notes=data.notes,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        day_items = cls.list_unavailability(db, workspace_id, data.unavailable_date, data.unavailable_date, data.animator_id)
        return next(serialized for serialized in day_items if serialized["id"] == str(item.id))

    @staticmethod
    def _get_unavailability(db: Session, workspace_id: UUID, unavailability_id: UUID) -> AnimatorUnavailability:
        item = (
            db.query(AnimatorUnavailability)
            .filter(AnimatorUnavailability.workspace_id == workspace_id, AnimatorUnavailability.id == unavailability_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Animator unavailability was not found")
        return item

    @staticmethod
    def _unavailability_update_data(data: AnimatorUnavailabilityUpdate) -> dict:
        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)
        return data.dict(exclude_unset=True)

    @classmethod
    def update_unavailability(
        cls,
        db: Session,
        workspace_id: UUID,
        unavailability_id: UUID,
        data: AnimatorUnavailabilityUpdate,
    ) -> dict:
        item = cls._get_unavailability(db, workspace_id, unavailability_id)
        update_data = cls._unavailability_update_data(data)
        if update_data.get("animator_id"):
            cls._ensure_animator_exists(db, workspace_id, update_data["animator_id"])
        for field, value in update_data.items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        day_items = cls.list_unavailability(db, workspace_id, item.unavailable_date, item.unavailable_date, item.animator_id)
        return next(serialized for serialized in day_items if serialized["id"] == str(item.id))

    @classmethod
    def delete_unavailability(cls, db: Session, workspace_id: UUID, unavailability_id: UUID) -> dict:
        item = cls._get_unavailability(db, workspace_id, unavailability_id)
        db.delete(item)
        db.commit()
        return {"deleted": True, "id": str(unavailability_id)}

    @classmethod
    def create_booking(
        cls,
        db: Session,
        workspace_id: UUID,
        data: AnimatorBookingCreate,
    ) -> dict:
        animator_ids = [str(item) for item in data.assigned_animator_ids]
        if animator_ids:
            users = (
                db.query(User)
                .filter(User.workspace_id == workspace_id, User.id.in_(data.assigned_animator_ids))
                .all()
            )
            if len(users) != len(set(animator_ids)):
                raise HTTPException(status_code=404, detail="One or more animators were not found")

        booking = AnimatorBooking(
            workspace_id=workspace_id,
            event_type=data.event_type,
            title=data.title,
            client_name=data.client_name,
            client_phone=data.client_phone,
            event_date=data.event_date,
            start_time=data.start_time,
            duration_minutes=data.duration_minutes,
            address=data.address,
            program_name=data.program_name,
            price=data.price,
            prepayment=data.prepayment,
            payment_status=data.payment_status,
            inventory_notes=data.inventory_notes,
            status=data.status,
            color=data.color,
            notes=data.notes,
            assigned_animator_ids=animator_ids,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        day_bookings = cls.list_bookings(db, workspace_id, data.event_date, data.event_date)
        return next(item for item in day_bookings if item["id"] == str(booking.id))

    @staticmethod
    def _get_booking(db: Session, workspace_id: UUID, booking_id: UUID) -> AnimatorBooking:
        booking = (
            db.query(AnimatorBooking)
            .filter(AnimatorBooking.workspace_id == workspace_id, AnimatorBooking.id == booking_id)
            .first()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Animator booking was not found")
        return booking

    @staticmethod
    def _update_data(data: AnimatorBookingUpdate) -> dict:
        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)
        return data.dict(exclude_unset=True)

    @classmethod
    def update_booking(
        cls,
        db: Session,
        workspace_id: UUID,
        booking_id: UUID,
        data: AnimatorBookingUpdate,
    ) -> dict:
        booking = cls._get_booking(db, workspace_id, booking_id)
        update_data = cls._update_data(data)
        if "assigned_animator_ids" in update_data and update_data["assigned_animator_ids"] is not None:
            animator_ids = [str(item) for item in update_data["assigned_animator_ids"]]
            if animator_ids:
                users = (
                    db.query(User)
                    .filter(User.workspace_id == workspace_id, User.id.in_(update_data["assigned_animator_ids"]))
                    .all()
                )
                if len(users) != len(set(animator_ids)):
                    raise HTTPException(status_code=404, detail="One or more animators were not found")
            update_data["assigned_animator_ids"] = animator_ids

        for field, value in update_data.items():
            setattr(booking, field, value)

        db.commit()
        db.refresh(booking)
        day_bookings = cls.list_bookings(db, workspace_id, booking.event_date, booking.event_date)
        return next(item for item in day_bookings if item["id"] == str(booking.id))

    @classmethod
    def delete_booking(cls, db: Session, workspace_id: UUID, booking_id: UUID) -> dict:
        booking = cls._get_booking(db, workspace_id, booking_id)
        db.delete(booking)
        db.commit()
        return {"deleted": True, "id": str(booking_id)}
