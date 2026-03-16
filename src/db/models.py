"""SQLAlchemy database models for project and job tracking.

These models fulfil the Phase 2 roadmap item:
- Projects are stored in a relational DB rather than raw JSON files on disk.
- Each indexing job has a status state machine: PENDING → RUNNING → COMPLETED | FAILED.

Usage (setup)::

    from src.db.models import Base, engine
    Base.metadata.create_all(bind=engine)

Usage (session)::

    from src.db.models import get_db
    with get_db() as db:
        db.add(project)
        db.commit()
"""

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from src.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Project(Base):
    """Represents a single user-submitted RAG project."""

    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(Float, default=time.time)
    documents_count = Column(Integer, default=0)
    chunks_count = Column(Integer, default=0)
    vector_database = Column(String, nullable=False)
    chunking_strategy = Column(String, nullable=False)
    embedding_model = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | running | completed | failed
    error_message = Column(Text, nullable=True)

    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")


class Job(Base):
    """Tracks the lifecycle of a single indexing task."""

    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    started_at = Column(Float, nullable=True)
    completed_at = Column(Float, nullable=True)
    status = Column(String, default="pending")  # pending | running | completed | failed
    error_message = Column(Text, nullable=True)

    project = relationship("Project", back_populates="jobs")


@contextmanager
def get_db() -> Iterator[Session]:
    """Context manager providing a SQLAlchemy session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """Create all database tables. Call once at application startup."""
    Base.metadata.create_all(bind=engine)
