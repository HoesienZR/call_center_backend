
from rest_framework import status

from users.serializers import CustomUserSerializer

from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiExample,
    OpenApiResponse
)


user_schema = extend_schema_view(

    # ------------------ list ------------------
    list=extend_schema(
        tags=["Users"],
        summary="List all users",
        description="Retrieve the list of all users.",
        responses={
            200: OpenApiResponse(
                response=CustomUserSerializer(many=True),
                description="List of users"
            )
        }
    ),

    # ------------------ retrieve ------------------
    retrieve=extend_schema(
        tags=["Users"],
        summary="Retrieve a user",
        description="Get a specific user by ID.",
        responses={
            200: OpenApiResponse(
                response=CustomUserSerializer,
                description="User details"
            ),
            404: OpenApiResponse(description="User not found"),
        }
    ),

    # ------------------ callers ------------------
    callers=extend_schema(
        tags=["Users"],
        summary="List users with 'caller' role",
        description="Retrieve all users who have the role 'caller' in at least one project.",
        responses={
            200: OpenApiResponse(
                response=CustomUserSerializer(many=True),
                description="List of caller users"
            )
        },
        examples=[
            OpenApiExample(
                "Example response",
                value=[
                    {
                        "id": 5,
                        "username": "caller_user",
                        "email": "caller@example.com",
                        "full_name": "Caller User",
                        "is_active": True,
                    }
                ]
            )
        ]
    ),

    # ------------------ me ------------------
    me=extend_schema(
        tags=["Users"],
        summary="Current user's profile",
        description="Returns the profile of the authenticated user.",
        responses={
            200: OpenApiResponse(
                response=CustomUserSerializer,
                description="Current user's profile"
            ),
            401: OpenApiResponse(description="Authentication required"),
        },
        examples=[
            OpenApiExample(
                "Example",
                value={
                    "id": 1,
                    "username": "admin",
                    "email": "admin@example.com",
                    "full_name": "Admin User",
                    "is_active": True,
                }
            )
        ]
    ),

)

