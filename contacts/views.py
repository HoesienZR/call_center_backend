import logging
import random
from random import random

import pandas as pd
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.utils import (
    validate_phone_number, normalize_phone_number, clean_string_field
)
from .models import CustomUser as User
from .models import (
    Project, Contact, UploadedFile, ProjectMembership
)
from .permission import IsProjectAdminOrCaller
from .serializers import (
    ContactSerializer,
    CallSerializer
)

# تنظیم logger
logger = logging.getLogger(__name__)


# Create your views here.


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated, IsProjectAdminOrCaller | IsAdminUser]

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    # TODO this also need to get some changes
    def get_queryset(self):
        """
        سفارشی‌سازی کوئری‌ست برای فیلتر مخاطبین بر اساس پروژه، وضعیت تماس و دسترسی کاربر.
        """
        queryset = self.queryset  # e.g., Contact.objects.all()
        user = self.request.user
        status_filter = self.request.query_params.get("status")  # Use 'status', not 'call_status'
        project_id = self.request.query_params.get('project_id')
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                if not (user.is_superuser or ProjectMembership.objects.filter(
                        project=project, user=user
                ).exists()):
                    return Contact.objects.none()

                # بررسی نقش کاربر در پروژه
                is_admin = ProjectMembership.objects.filter(
                    project=project, user=user, role='admin'
                ).exists()

                if user.is_superuser or is_admin:
                    # ادمین همه مخاطبین پروژه را می‌بیند
                    contacts_qs = queryset.filter(project=project)
                else:
                    # تماس‌گیرنده فقط مخاطبین تخصیص‌یافته به خودش را می‌بیند
                    contacts_qs = queryset.filter(
                        project=project,
                        assigned_caller=user
                    )
                contacts_qs = contacts_qs.prefetch_related(
                    'calls__answers__selected_choice',
                    'calls__answers__question',
                    'assigned_caller',
                    'project'
                )
                # Filter on call status if provided (via relation)
                if status_filter:
                    contacts_qs = contacts_qs.filter(call_status=status_filter)
                return contacts_qs

            except Project.DoesNotExist:
                return Contact.objects.none()

        # اگر project_id مشخص نشده، پردازش عادی
        if user.is_superuser:
            contacts_qs = queryset.all()
        else:
            user_projects = Project.objects.filter(members=user)
            is_admin_in_any_project = ProjectMembership.objects.filter(
                project__in=user_projects,
                user=user,
                role='admin'
            ).exists()

            if is_admin_in_any_project:
                contacts_qs = queryset.filter(project__in=user_projects)
            else:
                contacts_qs = queryset.filter(assigned_caller=user)

            # Eager loading (applied globally)
            contacts_qs = contacts_qs.prefetch_related(
                'calls__answers__selected_choice',
                'calls__answers__question',
                'assigned_caller',
                'project'
            )

        # Filter on call status if provided
        if status_filter:
            contacts_qs = contacts_qs.filter(call_status=status_filter)
        return contacts_qs

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

    # TODO maybe this need to get deleted
    @action(detail=False, methods=['post'], url_path='upload-contacts')
    def upload_contacts_file(self, request):
        """
        آپلود فایل اکسل مخاطبین و اتصال آنها به پروژه با تخصیص تصادفی تماس‌گیرندگان
        """
        project_id = request.data.get("project_id")
        if not project_id:
            return Response({"error": "شناسه پروژه الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
            # بررسی دسترسی ادمین بودن در پروژه
            if not (request.user.is_superuser or ProjectMembership.objects.filter(
                    project=project, user=request.user, role='admin'
            ).exists()):
                return Response({
                    "detail": "شما ادمین این پروژه نیستید و نمی‌توانید فایل آپلود کنید."
                }, status=status.HTTP_403_FORBIDDEN)
        except Project.DoesNotExist:
            return Response({"error": "پروژه یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get("file")
        if not file:
            return Response({"error": "فایل ارسال نشده است"}, status=status.HTTP_400_BAD_REQUEST)

        # بررسی نوع فایل
        if not file.name.endswith(('.xlsx', '.xls')):
            return Response({
                "error": "فقط فایل‌های اکسل (.xlsx, .xls) پشتیبانی می‌شوند"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # خواندن فایل اکسل با تنظیمات ویژه برای جلوگیری از NaN
            try:
                df = pd.read_excel(file, na_values=['', ' ', 'NA', 'N/A', 'null'])

                # جایگزینی همه مقادیر NaN با رشته خالی
                df = df.fillna('')

                # تبدیل تمام ستون‌ها به رشته برای جلوگیری از مشکلات نوع داده
                df = df.astype(str)

                # تمیز کردن مقادیر 'nan' string که ممکن است ایجاد شده باشد
                df = df.replace('nan', '')
                df = df.replace('None', '')

            except Exception as e:
                return Response({
                    "error": f"خطا در خواندن فایل اکسل: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)

            # بررسی وجود ستون‌های ضروری
            required_columns = ['phone']
            optional_columns = ['full_name', 'email', 'address', 'custom_fields']

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return Response({
                    "error": f"ستون‌های ضروری موجود نیستند: {', '.join(missing_columns)}",
                    "required_columns": required_columns,
                    "optional_columns": optional_columns,
                    "available_columns": list(df.columns)
                }, status=status.HTTP_400_BAD_REQUEST)

            # دریافت لیست تماس‌گیرندگان فعال پروژه
            project_callers = list(ProjectMembership.objects.filter(
                project=project, role='caller'
            ).select_related('user'))

            if not project_callers:
                return Response({
                    "error": "در این پروژه هیچ تماس‌گیرنده‌ای وجود ندارد"
                }, status=status.HTTP_400_BAD_REQUEST)

            successful_contacts = []
            failed_contacts = []
            updated_contacts = []

            with transaction.atomic():
                # ذخیره اطلاعات فایل آپلود شده
                uploaded_file = UploadedFile.objects.create(
                    file_name=file.name,
                    file_path=f"uploads/contacts/{file.name}",
                    file_type='contacts',
                    records_count=len(df),
                    project=project,
                    uploaded_by=request.user
                )

                for index, row in df.iterrows():
                    try:
                        # تمیز کردن داده‌ها و جلوگیری از مقادیر NaN
                        phone = clean_string_field(str(row.get('phone', '')).strip())
                        full_name = clean_string_field(str(row.get('full_name', '')).strip())
                        email = clean_string_field(str(row.get('email', '')).strip())
                        address = clean_string_field(str(row.get('address', '')).strip())
                        custom_fields = clean_string_field(str(row.get('custom_fields', '')).strip())

                        # اطمینان از اینکه مقادیر 'nan' string تبدیل به رشته خالی شوند
                        if phone.lower() == 'nan':
                            phone = ''
                        if full_name.lower() == 'nan':
                            full_name = ''
                        if email.lower() == 'nan':
                            email = ''
                        if address.lower() == 'nan':
                            address = ''
                        if custom_fields.lower() == 'nan':
                            custom_fields = ''

                        if not phone:
                            failed_contacts.append({
                                'row': index + 2,
                                'data': safe_dict_conversion(row),
                                'error': 'شماره تلفن الزامی است'
                            })
                            continue

                        # اعتبارسنجی شماره تلفن
                        normalized_phone = normalize_phone_number(phone)
                        if not validate_phone_number(normalized_phone):
                            failed_contacts.append({
                                'row': index + 2,
                                'data': safe_dict_conversion(row),
                                'error': 'شماره تلفن نامعتبر است'
                            })
                            continue

                        # اگر نام کامل وجود نداشت
                        if not full_name:
                            full_name = f"مخاطب {normalized_phone}"

                        # بررسی وجود مخاطب
                        existing_contact = Contact.objects.filter(
                            project=project,
                            phone=normalized_phone
                        ).first()

                        if existing_contact:
                            # به‌روزرسانی مخاطب موجود
                            existing_contact.full_name = full_name
                            existing_contact.email = email if email and '@' in email else existing_contact.email
                            existing_contact.address = address or existing_contact.address
                            existing_contact.custom_fields = custom_fields or existing_contact.custom_fields
                            existing_contact.is_active = True

                            if not existing_contact.assigned_caller:
                                random_caller = random.choice(project_callers)
                                existing_contact.assigned_caller = random_caller.user

                            existing_contact.save()

                            updated_contacts.append({
                                'id': existing_contact.id,
                                'full_name': existing_contact.full_name,
                                'phone': existing_contact.phone,
                                'assigned_caller': existing_contact.assigned_caller.get_full_name() if existing_contact.assigned_caller else None,
                                'custom_fields': existing_contact.custom_fields,
                                'action': 'updated'
                            })
                        else:
                            # ایجاد مخاطب جدید
                            random_caller = random.choice(project_callers)
                            normalized_phone = "0" + normalized_phone
                            new_contact = Contact.objects.create(
                                project=project,
                                full_name=full_name,
                                phone=normalized_phone,
                                email=email if email and '@' in email else '',
                                address=address or '',
                                custom_fields=custom_fields or '',
                                assigned_caller=random_caller.user,
                                call_status='pending',
                                created_by=request.user
                            )

                            successful_contacts.append({
                                'id': new_contact.id,
                                'full_name': new_contact.full_name,
                                'phone': new_contact.phone,
                                'assigned_caller': new_contact.assigned_caller.get_full_name(),
                                'assigned_caller_id': new_contact.assigned_caller.id,
                                'custom_fields': new_contact.custom_fields,
                                'action': 'created'
                            })

                    except Exception as e:
                        failed_contacts.append({
                            'row': index + 2,
                            'data': safe_dict_conversion(row),
                            'error': str(e)
                        })

            # آماده کردن پاسخ با تبدیل ایمن به JSON
            response_data = {
                'message': 'فایل مخاطبین با موفقیت پردازش شد',
                'file_id': uploaded_file.id,
                'total_records': len(df),
                'successful_count': len(successful_contacts),
                'updated_count': len(updated_contacts),
                'failed_count': len(failed_contacts),
                'project_id': project.id,
                'project_name': project.name,
                'callers_count': len(project_callers)
            }

            if successful_contacts:
                response_data['successful_contacts'] = successful_contacts

            if updated_contacts:
                response_data['updated_contacts'] = updated_contacts

            if failed_contacts:
                response_data['failed_contacts'] = failed_contacts

            if failed_contacts and not successful_contacts and not updated_contacts:
                status_code = status.HTTP_400_BAD_REQUEST
                response_data['message'] = 'پردازش فایل با خطا مواجه شد'
            elif failed_contacts:
                status_code = status.HTTP_207_MULTI_STATUS
                response_data['message'] = 'فایل با موفقیت جزئی پردازش شد'
            else:
                status_code = status.HTTP_201_CREATED

            return Response(response_data, status=status_code)

        except Exception as e:
            logger.error(f"خطا در پردازش فایل مخاطبین: {str(e)}")
            return Response({
                "error": f"خطای داخلی سرور: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='request_new')
    def request_new_contact(self, request):
        "درخواست مخاطب جدید برای تماس‌گیرنده"
        project_id = request.data.get('project_id')
        if not project_id:
            return Response(
                {"detail": "شناسه پروژه الزامی است."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            project = Project.objects.get(id=project_id)

            # بررسی عضویت کاربر در پروژه
            if not ProjectMembership.objects.filter(
                    project=project, user=request.user
            ).exists():
                return Response(
                    {"detail": "شما عضو این پروژه نیستید."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # یافتن مخاطب آزاد (بدون تخصیص)
            available_contact = Contact.objects.filter(
                project=project,
                assigned_caller__isnull=True,
                call_status='pending',
                is_active=True
            ).first()

            if available_contact:
                # تخصیص مخاطب به کاربر فعلی
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
            return Response(
                {"detail": "پروژه یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='release')
    def release_contact(self, request, pk=None):
        """
        آزاد کردن مخاطب توسط تماس‌گیرنده یا ادمین
        """
        contact = self.get_object()
        user = request.user

        # بررسی دسترسی
        is_admin = ProjectMembership.objects.filter(
            project=contact.project, user=user, role='admin'
        ).exists()

        if contact.assigned_caller == user or is_admin or user.is_superuser:
            contact.assigned_caller = None
            contact.call_status = 'pending'  # بازگشت به حالت در انتظار
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

    # TODO maybe this is also useless
    @action(detail=True, methods=["post"], url_path="remove-assigned-caller")
    def remove_assigned_caller(self, request, pk=None):
        """
        حذف تماس‌گیرنده تخصیص‌یافته از یک مخاطب. فقط ادمین پروژه می‌تواند.
        """
        contact = self.get_object()

        # فقط ادمین پروژه می‌تواند این کار را انجام دهد
        if not (request.user.is_superuser or ProjectMembership.objects.filter(
                project=contact.project,
                user=request.user,
                role='admin'
        ).exists()):
            return Response(
                {"detail": "فقط ادمین پروژه می‌تواند تماس‌گیرنده را حذف کند."},
                status=status.HTTP_403_FORBIDDEN
            )

        contact.assigned_caller = None
        contact.call_status = 'pending'
        contact.save()

        return Response(
            {"detail": "تماس‌گیرنده از مخاطب حذف شد."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"], url_path="submit-call")
    def submit_call(self, request, pk=None):
        """
        ثبت یک تماس جدید برای یک مخاطب
        """
        contact = self.get_object()

        # بررسی دسترسی
        if not (contact.assigned_caller == request.user or
                ProjectMembership.objects.filter(
                    project=contact.project, user=request.user, role='admin'
                ).exists() or request.user.is_superuser):
            return Response(
                {"detail": "شما اجازه ثبت تماس برای این مخاطب را ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )

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

        contact.call_status = status_map.get(call_result, contact.call_status)
        contact.last_call_date = call.call_date
        contact.save()

        return Response(CallSerializer(call).data, status=status.HTTP_201_CREATED)

    # TODO another useless
    @action(detail=False, methods=['get'], url_path="pending_in_project/(?P<project_id>\d+)")
    def pending_contacts_in_project(self, request, project_id=None):
        """
        مخاطبین در انتظار تماس کاربر در یک پروژه خاص
        """
        user = request.user
        pending_contacts = self.get_queryset().filter(
            project_id=project_id,
            assigned_caller=user,
            call_status='pending'
        )
        serializer = self.get_serializer(pending_contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def get_statistics(self, request):
        """
        آمارهای کلی مخاطبین
        """
        project_id = request.query_params.get('project_id')
        user = request.user

        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                # بررسی دسترسی
                if not (user.is_superuser or ProjectMembership.objects.filter(
                        project=project, user=user
                ).exists()):
                    return Response(
                        {"detail": "شما به این پروژه دسترسی ندارید."},
                        status=status.HTTP_403_FORBIDDEN
                    )

                base_queryset = Contact.objects.filter(project=project)
            except Project.DoesNotExist:
                return Response(
                    {"detail": "پروژه یافت نشد."},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # آمار کلی برای کاربر
            base_queryset = self.get_queryset()

        statistics = {
            'total_contacts': base_queryset.count(),
            'pending_contacts': base_queryset.filter(call_status='pending').count(),
            'contacted': base_queryset.filter(call_status='contacted').count(),
            'follow_up': base_queryset.filter(call_status='follow_up').count(),
            'not_interested': base_queryset.filter(call_status='not_interested').count(),
            'assigned_to_me': base_queryset.filter(assigned_caller=user).count() if not user.is_superuser else None,
            'unassigned': base_queryset.filter(assigned_caller__isnull=True).count(),
        }

        return Response(statistics)

    @action(detail=False, methods=['post'], url_path='bulk-assign')
    def bulk_assign_contacts(self, request):
        """
        تخصیص دسته‌ای مخاطبین به تماس‌گیرندگان
        """
        project_id = request.data.get('project_id')
        contact_ids = request.data.get('contact_ids', [])
        caller_id = request.data.get('caller_id')

        if not project_id or not contact_ids:
            return Response(
                {"error": "شناسه پروژه و لیست مخاطبین الزامی است."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            project = Project.objects.get(id=project_id)
            # بررسی دسترسی ادمین
            if not (request.user.is_superuser or ProjectMembership.objects.filter(
                    project=project, user=request.user, role='admin'
            ).exists()):
                return Response(
                    {"detail": "فقط ادمین پروژه می‌تواند مخاطبین را تخصیص دهد."},
                    status=status.HTTP_403_FORBIDDEN
                )

            contacts = Contact.objects.filter(
                id__in=contact_ids,
                project=project
            )

            if caller_id:
                # تخصیص به یک تماس‌گیرنده خاص
                try:
                    caller = User.objects.get(id=caller_id)
                    # بررسی عضویت تماس‌گیرنده در پروژه
                    if not ProjectMembership.objects.filter(
                            project=project, user=caller, role='caller'
                    ).exists():
                        return Response(
                            {"error": "تماس‌گیرنده انتخاب شده عضو این پروژه نیست."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    updated_count = contacts.update(assigned_caller=caller)

                except User.DoesNotExist:
                    return Response(
                        {"error": "تماس‌گیرنده یافت نشد."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # تخصیص تصادفی
                project_callers = list(ProjectMembership.objects.filter(
                    project=project, role='caller'
                ).select_related('user'))

                if not project_callers:
                    return Response(
                        {"error": "در این پروژه هیچ تماس‌گیرنده‌ای وجود ندارد."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                updated_count = 0
                for contact in contacts:
                    random_caller = random.choice(project_callers)
                    contact.assigned_caller = random_caller.user
                    contact.save()
                    updated_count += 1

            return Response({
                "message": f"{updated_count} مخاطب با موفقیت تخصیص یافت.",
                "updated_count": updated_count
            })

        except Project.DoesNotExist:
            return Response(
                {"error": "پروژه یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )
