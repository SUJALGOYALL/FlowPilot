import secrets

from app.core.security import hash_password, verify_password
from app.db.redis import redis_client


OTP_EXPIRY_SECONDS = 10 * 60
OTP_LENGTH = 6


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def store_otp(email: str, otp: str) -> None:
    otp_hash = hash_password(otp)

    key = f"email_verification:{email.lower()}"

    await redis_client.set(
        key,
        otp_hash,
        ex=OTP_EXPIRY_SECONDS,
    )


async def verify_otp(email: str, otp: str) -> bool:
    key = f"email_verification:{email.lower()}"

    stored_hash = await redis_client.get(key)

    if stored_hash is None:
        return False

    return verify_password(
        otp,
        stored_hash,
    )


async def delete_otp(email: str) -> None:
    key = f"email_verification:{email.lower()}"

    await redis_client.delete(key)