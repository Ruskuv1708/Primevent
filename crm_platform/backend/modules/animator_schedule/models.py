from sqlalchemy import Column, Date, ForeignKey, Index, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.base_models import CRMBasedModel


class AnimatorBooking(CRMBasedModel):
    __tablename__ = "animator_bookings"
    __table_args__ = (
        Index("ix_animator_bookings_workspace_date_start", "workspace_id", "event_date", "start_time"),
    )

    event_type = Column(String, nullable=False, default="order", server_default="order")
    title = Column(String, nullable=False)
    client_name = Column(String, nullable=False)
    client_phone = Column(String, nullable=True)
    event_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    address = Column(Text, nullable=True)
    program_name = Column(String, nullable=True)
    price = Column(Integer, nullable=True)
    prepayment = Column(Integer, nullable=True)
    payment_status = Column(String, nullable=False, default="pending")
    inventory_notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="confirmed")
    color = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    assigned_animator_ids = Column(JSONB, nullable=False, default=list)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)


class AnimatorUnavailability(CRMBasedModel):
    __tablename__ = "animator_unavailability"
    __table_args__ = (
        Index("ix_animator_unavailability_workspace_date", "workspace_id", "unavailable_date", "start_time"),
        Index("ix_animator_unavailability_animator_date", "animator_id", "unavailable_date"),
    )

    animator_id = Column(UUID(as_uuid=True), ForeignKey("access_users.id"), nullable=False)
    unavailable_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)
