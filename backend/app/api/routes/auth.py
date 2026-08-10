from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.email import send_email
from app.services.otp import generate_otp, store_otp


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Check whether the email already exists
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    # 2. Hash the password
    hashed_password = hash_password(data.password)

    # 3. Create the user
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hashed_password,
        role="employee",
        is_active=True,
        is_verified=False,
    )

    db.add(user)

    # We need the generated user ID before continuing.
    await db.flush()

    # 4. Generate OTP
    otp = generate_otp()

    # 5. Store hashed OTP in Redis
    await store_otp(data.email, otp)

    # 6. Send OTP email
    await send_email(
        to_email=data.email,
        subject="Verify your FlowPilot account",
        body=(
            f"Hello {data.full_name},\n\n"
            f"Your FlowPilot verification code is: {otp}\n\n"
            "This code will expire in 10 minutes.\n\n"
            "If you did not create this account, "
            "you can safely ignore this email.\n\n"
            "Regards,\n"
            "FlowPilot"
        ),
    )

    # 7. Commit the user
    await db.commit()

    return {
        "message": "Registration successful. "
        "Please verify your email using the OTP sent to you.",
        "email": data.email,
    }