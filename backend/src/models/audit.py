# backend/src/models/audit.py
"""Append-only audit trail + central error log.

Both tables are write-once from the application's point of view: the services
that populate them expose only an insert path, there are no update/delete
routes, and the admin API over them is read-only. This is the accountability
substrate a clinical deployment needs — "who did what, when, from where" for
authentication, PHI access, data mutations, external egress, and admin changes.

Neither table stores PHI. ``AuditLog.detail`` holds small structured context
(ids, counts, field names, endpoint hosts) — never document text or extracted
values — so the audit trail itself never becomes a second copy of patient data.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from ..utils.enums import AuditAction, AuditOutcome

# BigInteger PK on PostgreSQL (bigserial — these tables can grow large), but
# SQLite only autoincrements a plain INTEGER PRIMARY KEY, not BIGINT. The
# variant keeps the dev/test SQLite stack working (audit writes would otherwise
# fail the NOT NULL id constraint) while giving Postgres a 64-bit id.
_BigIntPk = BigInteger().with_variant(Integer, "sqlite")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(_BigIntPk, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )
    # Actor: FK is SET NULL on user delete so history survives account removal,
    # while ``actor_email`` keeps a human-readable snapshot regardless.
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, native_enum=False, length=32), index=True
    )
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    outcome: Mapped[AuditOutcome] = mapped_column(
        Enum(AuditOutcome, native_enum=False, length=16),
        default=AuditOutcome.SUCCESS,
    )
    # Small, PHI-free structured context. JSON (not JSONB) keeps it portable to
    # the SQLite dev/test stack; audit rows are never queried by detail content.
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Correlates a row to the request's logs and to any ErrorLog for the same
    # request (both use the same 12-char id).
    request_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_audit_logs_project_created", "project_id", "created_at"),
        Index("ix_audit_logs_actor_created", "actor_user_id", "created_at"),
    )


class ErrorLog(Base):
    """One row per unhandled server error, keyed by the user-facing error id.

    An admin looks up the id a user reported and sees the full traceback. Kept
    separate from ``AuditLog`` because its lifecycle (verbose, rotatable,
    tracebacks) differs from the durable accountability trail.
    """

    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(_BigIntPk, primary_key=True)
    error_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    method: Mapped[str | None] = mapped_column(String(8), nullable=True)
    path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status_code: Mapped[int] = mapped_column(default=500)
    exception_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
