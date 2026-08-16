from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.workflow import WorkflowRun


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    employee_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    job_title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )

    joining_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    employment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="full_time",
    )

    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="employee",
    )

    manager: Mapped["Employee | None"] = relationship(
        "Employee",
        remote_side="Employee.id",
        back_populates="direct_reports",
    )

    direct_reports: Mapped[list["Employee"]] = relationship(
        "Employee",
        back_populates="manager",
    )

    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(
        "WorkflowRun",
        back_populates="employee",
        cascade="all, delete-orphan",
    )