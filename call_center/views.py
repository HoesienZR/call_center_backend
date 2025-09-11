from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from datetime import datetime
from .permission import IsRegularUser,IsAdminOrCaller,IsProjectCaller
import pandas as pd
import os
import uuid
import json
import logging
from django.shortcuts import render
from django.db import connections
from django.http import HttpResponse

from .models import (
    Project, ProjectCaller, Contact, Call, CallEditHistory,
    CallStatistics, SavedSearch, UploadedFile, ExportReport, CachedStatistics
)
from .serializers import (
    UserSerializer, ProjectSerializer, ProjectCallerSerializer, ContactSerializer,
    CallSerializer, CallEditHistorySerializer, CallStatisticsSerializer,
    SavedSearchSerializer, UploadedFileSerializer, ExportReportSerializer, CachedStatisticsSerializer
)
from .utils import (
    validate_phone_number, normalize_phone_number, generate_secure_password,
    is_caller_user, assign_contacts_randomly, validate_excel_data, clean_string_field
)

# تنظیم logger
logger = logging.getLogger(__name__)


def check_postgresql_connection(request):
    try:
        connection = connections['default']
        connection.ensure_connection()
        return HttpResponse("PostgreSQL connection successful")
    except Exception as e:
        return HttpResponse(f"PostgreSQL connection failed: {e}")
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    @action(detail=False, methods=['get'],permission_classes=[IsAuthenticated,IsAdminOrCaller],
            url_path='callers',url_name='callers')
    def callers(self,request,pk=None):
        callers =  self.get_queryset().filter(profile__role='caller')
        serializer =  self.get_serializer(callers,many=True )
        return Response(serializer.data,status=status.HTTP_200_OK)

    #@action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrCaller],
    #        url_path='my_callers', url_name='my-callers')
    #def my_callers(self, request, pk=None):
    #    user =  User.objects.get(id=request.user.id)
    #    user_callers = Contact.objects.filter(user=self.request.user).
    #    serializer = self.get_serializer(user_callers, many=True)
    #    return Response(serializer.data, status=status.HTTP_200_OK)
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated,IsAdminOrCaller]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        return self.queryset.filter(
            Q(created_by=user) | Q(project_callers__caller=user, project_callers__is_active=True)
        ).distinct()
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    @action(detail=True, methods=['get'],permission_classes = [IsAuthenticated,IsAdminUser | IsProjectCaller],url_path='project_report',
            url_name = 'project-report')
    def project_report(self, request, pk=None):
        project = self.get_object()
        # Get start_date and end_date from query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Base queryset for calls
        calls_queryset = project.calls.all()

        # Apply date filters if provided
        if start_date:
            try:
                start_date = parse_date(start_date)
                if start_date:
                    calls_queryset = calls_queryset.filter(call_date__gte=start_date)
                else:
                    return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD.'},
                                    status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD.'},
                                status=status.HTTP_400_BAD_REQUEST)
        if end_date:
            try:
                end_date = parse_date(end_date)
                if end_date:
                    calls_queryset = calls_queryset.filter(call_date__lte=end_date)
                else:
                    return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD.'},
                                    status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD.'},
                                status=status.HTTP_400_BAD_REQUEST)
        # Calculate report metrics
        calls_count = calls_queryset.count()
        answered_calls_count = calls_queryset.filter(call_result='answered').count()
        answered_calls_rate = int((answered_calls_count / calls_count * 100) if calls_count > 0 else 0)
        not_interested_calls_count = calls_queryset.filter(call_result='not_interested').count()
        interested_calls_count = calls_queryset.filter(call_result='interested').count()

        # Include the filtered calls in the response
        calls_serializer = CallSerializer(calls_queryset, many=True)
        return Response({
            'project': ProjectSerializer(project).data,
            'reports': {
                'total_calls': calls_count,
                'answered_calls': answered_calls_count,
                'answered_calls_rate': answered_calls_rate,
                'interested_calls': interested_calls_count,
                'not_interested_calls': not_interested_calls_count,
            },
            'calls': calls_serializer.data
        }, status=status.HTTP_200_OK)
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def statistics(self, request, pk=None):
        project = self.get_object()
        stats = project.get_statistics()
        return Response(stats)

    @action(detail=True, methods=["get"], permission_classes=[IsAdminUser])
    def caller_performance(self, request, pk=None):
        project = self.get_object()
        report = project.get_caller_performance_report()
        return Response(report)

    @action(detail=True, methods=["get"], permission_classes=[IsAdminUser])
    def call_status_over_time(self, request, pk=None):
        project = self.get_object()
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        interval = request.query_params.get("interval", "day")

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None

        try:
            data = project.get_call_status_over_time(start_date, end_date, interval)
            return Response(data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], permission_classes=[IsAdminUser])
    def export_report(self, request, pk=None):
        project = self.get_object()
        report_type = request.query_params.get(
            "report_type")  # e.g., "project_statistics", "caller_performance", "call_status_over_time"
        export_format = request.query_params.get("format", "xlsx")  # e.g., "xlsx", "csv"

        if report_type == "project_statistics":
            data = [project.get_statistics()]
            file_name_prefix = f"project_{project.id}_statistics"
        elif report_type == "caller_performance":
            data = project.get_caller_performance_report()
            file_name_prefix = f"project_{project.id}_caller_performance"
        elif report_type == "call_status_over_time":
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")
            interval = request.query_params.get("interval", "day")

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None

            try:
                data = project.get_call_status_over_time(start_date, end_date, interval)
                file_name_prefix = f"project_{project.id}_call_status_over_time"
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "نوع گزارش نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        if not data:
            return Response({"message": "داده‌ای برای گزارش یافت نشد."}, status=status.HTTP_204_NO_CONTENT)

        # ایجاد DataFrame از داده‌ها
        df = pd.DataFrame(data)

        # ذخیره فایل
        export_path = os.path.join(settings.MEDIA_ROOT, "exports")
        if not os.path.exists(export_path):
            os.makedirs(export_path)

        unique_filename = f"{file_name_prefix}_{uuid.uuid4().hex[:8]}.{export_format}"
        full_file_path = os.path.join(export_path, unique_filename)

        if export_format == "xlsx":
            df.to_excel(full_file_path, index=False)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif export_format == "csv":
            df.to_csv(full_file_path, index=False, encoding="utf-8-sig")
            content_type = "text/csv"
        else:
            return Response({"error": "فرمت خروجی نامعتبر است. فقط xlsx و csv مجاز هستند."},
                            status=status.HTTP_400_BAD_REQUEST)

        # ثبت گزارش در دیتابیس
        ExportReport.objects.create(
            project=project,
            exported_by=request.user,
            export_type=export_format,
            file_name=unique_filename,
            file_path=full_file_path,
            records_count=len(df),
            filters=json.dumps(request.query_params.dict())
        )

        # ارسال فایل به کاربر
        # به جای ارسال مستقیم فایل، یک URL برای دانلود آن برمی‌گردانیم
        file_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, "exports", unique_filename))
        return Response({"message": "گزارش با موفقیت ایجاد شد.", "download_url": file_url}, status=status.HTTP_200_OK)


class ProjectCallerViewSet(viewsets.ModelViewSet):
    queryset = ProjectCaller.objects.all()
    serializer_class = ProjectCallerSerializer
    permission_classes = [IsAdminUser,IsAuthenticated,IsAdminOrCaller]


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        # Callers can only see contacts assigned to them or unassigned contacts in their projects
        user_projects = self.request.user.project_assignments.filter(is_active=True).values_list("project_id",
                                                                       flat=True)
        return queryset.filter(project__in=user_projects).filter(
            models.Q(assigned_caller=self.request.user) | models.Q(assigned_caller__isnull=True))
    
    def create(self, request, *args, **kwargs):
        project_and_user_info:dict = {
            "project": request.data.get("project_id"),
            "assigned_caller" : request.data.get("assigned_caller_id") or self.request.user,
            "authenticated_user":  self.request.user

        }
        ProjectCaller.objects.get_or_create(caller=User.objects.get(id=project_and_user_info['assigned_caller']),
                                            project=Project.objects.get(id=project_and_user_info['project'])
                                                                         )

        logger.info(f"Incoming request data: {request.data}")
        print(request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated,IsAdminOrCaller],
            url_path="by_projects/(?P<project_id>\d+)", url_name='by-project')
    def get_project_contacts(self, request, project_id=None):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"detail": "پروژه یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        # شرط اصلاح‌شده: کاربر سازنده پروژه باشد یا تماس‌گیرنده فعال پروژه باشد
        if self.request.user == project.created_by or project.project_callers.filter(caller=request.user,is_active=True).exists():

            serializer = ProjectSerializer(project,)
            return Response(serializer.data)
        else:
            return Response({"detail": "شما به این پروژه دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)
    @action(detail=False,methods=['get'],permission_classes = [IsAuthenticated, IsAdminOrCaller],
            url_name='pending-caller-contacts',url_path="caller_pending_contact/(?P<project_id>\d+)")
    def pending_contacts(self, request, project_id=None):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"detail": "پروژه یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        caller_pending_contacts = Contact.objects.filter(project=project,call_status='pending',assigned_caller=request.user)
        serializer = ContactSerializer(caller_pending_contacts,many=True)
        return Response(serializer.data)
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def call_statistics(self, request, pk=None):
        contact = self.get_object()
        stats = contact.get_call_statistics()
        return Response(stats)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def last_call(self, request, pk=None):
        contact = self.get_object()
        last_call = contact.get_last_call()
        if last_call:
            serializer = CallSerializer(last_call)
            return Response(serializer.data)
        return Response({"detail": "No calls found for this contact."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated,IsAdminOrCaller,])
    def request_new_call(self, request):
        """
        درخواست یک مخاطب جدید برای تماس توسط تماس‌گیرنده.
        این Endpoint یک مخاطب تخصیص داده نشده یا مخاطبی که قبلاً تماس گرفته شده و نیاز به پیگیری دارد را برمی‌گرداند.
        """
        user = request.user
        if not is_caller_user(user):
            return Response({"detail": "فقط تماس‌گیرندگان مجاز به درخواست تماس جدید هستند."},
                            status=status.HTTP_403_FORBIDDEN)

        # پیدا کردن پروژه‌هایی که تماس‌گیرنده در آن‌ها فعال است
        active_projects = user.project_assignments.filter(is_active=True).values_list("project", flat=True)
        if not active_projects:
            return Response({"detail": "شما به هیچ پروژه‌ای تخصیص داده نشده‌اید یا در پروژه‌ای فعال نیستید."},
                            status=status.HTTP_404_NOT_FOUND)
        print(active_projects)
        # اولویت ۱: مخاطبین تخصیص داده شده به این تماس‌گیرنده که هنوز تماس گرفته نشده‌اند یا نیاز به پیگیری دارند
        contact = Contact.objects.filter(
            project__in=active_projects,
            assigned_caller=user,
            call_status__in=["pending", "follow_up"]
        ).order_by("last_call_date").first()
        print(contact)
        if not contact:
            # اولویت ۲: مخاطبین تخصیص داده نشده در پروژه‌های این تماس‌گیرنده
            contact = Contact.objects.filter(
                project__in=active_projects,
                assigned_caller__isnull=True,
                call_status="pending"
            ).order_by("created_at").first()
            if contact:
                # تخصیص مخاطب به تماس‌گیرنده
                contact.assigned_caller = user
                contact.save()

        if contact:
            serializer = self.get_serializer(contact)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({"detail": "هیچ مخاطب جدیدی برای تماس یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsAdminOrCaller],
            url_path="remove_assigned_caller/(?P<contact_id>\d+)", url_name="remove-assigned_caller")
    def remove_assigned_caller(self, request, contact_id=None):
        """
        حذف تماس‌گیرنده تخصیص‌یافته از یک مخاطب خاص.
        """
        try:

            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            return Response({"detail": "مخاطب یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        project = contact.project
        # بررسی دسترسی: کاربر باید ادمین، سازنده پروژه، یا تماس‌گیرنده فعال پروژه باشد
        if (project.project_callers.filter(caller=request.user, is_active=True).exists() or request.user.is_staff):
            if contact.assigned_caller:
                caller = contact.assigned_caller
                # ثبت لاگ
                contact.assigned_caller = None

                contact.save()
                return Response({"detail": f"تماس‌گیرنده از مخاطب {contact.full_name} حذف شد."},
                                status=status.HTTP_200_OK)
            else:
                return Response({"detail": "این مخاطب تماس‌گیرنده‌ای ندارد."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": "شما به این پروژه دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated,],
            url_path="submit_call_feedback", url_name="submit-call-feedback")
    def submit_call_feedback(self, request, pk=None):
        """
        ثبت بازخورد تماس برای یک مخاطب خاص.
        """
        try:
            contact = self.get_object()
        except Contact.DoesNotExist:
            return Response({"detail": "مخاطب یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        project = contact.project
        # بررسی دسترسی
        if not (request.user.is_staff or
                request.user == project.created_by or
                project.project_callers.filter(caller=request.user, is_active=True).exists() or
                contact.assigned_caller == request.user):
            return Response({"detail": "شما به این پروژه یا مخاطب دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)
        serializer = CallSerializer(data={
            'contact_id': contact.id,
            'project_id': project.id,
            'caller_id': request.user.id,
            'status': request.data.get('status'),
            'call_result': request.data.get('result', ''),
            'notes': request.data.get('notes', ''),
            'follow_up_date': request.data.get('follow_up_date', None),
            'follow_up_notes': request.data.get('follow_up_notes', ''),
            'duration': request.data.get('duration', 0),
            'is_editable': True,
            'feedback': request.data.get('notes', ''),  # نگاشت notes به feedback
            'detailed_report': request.data.get('notes', ''),  # نگاشت notes به detailed_report
        })

        if serializer.is_valid():
            serializer.save(caller=request.user)

            # به‌روزرسانی call_status مخاطب
            call_status_map = {
                'answered': 'completed' if request.data.get('result') in ['callback_requested',
                                                                          'answered'] else 'not_interested',
                'no_answer': 'pending',
                'busy': 'pending',
                'unreachable': 'pending',
                'wrong_number': 'not_interested',
                'not_interested': 'not_interested',
                'callback_requested': 'follow_up',
            }
            new_call_status = call_status_map.get(request.data.get('result'), 'pending')

            contact.call_status = new_call_status
            contact.last_call_date = timezone.now()
            contact.save()

            # ثبت لاگ
            return Response({"detail": "بازخورد تماس با موفقیت ثبت شد.", "data": serializer.data},
                            status=status.HTTP_201_CREATED)
        else:
            return Response({"detail": "خطا در داده‌های ارسالی", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
class CallViewSet(viewsets.ModelViewSet):
    queryset = Call.objects.all()
    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        # Callers can only see their own calls
        return queryset.filter(caller=self.request.user)

    def perform_create(self, serializer):
        serializer.save(caller=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def edit_call(self, request, pk=None):
        call = self.get_object()
        if not call.can_edit(request.user):
            return Response({"detail": "You are not authorized to edit this call."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(call, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Save original data if it\"s the first edit
        call.save_original_data_if_first_edit()

        # Manually save changes and create CallEditHistory
        for attr, value in serializer.validated_data.items():
            if hasattr(call, attr) and getattr(call, attr) != value:
                CallEditHistory.objects.create(
                    call=call,
                    edited_by=request.user,
                    field_name=attr,
                    old_value=str(getattr(call, attr)),
                    new_value=str(value),
                    edit_reason=request.data.get("edit_reason", "")
                )
                setattr(call, attr, value)

        call.edited_at = datetime.now()
        call.edited_by = request.user
        call.edit_reason = request.data.get("edit_reason", "")
        call.save()

        return Response(self.get_serializer(call).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_feedback(self, request, pk=None):
        """
        ثبت بازخورد برای یک تماس موجود.
        """
        call = self.get_object()
        if call.caller != request.user:
            return Response({"detail": "شما مجاز به ثبت بازخورد برای این تماس نیستید."},
                            status=status.HTTP_403_FORBIDDEN)

        feedback_text = request.data.get("notes")
        call_status = request.data.get("status")
        if not feedback_text and not call_status:
            return Response({"error": "حداقل یکی از فیلدهای feedback_text یا call_status الزامی است."},
                            status=status.HTTP_400_BAD_REQUEST)

        if feedback_text:
            call.feedback = feedback_text

        if call_status:
            if call_status not in [choice[0] for choice in Call.CALL_STATUS_CHOICES]:
                return Response({"error": "وضعیت تماس نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
            call.status = call_status

        call.save()
        return Response(self.get_serializer(call).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_detailed_report(self, request, pk=None):
        """
        ثبت گزارش تفصیلی برای یک تماس موجود.
        """
        call = self.get_object()
        if call.caller != request.user:
            return Response({"detail": "شما مجاز به ثبت گزارش برای این تماس نیستید."}, status=status.HTTP_403_FORBIDDEN)

        report_data = request.data.get("report_data")  # انتظار یک دیکشنری یا JSON برای گزارش تفصیلی
        call_status = request.data.get("call_status")

        if not report_data and not call_status:
            return Response({"error": "حداقل یکی از فیلدهای report_data یا call_status الزامی است."},
                            status=status.HTTP_400_BAD_REQUEST)

        if report_data:
            call.detailed_report = report_data

        if call_status:
            if call_status not in [choice[0] for choice in Call.CALL_STATUS_CHOICES]:
                return Response({"error": "وضعیت تماس نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
            call.status = call_status

        call.save()
        return Response(self.get_serializer(call).data, status=status.HTTP_200_OK)


class CallEditHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CallEditHistory.objects.all()
    serializer_class = CallEditHistorySerializer
    permission_classes = [IsAdminUser]


class CallStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CallStatistics.objects.all()
    serializer_class = CallStatisticsSerializer
    permission_classes = [IsAdminUser]


class SavedSearchViewSet(viewsets.ModelViewSet):
    queryset = SavedSearch.objects.all()
    serializer_class = SavedSearchSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user) | queryset.filter(is_public=True)


class UploadedFileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCaller]  # اصلاح مجوزها

    def allowed_file(self, filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ["xlsx", "xls", "csv"]

    def ensure_upload_folder(self):
        upload_path = os.path.join(settings.MEDIA_ROOT, "uploads")
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        return upload_path

    def save_uploaded_file(self, file, project, file_type):
        """ذخیره فایل آپلود شده با نام یکتا"""
        upload_path = self.ensure_upload_folder()
        file_extension = file.name.rsplit(".", 1)[1].lower()
        unique_filename = f"{project.id}_{file_type}_{uuid.uuid4().hex[:8]}.{file_extension}"
        fs = FileSystemStorage(location=upload_path)
        filename = fs.save(unique_filename, file)
        return os.path.join(upload_path, filename)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated,])
    def upload_contacts(self, request):
        """
        آپلود فایل اکسل مخاطبین و تخصیص تماس‌گیرندگان.
        - تمام مخاطبین ایجاد می‌شوند، حتی با داده‌های ناقص.
        - اگر assigned_caller_username خالی یا نامعتبر باشد، تماس‌گیرنده به‌صورت تصادفی تخصیص می‌یابد.
        """
        if "file" not in request.FILES:
            return Response({"error": "فایل ارسال نشده است"}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        project_id = request.data.get("project_id")
        # تخصیص خودکار به‌صورت پیش‌فرض فعال است
        auto_assign = True

        if not project_id:
            return Response({"error": "شناسه پروژه الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "پروژه یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

        # بررسی دسترسی
        if not (request.user.is_staff or
                request.user == project.created_by or
                project.project_callers.filter(caller=request.user, is_active=True).exists()):
            return Response({"detail": "شما به این پروژه دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        if not self.allowed_file(file.name):
            return Response({"error": "فرمت فایل نامعتبر است. فقط xlsx, xls, csv مجاز هستند."},
                            status=status.HTTP_400_BAD_REQUEST)

        # ذخیره فایل
        file_path = self.save_uploaded_file(file, project, "contacts")

        contacts_added = 0
        contacts_updated = 0
        contacts_skipped = 0
        errors = []
        unassigned_contacts = []

        try:
            # خواندن فایل
            if file.name.endswith(".csv"):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                df = pd.read_excel(file_path)

            # اعتبارسنجی ساختار فایل
            required_columns = ["full_name", "phone"]
            validation_errors = validate_excel_data(df, required_columns)

            if validation_errors:
                return Response({
                    "error": "; ".join(validation_errors),
                    "required_columns": required_columns,
                    "found_columns": list(df.columns)
                }, status=status.HTTP_400_BAD_REQUEST)

            # پردازش داده‌ها
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # تمیز کردن داده‌ها
                        full_name = clean_string_field(row.get("full_name", "نامشخص"))
                        phone = clean_string_field(row.get("phone", ""))

                        # مدیریت شماره تلفن خالی
                        if not phone:
                            phone = f"unknown_{uuid.uuid4().hex[:8]}"
                            errors.append(f"ردیف {index + 2}: شماره تلفن خالی بود، مقدار پیش‌فرض '{phone}' استفاده شد.")

                        # اعتبارسنجی و نرمال‌سازی شماره تلفن
                        is_valid, normalized_phone = validate_phone_number(phone)
                        if not is_valid:
                            errors.append(f"ردیف {index + 2}: شماره تلفن نامعتبر: {normalized_phone}")
                            normalized_phone = phone  # استفاده از مقدار خام در صورت نامعتبر بودن

                        phone = normalize_phone_number(normalized_phone)

                        # بررسی وجود مخاطب
                        existing_contact = Contact.objects.filter(project=project, phone=phone).first()

                        if existing_contact:
                            # به‌روزرسانی مخاطب موجود
                            existing_contact.full_name = full_name
                            existing_contact.email = clean_string_field(row.get("email"))
                            existing_contact.address = clean_string_field(row.get("address"))

                            # به‌روزرسانی فیلدهای سفارشی
                            custom_fields = {}
                            for col in df.columns:
                                if col not in ["full_name", "phone", "email", "address", "assigned_caller_username"]:
                                    value = clean_string_field(row.get(col))
                                    if value:
                                        custom_fields[col] = value
                            existing_contact.custom_fields = custom_fields

                            # اگر مخاطب موجود تماس‌گیرنده ندارد، برای تخصیص تصادفی اضافه می‌شود
                            if not existing_contact.assigned_caller:
                                unassigned_contacts.append(existing_contact)

                            existing_contact.save()
                            contacts_updated += 1
                            continue

                        # ایجاد مخاطب جدید
                        contact = Contact(
                            project=project,
                            full_name=full_name,
                            phone=phone,
                            email=clean_string_field(row.get("email")),
                            address=clean_string_field(row.get("address")),
                            call_status='pending',
                            is_active=True
                        )

                        # تخصیص تماس‌گیرنده (اگر مشخص شده)
                        assigned_caller_username = clean_string_field(row.get("assigned_caller_username"))
                        if assigned_caller_username:
                            try:
                                assigned_caller = User.objects.get(username=assigned_caller_username)
                                if is_caller_user(assigned_caller):
                                    if ProjectCaller.objects.filter(project=project, caller=assigned_caller, is_active=True).exists():
                                        contact.assigned_caller = assigned_caller
                                    else:
                                        errors.append(f"ردیف {index + 2}: تماس‌گیرنده {assigned_caller_username} در این پروژه فعال نیست.")
                                        unassigned_contacts.append(contact)
                                else:
                                    errors.append(f"ردیف {index + 2}: کاربر {assigned_caller_username} یک تماس‌گیرنده نیست.")
                                    unassigned_contacts.append(contact)
                            except User.DoesNotExist:
                                errors.append(f"ردیف {index + 2}: تماس‌گیرنده با نام کاربری {assigned_caller_username} یافت نشد.")
                                unassigned_contacts.append(contact)
                        else:
                            # اگر تماس‌گیرنده مشخص نشده، به لیست تخصیص تصادفی اضافه می‌شود
                            unassigned_contacts.append(contact)

                        # فیلدهای سفارشی
                        custom_fields = {}
                        for col in df.columns:
                            if col not in ["full_name", "phone", "email", "address", "assigned_caller_username"]:
                                value = clean_string_field(row.get(col))
                                if value:
                                    custom_fields[col] = value
                        contact.custom_fields = custom_fields

                        contact.save()
                        contacts_added += 1

                    except Exception as e:
                        contacts_skipped += 1
                        errors.append(f"ردیف {index + 2}: خطا در پردازش - {str(e)}")
                        logger.error(f"Error processing row {index + 2}: {str(e)}")

            # تخصیص تصادفی مخاطبین بدون تماس‌گیرنده
            auto_assigned_count = 0
            if unassigned_contacts:
                auto_assigned_count, assign_message = assign_contacts_randomly(project, unassigned_contacts)
                # ثبت لاگ برای تخصیص

            # ثبت اطلاعات فایل آپلود شده
            uploaded_file_record = UploadedFile.objects.create(
                project=project,
                file_name=file.name,
                file_path=file_path,
                file_type="contacts",
                uploaded_by=request.user,
                records_count=contacts_added + contacts_updated
            )

            response_data = {
                "message": "فایل با موفقیت پردازش شد.",
                "contacts_added": contacts_added,
                "contacts_updated": contacts_updated,
                "contacts_skipped": contacts_skipped,
                "auto_assigned_count": auto_assigned_count,
                "total_rows": len(df),
                "file_id": uploaded_file_record.id
            }

            if errors:
                response_data["errors"] = errors[:20]  # محدود کردن خطاها به 20 مورد اول
                response_data["total_errors"] = len(errors)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing contacts file: {str(e)}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return Response({"error": f"خطا در پردازش فایل: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExportReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExportReport.objects.all()
    serializer_class = ExportReportSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUser])
    def export_contacts(self, request):
        # Implement export logic here (similar to Flask example)
        return Response({"detail": "Export contacts endpoint not yet implemented."},
                        status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def export_calls(self, request):
        # Implement export logic here (similar to Flask example)
        return Response({"detail": "Export calls endpoint not yet implemented."},
                        status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def download(self, request, pk=None):
        # Implement download logic here (similar to Flask example)
        return Response({"detail": "Download endpoint not yet implemented."}, status=status.HTTP_501_NOT_IMPLEMENTED)


class CachedStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CachedStatistics.objects.all()
    serializer_class = CachedStatisticsSerializer
    permission_classes = [IsAdminUser]
