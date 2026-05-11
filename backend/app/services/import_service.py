from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionLocal
from app.models.contacts import Contact, ContactList, ContactListMember, ImportJob
from app.models.enums import ContactSource, ImportJobStatus
from app.schemas.contact import CSVPreviewResponse
from app.services.contact_service import is_suppressed

logger = logging.getLogger(__name__)
EMAIL_ADAPTER = TypeAdapter(EmailStr)
MAX_IMPORT_BYTES = 25 * 1024 * 1024


def _decode_csv(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("INVALID_CSV") from exc


async def preview_csv(file_bytes: bytes) -> CSVPreviewResponse:
    if len(file_bytes) > MAX_IMPORT_BYTES:
        raise ValueError("FILE_TOO_LARGE")

    csv_text = _decode_csv(file_bytes)
    try:
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
    except csv.Error as exc:
        raise ValueError("INVALID_CSV") from exc

    if not rows:
        raise ValueError("INVALID_CSV")

    headers = rows[0]
    if not headers:
        raise ValueError("INVALID_CSV")

    data_rows = rows[1:]
    return CSVPreviewResponse(headers=headers, preview_rows=data_rows[:10], total_rows=len(data_rows))


async def start_import_job(
    org_id: UUID,
    list_id: UUID,
    created_by: UUID,
    column_mapping: dict[str, str],
    file_bytes: bytes,
    db: AsyncSession,
) -> ImportJob:
    job = ImportJob(
        list_id=list_id,
        created_by=created_by,
        status=ImportJobStatus.PENDING,
        total_rows=0,
        added=0,
        updated=0,
        skipped=0,
        errored=0,
        error_log=[],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    if settings.APP_ENV != "test":
        async def _background() -> None:
            async with SessionLocal() as background_db:
                try:
                    await run_import(job.id, org_id, list_id, column_mapping, file_bytes, background_db)
                except Exception:
                    logger.exception("Background import job failed")

        asyncio.create_task(_background())
    return job


def _map_row(
    row: dict[str, str],
    column_mapping: dict[str, str],
) -> tuple[str | None, dict[str, Any]]:
    email_value: str | None = None
    contact_fields: dict[str, Any] = {}
    custom_fields: dict[str, Any] = {}

    for csv_column, field_name in column_mapping.items():
        raw_value = (row.get(csv_column) or "").strip()
        if not field_name or field_name == "skip":
            continue
        if field_name == "email":
            email_value = raw_value or None
        elif field_name in {"first_name", "last_name", "phone"}:
            contact_fields[field_name] = raw_value or None
        elif field_name.startswith("custom_fields."):
            custom_key = field_name.split(".", 1)[1]
            custom_fields[custom_key] = raw_value
    contact_fields["custom_fields"] = custom_fields
    return email_value, contact_fields


async def run_import(
    job_id: UUID,
    org_id: UUID,
    list_id: UUID,
    column_mapping: dict[str, str],
    file_bytes: bytes,
    db: AsyncSession,
) -> None:
    job = await db.get(ImportJob, job_id)
    if job is None:
        return

    job.status = ImportJobStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        csv_text = _decode_csv(file_bytes)
        reader = csv.DictReader(io.StringIO(csv_text))
        if reader.fieldnames is None:
            raise ValueError("INVALID_CSV")

        job.total_rows = 0
        job.added = 0
        job.updated = 0
        job.skipped = 0
        job.errored = 0
        job.error_log = []

        for index, row in enumerate(reader, start=1):
            job.total_rows += 1
            try:
                email_value, contact_fields = _map_row(row, column_mapping)
                if email_value is None:
                    raise ValueError("INVALID_CSV")
                EMAIL_ADAPTER.validate_python(email_value)

                if await is_suppressed(org_id, email_value, db):
                    job.skipped += 1
                    continue

                contact_result = await db.execute(
                    select(Contact).where(
                        Contact.org_id == org_id,
                        Contact.email.ilike(email_value),
                    )
                )
                contact = contact_result.scalar_one_or_none()
                if contact is None:
                    contact = Contact(
                        org_id=org_id,
                        email=email_value,
                        first_name=contact_fields.get("first_name"),
                        last_name=contact_fields.get("last_name"),
                        phone=contact_fields.get("phone"),
                        custom_fields=contact_fields.get("custom_fields", {}),
                        source=ContactSource.IMPORT,
                    )
                    db.add(contact)
                    await db.flush()
                    job.added += 1
                else:
                    if contact_fields.get("first_name") is not None:
                        contact.first_name = contact_fields.get("first_name")
                    if contact_fields.get("last_name") is not None:
                        contact.last_name = contact_fields.get("last_name")
                    if contact_fields.get("phone") is not None:
                        contact.phone = contact_fields.get("phone")
                    merged_custom_fields = dict(contact.custom_fields or {})
                    merged_custom_fields.update(contact_fields.get("custom_fields", {}))
                    contact.custom_fields = merged_custom_fields
                    job.updated += 1

                insert_stmt = pg_insert(ContactListMember).values(contact_id=contact.id, list_id=list_id)
                insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["contact_id", "list_id"])
                await db.execute(insert_stmt)
            except Exception as exc:  # noqa: BLE001
                job.errored += 1
                job.error_log = list(job.error_log or []) + [{"row": index, "error": str(exc)}]
        job.status = ImportJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        job.status = ImportJobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.error_log = list(job.error_log or []) + [{"error": str(exc)}]
        await db.commit()


async def get_import_job(org_id: UUID, job_id: UUID, db: AsyncSession) -> ImportJob:
    result = await db.execute(
        select(ImportJob)
        .join(ContactList, ContactList.id == ImportJob.list_id)
        .where(ImportJob.id == job_id, ContactList.org_id == org_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise ValueError("NOT_FOUND")
    return job