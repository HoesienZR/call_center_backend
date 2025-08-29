from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from datetime import datetime
import pandas as pd
import os
import uuid
import json
import logging

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


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return self.queryset.filter(created_by=self.request.user)
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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
    permission_classes = [IsAdminUser]


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
        print(user_projects)
        return queryset.filter(project__in=user_projects).filter(
            models.Q(assigned_caller=self.request.user) | models.Q(assigned_caller__isnull=True))
    @action(detail=False,methods=['get'],permission_classes=[IsAuthenticated],url_path="by_projects/(?P<project_id>\d+)",url_name='by-project')
    def get_project_contacts(self,request,project_id=None):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"detail": "پروژه یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        if self.request.user==project.created_by:
            contacts = Contact.objects.filter(project=project)
            print(contacts)
            serializer = ContactSerializer(contacts, many=True)
            return Response(serializer.data)


        else:
            return Response({'detail':"شما به این پروژ دسترسی ندارید "},status=status.HTTP_403_FORBIDDEN)


        pass
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

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
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

        # اولویت ۱: مخاطبین تخصیص داده شده به این تماس‌گیرنده که هنوز تماس گرفته نشده‌اند یا نیاز به پیگیری دارند
        contact = Contact.objects.filter(
            project__in=active_projects,
            assigned_caller=user,
            call_status__in=["pending", "follow_up"]
        ).order_by("last_call_date").first()

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

        feedback_text = request.data.get("feedback_text")
        call_status = request.data.get("call_status")

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
    permission_classes = [IsAdminUser]

    def allowed_file(self, filename):
        return "." in filename and \
            filename.rsplit(".", 1)[1].lower() in ["xlsx", "xls", "csv"]

    def ensure_upload_folder(self):
        upload_path = os.path.join(settings.MEDIA_ROOT, "uploads")
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        return upload_path

    def save_uploaded_file(self, file, project, file_type):
        """ذخیره فایل آپلود شده با نام یکتا"""
        upload_path = self.ensure_upload_folder()

        # ایجاد نام فایل یکتا
        file_extension = file.name.rsplit(".", 1)[1].lower()
        unique_filename = f"{project.id}_{file_type}_{uuid.uuid4().hex[:8]}.{file_extension}"

        fs = FileSystemStorage(location=upload_path)
        filename = fs.save(unique_filename, file)
        return os.path.join(upload_path, filename)

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUser])
    def upload_contacts(self, request):
        if "file" not in request.FILES:
            return Response({"error": "فایل ارسال نشده است"}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        project_id = request.data.get("project_id")
        auto_assign = request.data.get("auto_assign", "false").lower() == "true"

        if not project_id:
            return Response({"error": "شناسه پروژه الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "پروژه یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

        if not self.allowed_file(file.name):
            return Response({"error": "فرمت فایل نامعتبر است. فقط xlsx, xls, csv مجاز هستند."},
                            status=status.HTTP_400_BAD_REQUEST)

        # ذخیره فایل
        file_path = self.save_uploaded_file(file, project, "contacts")

        contacts_added = 0
        contacts_skipped = 0
        contacts_updated = 0
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
                        full_name = clean_string_field(row["full_name"])
                        phone = clean_string_field(row["phone"])

                        if not full_name or not phone:
                            contacts_skipped += 1
                            errors.append(f"ردیف {index + 2}: نام یا شماره تلفن خالی است.")
                            continue

                        # اعتبارسنجی و نرمال‌سازی شماره تلفن
                        is_valid, normalized_phone = validate_phone_number(phone)
                        if not is_valid:
                            contacts_skipped += 1
                            errors.append(f"ردیف {index + 2}: {normalized_phone}")
                            continue

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

                            existing_contact.save()
                            contacts_updated += 1
                            continue

                        # ایجاد مخاطب جدید
                        contact = Contact(
                            project=project,
                            full_name=full_name,
                            phone=phone,
                            email=clean_string_field(row.get("email")),
                            address=clean_string_field(row.get("address"))
                        )

                        # تخصیص تماس‌گیرنده (اگر مشخص شده)
                        assigned_caller_username = clean_string_field(row.get("assigned_caller_username"))
                        if assigned_caller_username:
                            try:
                                assigned_caller = User.objects.get(username=assigned_caller_username)
                                if is_caller_user(assigned_caller):
                                    # بررسی اینکه تماس‌گیرنده در این پروژه فعال است
                                    if ProjectCaller.objects.filter(project=project, caller=assigned_caller,
                                                                    is_active=True).exists():
                                        contact.assigned_caller = assigned_caller
                                    else:
                                        errors.append(
                                            f"ردیف {index + 2}: تماس‌گیرنده {assigned_caller_username} در این پروژه فعال نیست.")
                                else:
                                    errors.append(
                                        f"ردیف {index + 2}: کاربر {assigned_caller_username} یک تماس‌گیرنده نیست.")
                            except User.DoesNotExist:
                                errors.append(
                                    f"ردیف {index + 2}: تماس‌گیرنده با نام کاربری {assigned_caller_username} یافت نشد.")

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

                        # اگر تماس‌گیرنده تخصیص نداده شده، به لیست اضافه کن
                        if not contact.assigned_caller:
                            unassigned_contacts.append(contact)

                    except Exception as e:
                        contacts_skipped += 1
                        errors.append(f"ردیف {index + 2}: خطا در پردازش - {str(e)}")
                        logger.error(f"Error processing row {index + 2}: {str(e)}")

            # تخصیص تصادفی مخاطبین (اگر درخواست شده)
            auto_assigned_count = 0
            if auto_assign and unassigned_contacts:
                auto_assigned_count, assign_message = assign_contacts_randomly(project, unassigned_contacts)

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
                "total_rows": len(df),
                "file_id": uploaded_file_record.id
            }

            if auto_assign:
                response_data["auto_assigned_count"] = auto_assigned_count

            if errors:
                response_data["errors"] = errors[:20]  # محدود کردن خطاها به 20 مورد اول
                response_data["total_errors"] = len(errors)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing contacts file: {str(e)}")
            # حذف فایل در صورت خطا
            if os.path.exists(file_path):
                os.remove(file_path)
            return Response({"error": f"خطا در پردازش فایل: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUser])
    def upload_callers(self, request):
        if "file" not in request.FILES:
            return Response({"error": "فایل ارسال نشده است"}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        project_id = request.data.get("project_id")
        generate_passwords = request.data.get("generate_passwords", "false").lower() == "true"

        if not project_id:
            return Response({"error": "شناسه پروژه الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "پروژه یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

        if not self.allowed_file(file.name):
            return Response({"error": "فرمت فایل نامعتبر است. فقط xlsx, xls, csv مجاز هستند."},
                            status=status.HTTP_400_BAD_REQUEST)

        # ذخیره فایل
        file_path = self.save_uploaded_file(file, project, "callers")

        callers_added = 0
        callers_assigned = 0
        callers_updated = 0
        callers_skipped = 0
        errors = []
        generated_passwords = {}

        try:
            # خواندن فایل
            if file.name.endswith(".csv"):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                df = pd.read_excel(file_path)

            # اعتبارسنجی ساختار فایل
            required_columns = ["username", "full_name"]
            if not generate_passwords:
                required_columns.append("password")

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
                        username = clean_string_field(row["username"])
                        full_name = clean_string_field(row["full_name"])

                        if not username or not full_name:
                            callers_skipped += 1
                            errors.append(f"ردیف {index + 2}: نام کاربری یا نام کامل خالی است.")
                            continue

                        # تولید یا دریافت رمز عبور
                        if generate_passwords:
                            password = generate_secure_password()
                            generated_passwords[username] = password
                        else:
                            password = clean_string_field(row.get("password"))
                            if not password:
                                callers_skipped += 1
                                errors.append(f"ردیف {index + 2}: رمز عبور خالی است.")
                                continue

                        # ایجاد یا به‌روزرسانی کاربر
                        user, created = User.objects.get_or_create(username=username)

                        # تنظیم اطلاعات کاربر
                        name_parts = full_name.split(" ", 1)
                        user.first_name = name_parts[0]
                        user.last_name = name_parts[1] if len(name_parts) > 1 else ""

                        email = clean_string_field(row.get("email"))
                        if email and (not user.email or user.email == ""):
                            user.email = email

                        user.set_password(password)
                        user.is_active = True
                        user.is_staff = False  # تماس‌گیرندگان staff نیستند
                        user.is_superuser = False
                        user.save()

                        if created:
                            callers_added += 1
                        else:
                            callers_updated += 1

                        # تخصیص به پروژه
                        project_caller, assigned_created = ProjectCaller.objects.get_or_create(
                            project=project,
                            caller=user,
                            defaults={'is_active': True}
                        )

                        if assigned_created:
                            callers_assigned += 1
                        elif not project_caller.is_active:
                            project_caller.is_active = True
                            project_caller.save()
                            callers_assigned += 1

                    except Exception as e:
                        callers_skipped += 1
                        errors.append(f"ردیف {index + 2}: خطا در پردازش - {str(e)}")
                        logger.error(f"Error processing caller row {index + 2}: {str(e)}")

            # ثبت اطلاعات فایل آپلود شده
            uploaded_file_record = UploadedFile.objects.create(
                project=project,
                file_name=file.name,
                file_path=file_path,
                file_type="callers",
                uploaded_by=request.user,
                records_count=callers_added + callers_updated
            )

            response_data = {
                "message": "فایل با موفقیت پردازش شد.",
                "callers_added": callers_added,
                "callers_updated": callers_updated,
                "callers_assigned": callers_assigned,
                "callers_skipped": callers_skipped,
                "total_rows": len(df),
                "file_id": uploaded_file_record.id
            }

            if generate_passwords and generated_passwords:
                response_data["generated_passwords"] = generated_passwords
                response_data["password_note"] = "رمزهای عبور تولید شده را در جای امنی ذخیره کنید."

            if errors:
                response_data["errors"] = errors[:20]  # محدود کردن خطاها به 20 مورد اول
                response_data["total_errors"] = len(errors)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing callers file: {str(e)}")
            # حذف فایل در صورت خطا
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
