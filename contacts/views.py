import logging
import random
from random import random

import pandas as pd
from django.db import transaction
from django.db.models import Q, Count
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from call_center_backend import settings
from core.utils import (
    validate_phone_number, normalize_phone_number,
)
AUTH_USER_MODEL = settings.AUTH_USER_MODEL
from projects.models import ProjectMembership
from .models import Project, Contact

from .permission import IsProjectCaller,IsProjectAdmin,ReleaseContactPermission

from .serializers import (
    ContactSerializer,
    ContactStatsSerializer,
    #CallSerializer
)
from .schema import (filter_contact_by_status_and_project_schema,
                     release_contact_schema,
                     get_contact_stats_schema,
                     filter_contact_by_project_schema,
                     filter_contact_by_status_schema,
                     request_new_contact_schema)
# تنظیم logger
logger = logging.getLogger(__name__)


# Create your views here.
User = settings.AUTH_USER_MODEL


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.select_related("project","assigned_caller").prefetch_related('calls')
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated, IsProjectAdmin | IsAdminUser| IsProjectCaller]


    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_queryset(self):
        user = self.request.user
        base_qs = Contact.objects.select_related("project", "assigned_caller").prefetch_related("calls")
        if user.is_superuser:
            qs = base_qs
        else:
            user_projects = Project.objects.filter(member=user)
            if ProjectMembership.objects.filter(project__in=user_projects, user=user, role='admin').exists():
                qs = base_qs.filter(project__in=user_projects)
            else:
                qs = base_qs.filter(assigned_caller=user)

        qs = qs.annotate(
            total_calls=Count('calls', distinct=True),
            answered_calls=Count('calls', filter=Q(calls__status='answered'), distinct=True),
            not_answered_calls=Count('calls', filter=Q(calls__status='no_answer'), distinct=True),
            interested_calls=Count('calls', filter=Q(calls__call_result='interested'), distinct=True),
            not_interested_calls=Count('calls', filter=Q(calls__call_result='not_interested'), distinct=True),
            no_time_calls=Count('calls', filter=Q(calls__call_result='no_time'), distinct=True),
        )

        return qs

    def perform_create(self, serializer):
        """
        ثبت مخاطب جدید با اعمال منطق تخصیص
        """
        project = serializer.validated_data['project']
        user = self.request.user

        # اگر کاربر تماس‌گیرنده است، مخاطب به خودش تخصیص داده می‌شود
        if not serializer.validated_data.get('assigned_caller'):
            try:
                membership = ProjectMembership.objects.get(project=project, user=user)
                if membership.role == 'caller':
                    serializer.validated_data['assigned_caller'] = user
            except ProjectMembership.DoesNotExist:
                pass

        serializer.save(created_by=user)

    @extend_schema(**filter_contact_by_status_and_project_schema)
    @action(detail=False, methods=['get'],url_path="filter_contact_by_status_and_project",permission_classes = [])
    def filter_contact_by_status_and_project(self, request,):

        contact_status = self.request.GET.get('status')
        project_id = self.request.GET.get('project_id')
        if contact_status is None or project_id is None:
            return Response({'detail':'status and project id must provided'},status=status.HTTP_400_BAD_REQUEST)
        contacts_filtered_by_project_and_status = self._filter_contacts(project_id=project_id,contact_status=contact_status)
        serializer = self.get_serializer(contacts_filtered_by_project_and_status, many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    @extend_schema(**filter_contact_by_status_schema)
    @action(detail=False, methods=['get'],url_path="filter_contact_by_status")
    def filter_contact_by_status(self, request,):
        contact_status = self.request.GET.get('status')
        if contact_status is None :
            return Response({'detail':'status must to set '},status=status.HTTP_400_BAD_REQUEST)
        contact_filter_by_status =  self._filter_contacts(contact_status=contact_status)
        serializer = self.get_serializer(contact_filter_by_status, many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    @extend_schema(**filter_contact_by_project_schema)
    @action(detail=False, methods=['get'],url_path="filter_contact_by_project")
    def filter_contact_by_project(self, request, ):
        user = self.request.user
        project_id = self.request.GET.get('project_id')
        if project_id is None:
            return Response({'detail':"project does not exist or not valid "},status=status.HTTP_400_BAD_REQUEST)
        contact_filter_by_project= self._filter_contacts(project_id=project_id)
        serializer  = self.get_serializer(contact_filter_by_project, many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

    #TODO this is must change must into project memebet view set
    @action(detail=False, methods=['get'], url_path='request_new')
    def request_new_contact(self, request):
        "درخواست مخاطب جدید برای تماس‌گیرنده"
        project_id = request.data.get('project_id')
        if not project_id:
            return Response({"detail": "شناسه پروژه الزامی است."},status=status.HTTP_400_BAD_REQUEST)
        try:
            project = Project.objects.get(id=project_id)

            if not ProjectMembership.objects.filter(project=project, user=request.use).exists():
                return Response({"detail": "شما عضو این پروژه نیستید."},status=status.HTTP_403_FORBIDDEN)

            available_contact = Contact.objects.filter(
                project=project,
                assigned_caller__isnull=True,
                call_status='pending',
                is_active=True
            ).first()

            if available_contact:
                available_contact.assigned_caller = request.user
                available_contact.save()
                return Response(
                    {"detail": "مخاطب جدیدی به شما تخصیص یافت."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": "در حال حاضر مخاطب آزادی برای تخصیص وجود ندارد."},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Project.DoesNotExist:
            return Response({"detail": "پروژه یافت نشد."},status=status.HTTP_404_NOT_FOUND )


    @extend_schema(**release_contact_schema)
    @action(detail=True, methods=['post'], url_path='release',permission_classes = [ReleaseContactPermission])
    def release_contact(self, request,):
        """
        آزاد کردن مخاطب توسط تماس‌گیرنده یا ادمین
        """
        contact = self.get_object()
        user = request.user

        if contact.assigned_caller == user:
            contact.assigned_caller = None
            contact.save()

            return Response(
                {"detail": "مخاطب با موفقیت آزاد شد و به لیست عمومی بازگشت."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "شما اجازه آزاد کردن این مخاطب را ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )

    #TODO so sumbit call must go on call viewset we just implementd creat call function here
    @action(detail=True, methods=["post"], url_path="submit-call")
    def submit_call(self, request, pk=None):
        """
        ثبت یک تماس جدید برای یک مخاطب
        """
        contact = self.get_object()

        # بررسی دسترسی
        if not contact.assigned_caller == request.user :
            return Response({"detail": "شما اجازه ثبت تماس برای این مخاطب را ندارید."},status=status.HTTP_403_FORBIDDEN)
        serializer = CallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ثبت تماس
        call = serializer.save(
            caller=request.user,
            contact=contact,
            project=contact.project
        )

        # به‌روزرسانی وضعیت مخاطب
        call_result = serializer.validated_data.get('call_result')
        status_map = {
            'answered': 'contacted',
            'callback_requested': 'follow_up',
            'not_interested': 'not_interested',
            'wrong_number': 'not_interested',
        }
    @get_contact_stats_schema
    @action(detail=True,methods=['get'],url_path='stats')
    def get_contact_stats(self,request,pk=None):
        contact  = self.get_object()
        serializer = ContactStatsSerializer(contact,context={'request':request})
        if serializer.is_valid:
            return Response(serializer.data , status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def _filter_contacts(self, project_id=None, contact_status=None):
        qs = self.get_queryset()
        if project_id:
            qs = qs.filter(project_id=project_id)
        if status:
            qs = qs.filter(call_status=status)
        return qs