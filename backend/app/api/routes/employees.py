from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.database import get_db
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeResponse


router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(
        require_role("hr", "admin")
    ),
    db: AsyncSession = Depends(get_db),
):
    # 1. Check that the user exists
    result = await db.execute(
        select(User).where(User.id == data.user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # 2. Check whether this user already has an employee profile
    result = await db.execute(
        select(Employee).where(
            Employee.user_id == data.user_id
        )
    )

    existing_employee = result.scalar_one_or_none()

    if existing_employee is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee profile already exists for this user.",
        )

    # 3. Check employee ID uniqueness
    result = await db.execute(
        select(Employee).where(
            Employee.employee_id == data.employee_id
        )
    )

    existing_employee_id = result.scalar_one_or_none()

    if existing_employee_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee ID already exists.",
        )

    # 4. Validate manager if supplied
    if data.manager_id is not None:
        result = await db.execute(
            select(Employee).where(
                Employee.id == data.manager_id
            )
        )

        manager = result.scalar_one_or_none()

        if manager is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager not found.",
            )

    # 5. Create employee
    employee = Employee(
        user_id=data.user_id,
        employee_id=data.employee_id,
        department=data.department,
        job_title=data.job_title,
        manager_id=data.manager_id,
        joining_date=data.joining_date,
        employment_type=data.employment_type,
        location=data.location,
    )

    db.add(employee)

    await db.commit()
    await db.refresh(employee)

    return employee