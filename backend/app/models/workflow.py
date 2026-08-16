from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1.0",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    yaml_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    job_title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task_definitions: Mapped[list["WorkflowTaskDefinition"]] = relationship(
        "WorkflowTaskDefinition",
        back_populates="workflow_definition",
        cascade="all, delete-orphan",
        order_by="WorkflowTaskDefinition.task_order",
    )

    runs: Mapped[list["WorkflowRun"]] = relationship(
        "WorkflowRun",
        back_populates="workflow_definition",
        cascade="all, delete-orphan",
    )


class WorkflowTaskDefinition(Base):
    __tablename__ = "workflow_task_definitions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    workflow_definition_id: Mapped[int] = mapped_column(
        ForeignKey(
            "workflow_definitions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    task_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    approval_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    depends_on: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    task_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workflow_definition: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="task_definitions",
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    workflow_definition_id: Mapped[int] = mapped_column(
        ForeignKey(
            "workflow_definitions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey(
            "employees.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workflow_definition: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="runs",
    )

    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="workflow_runs",
    )

    tasks: Mapped[list["WorkflowTask"]] = relationship(
        "WorkflowTask",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="WorkflowTask.id",
    )


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    workflow_run_id: Mapped[int] = mapped_column(
        ForeignKey(
            "workflow_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    task_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )

    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    approval_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    depends_on: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workflow_run: Mapped["WorkflowRun"] = relationship(
        "WorkflowRun",
        back_populates="tasks",
    )