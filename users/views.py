from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import logging
from projects.models import ProjectMembership
from .models import *
from .serializers import CustomUserSerializer

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='callers', url_name='callers')
    def callers(self, request):
        """
        لیست تمام کاربرانی که در حداقل یک پروژه نقش 'caller' دارند.
        """
        caller_user_ids = ProjectMembership.objects.filter(role='caller').values_list('user_id', flat=True).distinct()
        callers = self.get_queryset().filter(id__in=caller_user_ids)
        serializer = self.get_serializer(callers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='me', url_name='me')
    def me(self, request):
        """
        اطلاعات کاربر لاگین کرده را برمی‌گرداند.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

