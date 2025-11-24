from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import status

from users.serializers import CustomUserSerializer

caller_schema = extend_schema(
    description="Retrieve a list of users who have the 'caller' role in at least one project.",
    responses={status.HTTP_200_OK: CustomUserSerializer(many=True)},
)

profile_schema = extend_schema(
    description="Retrieve information about the currently authenticated user.",
    responses={status.HTTP_200_OK: CustomUserSerializer()},
)
