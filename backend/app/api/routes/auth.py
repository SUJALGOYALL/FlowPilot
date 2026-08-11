from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    VerifyEmailRequest,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services.token import store_refresh_token
from app.services.email import send_email
from app.services.otp import (
    delete_otp,
    generate_otp,
    store_otp,
    verify_otp,
)


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

@router.post("/verify-email")
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Find the user
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # 2. Check whether email is already verified
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified.",
        )

    # 3. Verify OTP from Redis
    is_valid = await verify_otp(
        data.email,
        data.otp,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP.",
        )

    # 4. Mark email as verified
    user.is_verified = True

    # 5. Remove OTP so it cannot be reused
    await delete_otp(data.email)

    # 6. Save the change
    await db.commit()

    return {
        "message": "Email verified successfully.",
        "email": user.email,
    }

@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Find the user
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # 2. Check password
    if not verify_password(
        data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # 3. Check whether the account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    # 4. Check email verification
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    # 5. Generate access token
    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    # 6. Generate refresh token
    refresh_token, jti = create_refresh_token(
        user_id=user.id,
    )

    # 7. Store refresh session in Redis
    await store_refresh_token(
        jti=jti,
        user_id=user.id,
    )

    # 8. Return tokens
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )