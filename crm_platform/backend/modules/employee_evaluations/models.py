from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.base_models import CRMBasedModel


class EmployeeEvaluation(CRMBasedModel):
    __tablename__ = "employee_evaluations"
    __table_args__ = (
        Index("ix_employee_evaluations_workspace_employee", "workspace_id", "employee_id"),
        Index("ix_employee_evaluations_workspace_period", "workspace_id", "period_label"),
    )

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("access_users.id"), nullable=False)
    evaluator_id = Column(UUID(as_uuid=True), ForeignKey("access_users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    score = Column(Integer, nullable=False)
    period_label = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
