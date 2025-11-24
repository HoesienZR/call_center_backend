from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status

from users.serializers import CustomUserSerializer

login_post_schema = extend_schema(
    request=CustomUserSerializer,
    responses={status.HTTP_200_OK: CustomUserSerializer}
)

logout_post_schema = extend_schema(
    responses={status.HTTP_200_OK: OpenApiResponse(
        description="User logged out successfully",
        examples=[{
            "message": "با موفقیت خارج شدید"
        }]
    )}
)

user_profile_get_schema = extend_schema(
    responses={status.HTTP_200_OK: CustomUserSerializer}
)

register_post_schema = extend_schema(
    request=CustomUserSerializer,
    responses={status.HTTP_201_CREATED: OpenApiResponse(
        description="User registered successfully",
        examples=[{
            'message': 'کاربر با موفقیت ایجاد شد',
            'token': 'some_token',
            'user_id': 1,
            'username': 'john_doe',
            'email': 'john.doe@example.com',
        }]
    )}
)

request_otp_post_schema = extend_schema(
    request=OpenApiResponse(description="Phone number to request OTP"),
    responses={status.HTTP_200_OK: OpenApiResponse(description="OTP sent successfully")}
)

verify_otp_post_schema = extend_schema(
    request=OpenApiResponse(description="OTP code and phone number for verification"),
    responses={status.HTTP_200_OK: OpenApiResponse(description="OTP verification successful")}
)
