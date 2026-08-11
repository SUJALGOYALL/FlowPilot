from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


user_id = 1
role = "employee"


access_token = create_access_token(
    user_id=user_id,
    role=role,
)

refresh_token, jti = create_refresh_token(
    user_id=user_id,
)


print("ACCESS TOKEN:")
print(access_token)

print("\nREFRESH TOKEN:")
print(refresh_token)

print("\nREFRESH JTI:")
print(jti)

print("\nACCESS PAYLOAD:")
print(decode_token(access_token))

print("\nREFRESH PAYLOAD:")
print(decode_token(refresh_token))