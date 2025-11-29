from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework import status

from users.serializers import CustomUserSerializer

login_post_schema = extend_schema(
    tags=['Auth'],
    request=CustomUserSerializer,
    responses={status.HTTP_200_OK: CustomUserSerializer}
)

logout_post_schema = extend_schema(
    tags=['Auth'],
    responses={status.HTTP_200_OK: OpenApiResponse(
        description="User logged out successfully",
        examples={
            "message": "Logged out successfully"
        }
    )}
)

user_profile_get_schema = extend_schema(
    tags=['Auth'],
    responses={status.HTTP_200_OK: CustomUserSerializer}
)

register_post_schema = extend_schema(
    tags=['Auth'],
    request=CustomUserSerializer,
    responses={status.HTTP_201_CREATED: OpenApiResponse(
        description="User registered successfully",
        examples={
            'message': 'User created successfully',
            'token': 'some_token',
            'user_id': 1,
            'username': 'john_doe',
            'email': 'john.doe@example.com',
        }
    )}
)

request_otp_post_schema = extend_schema(
    tags=['Auth'],
    request=OpenApiResponse(description="Phone number to request OTP"),
    responses={status.HTTP_200_OK: OpenApiResponse(description="OTP sent successfully")}
)

verify_otp_post_schema = extend_schema(
    tags=['Auth'],
    request=OpenApiResponse(description="OTP code and phone number for verification"),
    responses={status.HTTP_200_OK: OpenApiResponse(description="OTP verification successful")}
)

auth_token_post_schema = extend_schema(
    tags=["Auth"],
    summary="Obtain authentication token",
    description="Authenticate a user with username & password and return a token + user info.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "example": "admin"},
                "password": {"type": "string", "example": "1234"},
            },
            "required": ["username", "password"],
        }
    },
    responses={
        200: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "example": "a8d34cbbaf5e..."},
                    "user_id": {"type": "integer", "example": 1},
                    "username": {"type": "string", "example": "admin"},
                    "email": {"type": "string", "example": "admin@example.com"},
                    "is_staff": {"type": "boolean", "example": True},
                    "is_superuser": {"type": "boolean", "example": True},
                    "full_name": {"type": "string", "example": "Admin User"},
                }
            },
            description="Successful login response"
        ),
        400: OpenApiResponse(
            description="Validation error (wrong username/password)"
        ),
    },
    examples=[
        OpenApiExample(
            "Example request",
            value={"username": "admin", "password": "1234"},
            request_only=True,
        ),
        OpenApiExample(
            "Example response",
            value={
                "token": "a8d34cbbaf5e...",
                "user_id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
                "full_name": "Admin User"
            },
            response_only=True,
        ),
    ]
)
