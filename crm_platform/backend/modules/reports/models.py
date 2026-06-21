from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.base_models import CRMBasedModel


class ReportType(CRMBasedModel):
    __tablename__ = "reports_report_types"
    __table_args__ = (
        Index("ix_reports_report_types_workspace_id", "workspace_id"),
        Index("ix_reports_report_types_workspace_name", "workspace_id", "name"),
    )

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String, nullable=False, default="requests")
    columns = Column(JSONB, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("access_workspaces.id"), nullable=False)