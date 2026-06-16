# backend/src/db/session.py
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..core.config import settings
from .base import Base

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    # Ensure connections are properly reset when returned to pool
    pool_reset_on_return="rollback",
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_fresh_db():
    """
    Get a fresh database session with explicit transaction cleanup.
    Use this in Celery tasks to avoid 'INTRANS' connection state issues on retry.

    This generator ensures each call gets a clean connection by:
    1. Rolling back any existing transaction before starting
    2. Explicitly closing the connection when done
    """
    db = SessionLocal()
    try:
        # Ensure we start with a clean slate (rollback any lingering transaction)
        db.rollback()
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        # Explicitly close the connection to return it cleanly to the pool
        db.close()
