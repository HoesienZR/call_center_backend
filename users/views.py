import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from projects.models import ProjectMembership
from users.services.user_schema import user_schema
from .serializers import CustomUserSerializer

User = get_user_model()

logger = logging.getLogger(__name__)


@user_schema
class UserViewSet(ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='callers', url_name='callers')
    def callers(self, request):
        """
        List all users who have the role 'caller' in at least one project.
        """
        caller_user_ids = ProjectMembership.objects.filter(role='caller').values_list('user_id', flat=True).distinct()
        callers = self.get_queryset().filter(id__in=caller_user_ids)
        serializer = self.get_serializer(callers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='me', url_name='me')
    def me(self, request):
        """
        Return the profile information of the currently logged-in user.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
