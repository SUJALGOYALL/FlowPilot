from app.db.redis import redis_client


REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60


async def store_refresh_token(
    jti: str,
    user_id: int,
) -> None:
    key = f"refresh_token:{jti}"

    await redis_client.set(
        key,
        str(user_id),
        ex=REFRESH_TOKEN_EXPIRE_SECONDS,
    )


async def is_refresh_token_valid(
    jti: str,
) -> bool:
    key = f"refresh_token:{jti}"

    return await redis_client.exists(key) == 1


async def revoke_refresh_token(
    jti: str,
) -> None:
    key = f"refresh_token:{jti}"

    await redis_client.delete(key)