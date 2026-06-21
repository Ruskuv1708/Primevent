from datetime import date
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from core.database_connector import get_db
from core.workspace_resolver import resolve_workspace_id
from modules.access_control.enums import UserRole
from modules.access_control.security import get_current_user
from modules.access_control.permissions import PermissionService
from modules.reports.schemas import (
    ReportSource,
    ReportTypeCreateSchema,
    ReportTypeGoogleImportSchema,
    ReportTypeResponseSchema,
    ReportTypeUpdateSchema,
)
from modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["Reporting Engine"])


def _require_report_type_admin(current_user):
    if current_user.role not in {UserRole.SUPERADMIN, UserRole.SYSTEM_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Permission denied: insufficient privileges")


@router.get("/types", response_model=list[ReportTypeResponseSchema])
def list_report_types(
    include_inactive: bool = False,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_permission(current_user, "view_reports")
    target_workspace = resolve_workspace_id(current_user, workspace_id)
    return ReportService.list_report_types(
        db=db,
        workspace_id=target_workspace,
        include_inactive=include_inactive,
    )


@router.post("/types", response_model=ReportTypeResponseSchema)
def create_report_type(
    data: ReportTypeCreateSchema,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_permission(current_user, "view_reports")
    _require_report_type_admin(current_user)
    target_workspace = resolve_workspace_id(current_user, workspace_id)
    return ReportService.create_report_type(
        db=db,
        workspace_id=target_workspace,
        payload=data,
    )


@router.post("/types/import-file", response_model=ReportTypeResponseSchema)
async def import_report_type_from_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    source: Optional[ReportSource] = Form(None),
    is_active: bool = Form(True),
    header_row: int = Form(1),
    worksheet_name: Optional[str] = Form(None),
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_permission(current_user, "view_reports")
    _require_report_type_admin(current_user)
    target_workspace = resolve_workspace_id(current_user, workspace_id)
    return await ReportService.import_report_type_from_file(
        db=db,
        workspace_id=target_workspace,
        upload_file=file,
        name=name,
        description=description,
        source=source,
        is_active=is_active,
        header_row=header_row,
        worksheet_name=worksheet_name,
    )


@router.post("/types/import-google", response_model=ReportTypeResponseSchema)
def import_report_type_from_google(
    data: ReportTypeGoogleImportSchema,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_permission(current_user, "view_reports")
    _require_report_type_admin(current_user)
    target_workspace = resolve_workspace_id(current_user, workspace_id)
    return ReportService.import_report_type_from_google(
        db=db,
        workspace_id=target_workspace,
        payload=data,
    )


@router.put("/types/{report_type_id}", response_model=ReportTypeResponseSchema)
def update_report_type(
    report_type_id: UUID,
    data: ReportTypeUpdateSchema,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_permission(current_user, "view_reports")
    _require_report_type_admin(current_user)
    target_workspace = resolve_workspace_id(current_user, workspace_id)
    return ReportService.update_report_type(
        db=db,
        workspace_id=target_workspace,
        report_type_id=report_type_id,
        payload=data,
    )


@router.delete("/types/{report_type_id}")
def delete_report_type(
    report_type_id: UUID,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    PermissionService.require_permission(current_user, "view_reports")
    _require_report_type_admin(current_user)
    target_workspace = resolve_workspace_id(current_user, workspace_id)
    return ReportService.delete_report_type(
        db=db,
        workspace_id=target_workspace,
        report_type_id=report_type_id,
    )

@router.get("/requests/excel")
def download_requests_report(
    workspace_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """ Download all requests as .xlsx """
    PermissionService.require_permission(current_user, "view_reports")
    workspace_id = resolve_workspace_id(current_user, workspace_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be before or equal to date_to")
    
    # 1. Generate the Excel binary data
    file_stream = ReportService.generate_requests_excel(
        db,
        workspace_id,
        date_from=date_from,
        date_to=date_to,
    )
    
    # 2. Return as a Stream
    # Headers tell the browser this is an attachment to download
    headers = {
        "Content-Disposition": 'attachment; filename="requests_report.xlsx"'
    }
    
    return StreamingResponse(
        file_stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

@router.get("/users/excel")
def download_users_report(
    workspace_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """ Download employee list """
    PermissionService.require_permission(current_user, "view_reports")
    workspace_id = resolve_workspace_id(current_user, workspace_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be before or equal to date_to")
    file_stream = ReportService.generate_users_excel(
        db,
        workspace_id,
        date_from=date_from,
        date_to=date_to,
    )
    
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="employees.xlsx"'}
    )
    
