import logging
import traceback
from io import BytesIO

import jdatetime
import pandas as pd
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from core.utils import generate_username
from contacts.models import Contact
from core.permissions import IsReadOnlyOrProjectAdmin, IsProjectAdmin
from core.utils import normalize_phone_number, validate_phone_number
from files.models import Question, UploadedFile
from .serializers import *
from rest_framework.decorators import action, api_view
from rest_framework import generics, mixins
from .utils import clean_string_field, import_caller_from_excel, check_if_user_exist, check_if_project_membership_exist, toggle_user_project_membership_role
from .schema import (
    project_list_schema,
    project_create_schema,
    check_user_role_schema,
    caller_performance_schema,
    project_membership_list_schema,
    caller_import_schema,
    toggle_user_role_schema,
)

logger = logging.getLogger(__name__)

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsReadOnlyOrProjectAdmin]

    @project_list_schema
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @project_create_schema
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        base_prefetch = [
            Prefetch('questions', queryset=Question.objects.prefetch_related('choices')),
            Prefetch(
                'calls__answers',
                queryset=CallAnswer.objects.select_related('selected_choice').prefetch_related(
                    Prefetch('question__choices')
                )
            )
        ]

        if user.is_superuser:
            return Project.objects.all().prefetch_related(*base_prefetch)

        return user.projects.distinct().prefetch_related(*base_prefetch)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.can_create_projects:
            raise PermissionDenied("شما اجازه ساخت پروژه جدید را ندارید.")
        with transaction.atomic():
            project = serializer.save(created_by=user)
            ProjectMembership.objects.create(project=project, user=user, role='admin')

    @check_user_role_schema
    @action(detail=False, methods=['get'], url_path='check-user-role', permission_classes=[IsAuthenticated])
    def check_user_role(self, request):
        project_id = request.data.get('project_id')
        user_id = request.data.get('user_id')

        if not project_id:
            return Response({'error': 'شناسه پروژه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)

        if not user_id:
            return Response({'error': 'شناسه کاربر الزامی است'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project_membership = ProjectMembership.objects.get(project_id=project_id, user_id=user_id)
        except ProjectMembership.DoesNotExist:
            return Response({'error': 'membership not found'}, status=status.HTTP_404_NOT_FOUND)
        except ProjectMembership.MultipleObjectsReturned:
            return Response({'error': "multiple roles returned"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProjectMembershipSerializer(project_membership)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @caller_performance_schema
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsProjectAdmin])
    def caller_performance(self, request, pk=None):
        project = self.get_object()
        report = project.get_caller_performance_report()
        return Response(report)

class ProjectMembershipApiListView(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = ProjectMembership.objects.select_related("project", "user")
    serializer_class = ProjectMembershipSerializer

    @project_membership_list_schema
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return self.queryset.filter(project_id=project_id)
        return self.queryset

class CallerImportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @caller_import_schema
    def post(self, request, project_id):
        """
        آپلود فایل اکسل و افزودن مخاطبین جدید.
        اگر تماس‌گیرنده وجود داشته باشد، اختصاص داده می‌شود.
        """
        project = get_object_or_404(Project, id=project_id)
        file_obj = request.FILES.get("file")

        if not file_obj:
            return Response({"error": "excel didn't received "}, status=status.HTTP_400_BAD_REQUEST)

        try:
            created_contacts = import_caller_from_excel(file_obj, project)
            return Response(
                {
                    "message": f"{len(created_contacts)} callers added",
                    "created_count": len(created_contacts),
                    "contacts": created_contacts,  # شامل شماره و نام
                    "project": project.name,
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            traceback.print_exc()
            return Response(
                {"error": f"Error at progress of {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

@toggle_user_role_schema
@api_view(["GET", ])
def toggle_user_role(request):
    try:
        project = check_if_user_exist(request.data.get('project_id'))
        user = check_if_user_exist(request.data.get('user_id'))
        project_membership = check_if_project_membership_exist(project=project, user=user)
        old_role, new_role = toggle_user_project_membership_role(project=project, user=user, project_membership=project_membership)
    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"Error at progress of {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    response_data = {
        'message': 'نقش کاربر با موفقیت تغییر یافت',
        'user_id': user.id,
        'username': user.username,
        'full_name': user.get_full_name(),
        'old_role': old_role,
        'new_role': new_role,
        'new_role_display': project_membership.get_role_display()
    }
    return Response(response_data, status=status.HTTP_200_OK)
