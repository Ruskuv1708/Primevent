from __future__ import annotations

from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnimatorBookingCreate(BaseModel):
    event_type: Literal["order", "rehearsal"] = "order"
    title: str = Field(min_length=1, max_length=180)
    client_name: str = Field(min_length=1, max_length=180)
    client_phone: str | None = Field(default=None, max_length=80)
    event_date: date
    start_time: time
    duration_minutes: int = Field(ge=15, le=720)
    address: str | None = None
    program_name: str | None = Field(default=None, max_length=180)
    price: int | None = Field(default=None, ge=0)
    prepayment: int | None = Field(default=None, ge=0)
    payment_status: str = Field(default="pending", max_length=80)
    inventory_notes: str | None = None
    assigned_animator_ids: list[UUID] = Field(default_factory=list)
    status: Literal["new", "confirmed", "completed", "cancelled"] = "confirmed"
    color: str | None = Field(default=None, max_length=40)
    notes: str | None = None


class AnimatorBookingUpdate(BaseModel):
    event_type: Literal["order", "rehearsal"] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    client_name: str | None = Field(default=None, min_length=1, max_length=180)
    client_phone: str | None = Field(default=None, max_length=80)
    event_date: date | None = None
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=720)
    address: str | None = None
    program_name: str | None = Field(default=None, max_length=180)
    price: int | None = Field(default=None, ge=0)
    prepayment: int | None = Field(default=None, ge=0)
    payment_status: str | None = Field(default=None, max_length=80)
    inventory_notes: str | None = None
    assigned_animator_ids: list[UUID] | None = None
    status: Literal["new", "confirmed", "completed", "cancelled"] | None = None
    color: str | None = Field(default=None, max_length=40)
    notes: str | None = None


class AnimatorUnavailabilityCreate(BaseModel):
    animator_id: UUID
    unavailable_date: date
    start_time: time
    duration_minutes: int = Field(ge=15, le=720)
    reason: str = Field(min_length=1, max_length=180)
    notes: str | None = None


class AnimatorUnavailabilityUpdate(BaseModel):
    animator_id: UUID | None = None
    unavailable_date: date | None = None
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=720)
    reason: str | None = Field(default=None, min_length=1, max_length=180)
    notes: str | None = None
