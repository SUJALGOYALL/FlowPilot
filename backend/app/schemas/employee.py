from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EmployeeCreate(BaseModel):
    user_id: int
    employee_id: str
    department: str
    job_title: str
    manager_id: int | None = None
    joining_date: date
    employment_type: str = "full_time"
    location: str | None = None


class EmployeeResponse(BaseModel):
    id: int
    user_id: int
    employee_id: str
    department: str
    job_title: str
    manager_id: int | None
    joining_date: date
    employment_type: str
    location: str | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )