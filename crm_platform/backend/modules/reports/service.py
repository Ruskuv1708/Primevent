from __future__ import annotations

import csv
import re
from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO, StringIO
from tempfile import SpooledTemporaryFile
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import requests as http_requests
from fastapi import HTTPException, UploadFile
from openpyxl import Workbook, load_workbook
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import settings
from core.export_safety import safe_spreadsheet_cell, safe_spreadsheet_row

# Import the models we want to report on
from modules.workflow.models import Request
from modules.access_control.models import User
from modules.access_control.enums import UserRole
from modules.reports.models import ReportType
from modules.reports.schemas import (
    ReportSource,
    ReportTypeColumnSchema,
    ReportTypeCreateSchema,
    ReportTypeGoogleImportSchema,
    ReportTypeUpdateSchema,
)

class ReportService:
    _SOURCE_SIGNATURES: dict[str, set[str]] = {
        "requests": {
            "title",
            "status",
            "priority",
            "department_id",
            "assigned_to_id",
            "assignee_name",
            "description",
            "created_at",
            "updated_at",
        },
        "users": {
            "full_name",
            "email",
            "role",
            "is_active",
            "department_id",
            "created_at",
            "updated_at",
        },
        "clients": {
            "full_name",
            "first_name",
            "last_name",
            "email",
            "phone",
            "company_name",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        },
        "companies": {
            "name",
            "registration_number",
            "email",
            "phone",
            "address",
            "created_at",
            "updated_at",
        },
    }
    IMPORT_CHUNK_SIZE = 1024 * 1024
    MAX_IMPORT_BYTES = settings.MAX_IMPORT_MB * 1024 * 1024

    @staticmethod
    def _resolve_period(date_from: date | None, date_to: date | None):
        start_dt = None
        end_dt = None
        if date_from:
            start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        if date_to:
            end_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        return start_dt, end_dt

    @staticmethod
    def _clean_header_value(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @staticmethod
    def _to_column_key(label: str, fallback: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", label.strip().lower()).strip("_")
        if not normalized:
            normalized = fallback
        return normalized[:120]

    @staticmethod
    def _extract_headers_from_csv(
        csv_text: str,
        header_row: int,
    ) -> list[str]:
        reader = csv.reader(StringIO(csv_text))
        row_count = 0
        target_row: list[str] | None = None
        for row_count, row in enumerate(reader, start=1):
            if row_count == header_row:
                target_row = row
                break

        if row_count == 0:
            raise HTTPException(status_code=400, detail="Imported file is empty")
        if target_row is None:
            raise HTTPException(
                status_code=400,
                detail=f"Header row {header_row} is outside of file bounds ({row_count} rows)",
            )

        header_values = [ReportService._clean_header_value(item) for item in target_row]
        headers = [item for item in header_values if item]
        if not headers:
            raise HTTPException(status_code=400, detail="Selected header row does not contain any column names")
        return headers

    @staticmethod
    def _extract_headers_from_xlsx(
        file_bytes: bytes,
        header_row: int,
        worksheet_name: str | None = None,
    ) -> list[str]:
        try:
            workbook = load_workbook(filename=BytesIO(file_bytes), read_only=True, data_only=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {exc}") from exc

        try:
            worksheet = workbook[worksheet_name] if worksheet_name else workbook.active
        except KeyError as exc:
            workbook.close()
            raise HTTPException(status_code=400, detail=f"Worksheet not found: {worksheet_name}") from exc

        max_row = worksheet.max_row or 0
        if header_row > max_row:
            workbook.close()
            raise HTTPException(
                status_code=400,
                detail=f"Header row {header_row} is outside of worksheet bounds ({max_row} rows)",
            )

        row_values = next(
            worksheet.iter_rows(min_row=header_row, max_row=header_row, values_only=True),
            None,
        )
        workbook.close()
        if row_values is None:
            raise HTTPException(status_code=400, detail="Selected header row is empty")

        header_values = [ReportService._clean_header_value(item) for item in row_values]
        headers = [item for item in header_values if item]
        if not headers:
            raise HTTPException(status_code=400, detail="Selected header row does not contain any column names")
        return headers

    @staticmethod
    def _build_columns_from_headers(headers: list[str]) -> list[ReportTypeColumnSchema]:
        columns: list[ReportTypeColumnSchema] = []
        used_keys: set[str] = set()
        for index, header in enumerate(headers, start=1):
            fallback = f"column_{index}"
            base_key = ReportService._to_column_key(header, fallback)
            key = base_key
            suffix = 2
            while key.lower() in used_keys:
                key = f"{base_key}_{suffix}"[:120]
                suffix += 1
            used_keys.add(key.lower())
            columns.append(ReportTypeColumnSchema(key=key, label=header))

        if not columns:
            raise HTTPException(status_code=400, detail="No report columns were detected")
        return columns

    @staticmethod
    async def _read_upload_limited(upload_file: UploadFile) -> bytes:
        chunks: list[bytes] = []
        total_size = 0
        while True:
            chunk = await upload_file.read(ReportService.IMPORT_CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > ReportService.MAX_IMPORT_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Imported file exceeds max size of {settings.MAX_IMPORT_MB} MB",
                )
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _response_text_limited(response) -> str:
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > ReportService.MAX_IMPORT_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Google Sheet export exceeds max size of {settings.MAX_IMPORT_MB} MB",
                    )
            except ValueError:
                pass

        chunks: list[bytes] = []
        total_size = 0
        for chunk in response.iter_content(chunk_size=ReportService.IMPORT_CHUNK_SIZE):
            if not chunk:
                continue
            total_size += len(chunk)
            if total_size > ReportService.MAX_IMPORT_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Google Sheet export exceeds max size of {settings.MAX_IMPORT_MB} MB",
                )
            chunks.append(chunk)

        encoding = response.encoding or "utf-8"
        return b"".join(chunks).decode(encoding, errors="replace")

    @staticmethod
    def _infer_source(columns: list[ReportTypeColumnSchema]) -> ReportSource:
        if not columns:
            return "custom"

        keys = {column.key.strip().lower() for column in columns if column.key.strip()}
        if not keys:
            return "custom"

        best_source = "custom"
        best_score = 0
        tie = False
        for source, signature in ReportService._SOURCE_SIGNATURES.items():
            score = len(keys.intersection(signature))
            if score > best_score:
                best_source = source
                best_score = score
                tie = False
            elif score == best_score and score > 0:
                tie = True

        if tie or best_score == 0:
            return "custom"
        return best_source  # type: ignore[return-value]

    @staticmethod
    def _source_or_infer(
        source: ReportSource | None,
        columns: list[ReportTypeColumnSchema],
    ) -> ReportSource:
        return source or ReportService._infer_source(columns)

    @staticmethod
    def generate_requests_excel(
        db: Session,
        workspace_id,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        """
        Generates an Excel file containing all Requests for this company.
        """
        start_dt, end_dt = ReportService._resolve_period(date_from, date_to)
        # 1. Fetch Data (SQLAlchemy)
        # We join with User to get the actual name of the assignee
        query = db.query(
            Request.title,
            Request.status,
            Request.priority,
            Request.created_at,
            User.full_name.label("assignee_name")
        ).outerjoin(User, Request.assigned_to_id == User.id)\
         .filter(Request.workspace_id == workspace_id)
        if start_dt:
            query = query.filter(Request.created_at >= start_dt)
        if end_dt:
            query = query.filter(Request.created_at < end_dt)

        total = query.count()
        if total > settings.MAX_EXPORT_ROWS:
            raise HTTPException(
                status_code=413,
                detail=f"Export exceeds max row limit ({settings.MAX_EXPORT_ROWS})"
            )
        # 2. Stream rows into a write-only workbook to avoid large memory spikes
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet(title="Requests_Export")
        sheet.append(["Title", "Status", "Priority", "Created Date", "Assigned To"])

        for row in query.yield_per(1000):
            sheet.append(safe_spreadsheet_row([
                row.title,
                row.status.value,
                row.priority.value,
                row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else "",
                row.assignee_name if row.assignee_name else "Unassigned",
            ]))

        output = SpooledTemporaryFile(max_size=settings.EXPORT_SPOOL_MAX_MB * 1024 * 1024)
        workbook.save(output)
        output.seek(0)
        return output

    @staticmethod
    def _normalize_columns(columns: list[ReportTypeColumnSchema] | None) -> list[dict]:
        if not columns:
            raise HTTPException(status_code=400, detail="At least one report column is required")

        normalized_columns: list[dict] = []
        seen_keys: set[str] = set()

        for column in columns:
            key = column.key.strip()
            label = column.label.strip()
            if not key or not label:
                raise HTTPException(status_code=400, detail="Each column must include key and label")

            normalized_key = key.lower()
            if normalized_key in seen_keys:
                raise HTTPException(status_code=400, detail=f"Duplicate report column key: {key}")
            seen_keys.add(normalized_key)

            formula = column.formula.strip() if column.formula else None
            fmt = column.format.strip() if column.format else None
            normalized_columns.append(
                {
                    "key": key,
                    "label": label,
                    "formula": formula or None,
                    "format": fmt or None,
                }
            )

        return normalized_columns

    @staticmethod
    def _serialize_report_type(report_type: ReportType) -> dict:
        raw_columns = report_type.columns if isinstance(report_type.columns, list) else []
        normalized_columns: list[dict] = []
        for item in raw_columns:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            label = str(item.get("label") or "").strip()
            if not key or not label:
                continue
            formula = item.get("formula")
            fmt = item.get("format")
            normalized_columns.append(
                {
                    "key": key,
                    "label": label,
                    "formula": str(formula).strip() if isinstance(formula, str) and formula.strip() else None,
                    "format": str(fmt).strip() if isinstance(fmt, str) and fmt.strip() else None,
                }
            )

        return {
            "id": str(report_type.id),
            "name": report_type.name,
            "description": report_type.description,
            "source": report_type.source,
            "columns": normalized_columns,
            "is_active": report_type.is_active,
            "workspace_id": str(report_type.workspace_id),
            "created_at": report_type.created_at.isoformat() if report_type.created_at else None,
            "updated_at": report_type.updated_at.isoformat() if report_type.updated_at else None,
        }

    @staticmethod
    def list_report_types(
        db: Session,
        workspace_id: UUID,
        include_inactive: bool = False,
    ) -> list[dict]:
        query = db.query(ReportType).filter(ReportType.workspace_id == workspace_id)
        if not include_inactive:
            query = query.filter(ReportType.is_active.is_(True))
        report_types = query.order_by(ReportType.updated_at.desc(), ReportType.created_at.desc()).all()
        return [ReportService._serialize_report_type(item) for item in report_types]

    @staticmethod
    def create_report_type(
        db: Session,
        workspace_id: UUID,
        payload: ReportTypeCreateSchema,
    ) -> dict:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Report type name is required")

        existing = (
            db.query(ReportType)
            .filter(
                ReportType.workspace_id == workspace_id,
                func.lower(ReportType.name) == name.lower(),
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Report type with this name already exists")

        report_type = ReportType(
            name=name,
            description=payload.description.strip() if payload.description else None,
            source=payload.source,
            columns=ReportService._normalize_columns(payload.columns),
            is_active=payload.is_active,
            workspace_id=workspace_id,
        )
        db.add(report_type)
        db.commit()
        db.refresh(report_type)
        return ReportService._serialize_report_type(report_type)

    @staticmethod
    def update_report_type(
        db: Session,
        workspace_id: UUID,
        report_type_id: UUID,
        payload: ReportTypeUpdateSchema,
    ) -> dict:
        report_type = (
            db.query(ReportType)
            .filter(
                ReportType.id == report_type_id,
                ReportType.workspace_id == workspace_id,
            )
            .first()
        )
        if not report_type:
            raise HTTPException(status_code=404, detail="Report type not found")

        if payload.name is not None:
            name = payload.name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="Report type name cannot be empty")
            existing = (
                db.query(ReportType)
                .filter(
                    ReportType.workspace_id == workspace_id,
                    func.lower(ReportType.name) == name.lower(),
                    ReportType.id != report_type_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(status_code=409, detail="Report type with this name already exists")
            report_type.name = name

        if payload.description is not None:
            report_type.description = payload.description.strip() or None

        if payload.source is not None:
            report_type.source = payload.source

        if payload.columns is not None:
            report_type.columns = ReportService._normalize_columns(payload.columns)

        if payload.is_active is not None:
            report_type.is_active = payload.is_active

        db.commit()
        db.refresh(report_type)
        return ReportService._serialize_report_type(report_type)

    @staticmethod
    def delete_report_type(
        db: Session,
        workspace_id: UUID,
        report_type_id: UUID,
    ) -> dict:
        report_type = (
            db.query(ReportType)
            .filter(
                ReportType.id == report_type_id,
                ReportType.workspace_id == workspace_id,
            )
            .first()
        )
        if not report_type:
            raise HTTPException(status_code=404, detail="Report type not found")

        db.delete(report_type)
        db.commit()
        return {"message": "Report type deleted"}

    @staticmethod
    def _extract_google_sheet_id(google_sheet_url: str) -> str:
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_sheet_url)
        if not match:
            raise HTTPException(status_code=400, detail="Invalid Google Sheets URL")
        return match.group(1)

    @staticmethod
    def _extract_gid_from_google_url(google_sheet_url: str) -> str | None:
        parsed = urlparse(google_sheet_url)
        query = parse_qs(parsed.query)
        if query.get("gid") and query["gid"][0].strip():
            return query["gid"][0].strip()

        if parsed.fragment:
            fragment_params = parse_qs(parsed.fragment)
            if fragment_params.get("gid") and fragment_params["gid"][0].strip():
                return fragment_params["gid"][0].strip()

            fragment_match = re.search(r"gid=([0-9]+)", parsed.fragment)
            if fragment_match:
                return fragment_match.group(1)
        return None

    @staticmethod
    async def import_report_type_from_file(
        db: Session,
        workspace_id: UUID,
        *,
        upload_file: UploadFile,
        name: str,
        description: str | None,
        source: ReportSource | None,
        is_active: bool,
        header_row: int,
        worksheet_name: str | None,
    ) -> dict:
        filename = (upload_file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=400, detail="Uploaded file name is missing")

        file_bytes = await ReportService._read_upload_limited(upload_file)
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        trimmed_worksheet = worksheet_name.strip() if worksheet_name else None
        if extension == "csv":
            decoded_text = None
            for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
                try:
                    decoded_text = file_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded_text is None:
                raise HTTPException(status_code=400, detail="Failed to decode CSV file")
            headers = ReportService._extract_headers_from_csv(decoded_text, header_row)
        elif extension in {"xlsx", "xlsm", "xltx", "xltm"}:
            headers = ReportService._extract_headers_from_xlsx(
                file_bytes=file_bytes,
                header_row=header_row,
                worksheet_name=trimmed_worksheet,
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or XLSX")

        columns = ReportService._build_columns_from_headers(headers)
        create_payload = ReportTypeCreateSchema(
            name=name,
            description=description,
            source=ReportService._source_or_infer(source, columns),
            columns=columns,
            is_active=is_active,
        )
        return ReportService.create_report_type(
            db=db,
            workspace_id=workspace_id,
            payload=create_payload,
        )

    @staticmethod
    def import_report_type_from_google(
        db: Session,
        workspace_id: UUID,
        payload: ReportTypeGoogleImportSchema,
    ) -> dict:
        sheet_id = ReportService._extract_google_sheet_id(payload.google_sheet_url)
        gid = payload.worksheet_gid.strip() if payload.worksheet_gid else ReportService._extract_gid_from_google_url(payload.google_sheet_url)
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        if gid:
            export_url = f"{export_url}&gid={gid}"

        try:
            response = http_requests.get(export_url, timeout=25, stream=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to fetch Google Sheet: {exc}") from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=400,
                detail=f"Google Sheets export failed with status {response.status_code}",
            )

        csv_text = ReportService._response_text_limited(response)
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="Google Sheet returned an empty file")

        headers = ReportService._extract_headers_from_csv(
            csv_text=csv_text,
            header_row=payload.header_row,
        )
        columns = ReportService._build_columns_from_headers(headers)

        create_payload = ReportTypeCreateSchema(
            name=payload.name,
            description=payload.description,
            source=ReportService._source_or_infer(payload.source, columns),
            columns=columns,
            is_active=payload.is_active,
        )
        return ReportService.create_report_type(
            db=db,
            workspace_id=workspace_id,
            payload=create_payload,
        )

    @staticmethod
    def generate_users_excel(
        db: Session,
        workspace_id,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        """
        Another example: Export List of Employees
        """
        start_dt, end_dt = ReportService._resolve_period(date_from, date_to)
        user_query = db.query(User).filter(User.workspace_id == workspace_id)
        if start_dt:
            user_query = user_query.filter(User.created_at >= start_dt)
        if end_dt:
            user_query = user_query.filter(User.created_at < end_dt)
        total = user_query.count()
        if total > settings.MAX_EXPORT_ROWS:
            raise HTTPException(
                status_code=413,
                detail=f"Export exceeds max row limit ({settings.MAX_EXPORT_ROWS})"
            )
        admin_roles = {UserRole.SUPERADMIN, UserRole.SYSTEM_ADMIN, UserRole.ADMIN}

        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet(title="Employees")
        sheet.append(["Name", "Email", "Role", "Admin"])
        for user in user_query.yield_per(1000):
            role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
            is_admin = (
                user.role in admin_roles
                if hasattr(user.role, "value")
                else str(user.role).upper() in {r.value for r in admin_roles}
            )
            sheet.append(safe_spreadsheet_row([user.full_name, user.email, role_value, is_admin]))

        output = SpooledTemporaryFile(max_size=settings.EXPORT_SPOOL_MAX_MB * 1024 * 1024)
        workbook.save(output)
        output.seek(0)
        return output
