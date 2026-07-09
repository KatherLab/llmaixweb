# backend/src/schemas/audit.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..utils.enums import AuditAction, AuditOutcome


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    actor_user_id: int | None = None
    actor_email: str | None = None
    actor_ip: str | None = None
    action: AuditAction
    resource_type: str | None = None
    resource_id: str | None = None
    project_id: int | None = None
    outcome: AuditOutcome
    detail: dict | None = None
    request_id: str | None = None


class PaginatedAuditLogs(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditLogEntry]


class ErrorLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    error_id: str
    created_at: datetime
    request_id: str | None = None
    actor_user_id: int | None = None
    actor_email: str | None = None
    method: str | None = None
    path: str | None = None
    status_code: int
    exception_type: str | None = None
    message: str | None = None
    traceback: str | None = None


class PaginatedErrorLogs(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ErrorLogEntry]
