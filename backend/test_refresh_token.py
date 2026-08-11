import asyncio

from app.core.security import create_refresh_token
from app.services.token import (
    is_refresh_token_valid,
    revoke_refresh_token,
    store_refresh_token,
)


async def test():
    user_id = 1

    token, jti = create_refresh_token(
        user_id=user_id,
    )

    print("JTI:")
    print(jti)

    await store_refresh_token(
        jti=jti,
        user_id=user_id,
    )

    print("\nAfter storing:")
    print(
        await is_refresh_token_valid(jti)
    )

    await revoke_refresh_token(jti)

    print("\nAfter revoking:")
    print(
        await is_refresh_token_valid(jti)
    )


if __name__ == "__main__":
    asyncio.run(test())