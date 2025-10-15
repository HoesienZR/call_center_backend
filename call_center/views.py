from random import random
from django.db.models import Count, Sum, Avg, Prefetch
import numpy as np
import pandas as pd
from django.db.models import Count, Avg, Sum, Q, F, Case, When, IntegerField, FloatField
from django.db.models.functions import Coalesce
from django.db.models import Count, Avg, Q
from django.db.models.aggregates import Sum
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.db import transaction, models
from datetime import datetime
from .permission import  IsProjectCaller, IsProjectAdmin, IsProjectAdminOrCaller, IsReadOnlyOrProjectAdmin
from .models import CustomUser as User, Question, CallAnswer, Ticket
import logging
import random
from django.db import connections
from django.http import HttpResponse
from rest_framework.pagination import PageNumberPagination
from .models import (
    Project, ProjectCaller, Contact, Call, CallEditHistory,
    CallStatistics, SavedSearch, UploadedFile, ExportReport, CachedStatistics, ProjectMembership, CustomUser
)
from .serializers import (
    CustomUserSerializer, ProjectSerializer, ContactSerializer,
    CallSerializer, CallEditHistorySerializer, CallStatisticsSerializer,
    SavedSearchSerializer, UploadedFileSerializer, ExportReportSerializer, CachedStatisticsSerializer,
    CustomUserSerializer, CallExcelSerializer, AnswerChoiceSerializer,TicketSerializer
)
from .utils import (
    validate_phone_number, normalize_phone_number, generate_secure_password,
    is_caller_user, assign_contacts_randomly, validate_excel_data, clean_string_field,generate_username
)
from drf_excel.mixins import XLSXFileMixin
from drf_excel.renderers import XLSXRenderer
import traceback
from rest_framework.views import APIView
from rest_framework import status, permissions
from .excel_imports import import_contacts_from_excel

from django.shortcuts import get_object_or_404
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
    """
    ViewSet برای مشاهده کاربران.
    """
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


def safe_dict_conversion(row):
    """
    تبدیل ایمن pandas Series به dictionary با جلوگیری از مقادیر NaN
    """
    try:
        if hasattr(row, 'to_dict'):
            row_dict = row.to_dict()
            # تبدیل همه مقادیر NaN به رشته خالی
            for key, value in row_dict.items():
                if pd.isna(value) or (isinstance(value, float) and np.isnan(value)):
                    row_dict[key] = ''
                else:
                    row_dict[key] = str(value)
            return row_dict
        else:
            return str(row)
    except Exception:
        return "خطا در تبدیل داده"


def clean_string_field(value):
    """
    تمیز کردن و اعتبارسنجی فیلدهای رشته‌ای
    """
    if pd.isna(value) or value is None:
        return ''

    # تبدیل به رشته
    str_value = str(value).strip()

    # حذف مقادیر نامعتبر
    if str_value.lower() in ['nan', 'none', 'null', '']:
        return ''

    return str_value


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsReadOnlyOrProjectAdmin]

    def get_queryset(self):
        user = self.request.user
        base_prefetch = [
            Prefetch(
                'questions',
                queryset=Question.objects.prefetch_related('choices')
            ),
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
    #TODO must  change this and just check this on s
    def perform_create(self, serializer):
        user = self.request.user
        if not user.can_create_projects:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("شما اجازه ساخت پروژه جدید را ندارید.")

        with transaction.atomic():
            project = serializer.save(created_by=user)
            ProjectMembership.objects.create(project=project, user=user, role='admin')


    # --- اکشن‌های گزارش‌گیری با پرمیشن‌های صحیح ---
    # در ProjectViewSet اضافه کنید:

    # در ProjectViewSet اضافه کنید:
    #TODO must change to  to drf nested routers
    @action(detail=True, methods=['get'], url_path='user-role',
            permission_classes=[IsAuthenticated])
    def get_user_role(self, request, pk=None):
        """
        دریافت نقش کاربر فعلی در پروژه مشخص شده
        GET /api/projects/{project_id}/user-role/
        """
        project = self.get_object()
        user = request.user


        # بررسی عضویت کاربر در پروژه
        try:

            membership = ProjectMembership.objects.get(project=project, user=user)

            return Response({
                'project_id': project.id,
                'project_name': project.name,
                'user_id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'role': membership.role,
                'role_display': membership.get_role_display(),
                'assigned_at': membership.assigned_at,
                'is_admin': membership.role == 'admin',
                'is_caller': membership.role == 'caller',
                'is_contact': membership.role == 'contact',
                "phone":user.phone_number
            }, status=status.HTTP_200_OK)

        except ProjectMembership.DoesNotExist:
            # اگر کاربر superuser باشد ولی عضو پروژه نباشد
            if user.is_superuser:
                return Response({
                    'project_id': project.id,
                    'project_name': project.name,
                    'user_id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name() or user.username,
                    'role': 'superuser',
                    'role_display': 'مدیر کل سیستم',
                    'assigned_at': None,
                    'is_admin': True,
                    'is_caller': False,
                    'is_contact': False
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'detail': 'شما عضو این پروژه نیستید'
                }, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get'], url_path='export-caller-performance',
            permission_classes=[IsAuthenticated, IsProjectAdmin])
    def export_caller_performance(self, request, pk=None):
        """
        خروجی اکسل از گزارش عملکرد تماس‌گیرندگان پروژه
        GET /api/projects/{project_id}/export-caller-performance/
        """
        project = self.get_object()

        try:
            # دریافت گزارش عملکرد تماس‌گیرندگان
            caller_performance = project.get_caller_performance_report()

            if not caller_performance:
                return Response({
                    'error': 'هیچ تماس‌گیرنده‌ای برای این پروژه یافت نشد'
                }, status=status.HTTP_404_NOT_FOUND)

            import pandas as pd
            from io import BytesIO
            from django.http import HttpResponse
            import jdatetime

            # تبدیل داده‌ها به DataFrame
            df_data = []
            for caller in caller_performance:
                # تبدیل ثانیه به دقیقه و ثانیه برای نمایش بهتر
                total_minutes = int(caller['total_duration_seconds'] // 60)
                total_seconds = int(caller['total_duration_seconds'] % 60)
                avg_minutes = int(caller['average_call_duration_seconds'] // 60)
                avg_seconds = int(caller['average_call_duration_seconds'] % 60)

                df_data.append({
                    'شناسه تماس‌گیرنده': caller['caller_id'],
                    'نام کاربری': caller['caller_username'],
                    'نام کامل': caller['caller_full_name'],
                    'تعداد کل تماس‌ها': caller['total_calls'],
                    'تماس‌های پاسخ داده شده': caller['answered_calls'],
                    'نرخ موفقیت (درصد)': f"{caller['success_rate']}%",
                    'مدت کل تماس‌ها (دقیقه:ثانیه)': f"{total_minutes}:{total_seconds:02d}",
                    'میانگین مدت تماس (دقیقه:ثانیه)': f"{avg_minutes}:{avg_seconds:02d}",
                    'مدت کل تماس‌ها (ثانیه)': caller['total_duration_seconds'],
                    'میانگین مدت تماس (ثانیه)': caller['average_call_duration_seconds']
                })

            df = pd.DataFrame(df_data)

            # ایجاد فایل اکسل در حافظه
            output = BytesIO()

            # استفاده از xlsxwriter برای کنترل بیشتر روی فرمت
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='گزارش عملکرد تماس‌گیرندگان', index=False)

                # دریافت workbook و worksheet برای فرمت‌بندی
                workbook = writer.book
                worksheet = writer.sheets['گزارش عملکرد تماس‌گیرندگان']

                # تنظیم فرمت هدرها
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })

                # تنظیم فرمت سلول‌های عادی
                cell_format = workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1
                })

                # فرمت برای اعداد درصد
                percent_format = workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1,
                    'fg_color': '#E8F4FD'
                })

                # اعمال فرمت به هدرها
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # تنظیم عرض ستون‌ها
                worksheet.set_column('A:A', 12)  # شناسه تماس‌گیرنده
                worksheet.set_column('B:B', 15)  # نام کاربری
                worksheet.set_column('C:C', 20)  # نام کامل
                worksheet.set_column('D:D', 12)  # تعداد کل تماس‌ها
                worksheet.set_column('E:E', 18)  # تماس‌های پاسخ داده شده
                worksheet.set_column('F:F', 15)  # نرخ موفقیت
                worksheet.set_column('G:G', 20)  # مدت کل تماس‌ها
                worksheet.set_column('H:H', 25)  # میانگین مدت تماس
                worksheet.set_column('I:I', 20)  # مدت کل (ثانیه)
                worksheet.set_column('J:J', 25)  # میانگین (ثانیه)

                # اعمال فرمت به سلول‌ها
                for row_num in range(1, len(df) + 1):
                    for col_num in range(len(df.columns)):
                        if col_num == 5:  # ستون نرخ موفقیت
                            worksheet.write(row_num, col_num, df.iloc[row_num - 1, col_num], percent_format)
                        else:
                            worksheet.write(row_num, col_num, df.iloc[row_num - 1, col_num], cell_format)

                # اضافه کردن اطلاعات پروژه در بالای فایل
                worksheet.insert_rows(0, 3)

                # فرمت برای اطلاعات پروژه
                project_info_format = workbook.add_format({
                    'bold': True,
                    'font_size': 12,
                    'fg_color': '#4F81BD',
                    'font_color': 'white'
                })

                # تاریخ فعلی
                current_date = jdatetime.datetime.now().strftime('%Y/%m/%d - %H:%M')

                worksheet.write('A1', f'گزارش عملکرد تماس‌گیرندگان پروژه: {project.name}', project_info_format)
                worksheet.write('A2', f'تاریخ تهیه گزارش: {current_date}', project_info_format)
                worksheet.write('A3', f'تعداد کل تماس‌گیرندگان: {len(caller_performance)}', project_info_format)

                # ادغام سلول‌ها برای اطلاعات پروژه
                worksheet.merge_range('A1:J1', f'گزارش عملکرد تماس‌گیرندگان پروژه: {project.name}', project_info_format)
                worksheet.merge_range('A2:J2', f'تاریخ تهیه گزارش: {current_date}', project_info_format)
                worksheet.merge_range('A3:J3', f'تعداد کل تماس‌گیرندگان: {len(caller_performance)}',
                                      project_info_format)

            output.seek(0)

            # تنظیم نام فایل با تاریخ
            persian_date = jdatetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"گزارش_عملکرد_تماس_گیرندگان_{project.name}_{persian_date}.xlsx"

            # ایجاد پاسخ HTTP با فایل اکسل
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            logger.error(f"خطا در ایجاد فایل اکسل گزارش عملکرد: {str(e)}")
            return Response({
                'error': f'خطا در ایجاد فایل اکسل: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #TODO this must change to nested router
    @action(detail=False, methods=['post'], url_path='check-user-role',
            permission_classes=[IsAuthenticated])
    def check_user_role(self, request):
        """
        بررسی نقش کاربر مشخص شده در پروژه مشخص شده
        POST /api/projects/check-user-role/
        Body: {"project_id": 1, "user_id": 2}
        """
        project_id = request.data.get('project_id')
        user_id = request.data.get('user_id')

        if not project_id:
            return Response({
                'error': 'شناسه پروژه الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not user_id:
            return Response({
                'error': 'شناسه کاربر الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
            target_user = CustomUser.objects.get(id=user_id)
        except Project.DoesNotExist:
            return Response({
                'error': 'پروژه یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'کاربر یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)

        # بررسی دسترسی - فقط ادمین پروژه یا superuser می‌تواند نقش سایرین را بررسی کند
        requesting_user = request.user
        if not requesting_user.is_superuser:
            try:
                requesting_membership = ProjectMembership.objects.get(
                    project=project, user=requesting_user
                )
                if requesting_membership.role != 'admin':
                    return Response({
                        'detail': 'فقط ادمین پروژه می‌تواند نقش سایر کاربران را بررسی کند'
                    }, status=status.HTTP_403_FORBIDDEN)
            except ProjectMembership.DoesNotExist:
                return Response({
                    'detail': 'شما عضو این پروژه نیستید'
                }, status=status.HTTP_403_FORBIDDEN)

        # بررسی عضویت کاربر هدف در پروژه
        try:
            membership = ProjectMembership.objects.get(project=project, user=target_user)
            return Response({
                'project_id': project.id,
                'project_name': project.name,
                'user_id': target_user.id,
                'username': target_user.username,
                'full_name': target_user.get_full_name() or target_user.username,
                'role': membership.role,
                'role_display': membership.get_role_display(),
                'assigned_at': membership.assigned_at,
                'is_admin': membership.role == 'admin',
                'is_caller': membership.role == 'caller',
                'is_contact': membership.role == 'contact'
            }, status=status.HTTP_200_OK)

        except ProjectMembership.DoesNotExist:
            # اگر کاربر هدف superuser باشد ولی عضو پروژه نباشد
            if target_user.is_superuser:
                return Response({
                    'project_id': project.id,
                    'project_name': project.name,
                    'user_id': target_user.id,
                    'username': target_user.username,
                    'full_name': target_user.get_full_name() or target_user.username,
                    'role': 'superuser',
                    'role_display': 'مدیر کل سیستم',
                    'assigned_at': None,
                    'is_admin': True,
                    'is_caller': False,
                    'is_contact': False
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'project_id': project.id,
                    'project_name': project.name,
                    'user_id': target_user.id,
                    'username': target_user.username,
                    'full_name': target_user.get_full_name() or target_user.username,
                    'role': None,
                    'role_display': 'عضو نیست',
                    'assigned_at': None,
                    'is_admin': False,
                    'is_caller': False,
                    'is_contact': False,
                    'is_member': False
                }, status=status.HTTP_200_OK)
    @action(detail=True, methods=["post"], url_path='upload-callers')
    def upload_callers(self, request, pk=None):
        """
        آپلود فایل اکسل کاربران موجود بر اساس شماره تلفن و اضافه کردن آنها به عنوان تماس‌گیرنده پروژه
        """
        project = self.get_object()

        # بررسی دسترسی ادمین بودن در پروژه
        if not (request.user.is_superuser or ProjectMembership.objects.filter(
                project=project, user=request.user, role='admin'
        ).exists()):
            return Response({
                "detail": "شما ادمین این پروژه نیستید و نمی‌توانید تماس‌گیرنده اضافه کنید."
            }, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get("file")
        if not file:
            return Response({"error": "فایل ارسال نشده است"}, status=status.HTTP_400_BAD_REQUEST)

        # بررسی نوع فایل
        if not file.name.endswith(('.xlsx', '.xls')):
            return Response({
                "error": "فقط فایل‌های اکسل (.xlsx, .xls) پشتیبانی می‌شوند"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            import pandas as pd

            # خواندن فایل اکسل
            try:
                df = pd.read_excel(file)
            except Exception as e:
                return Response({
                    "error": f"خطا در خواندن فایل اکسل: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)
            # بررسی وجود ستون شماره تلفن
            if ('phone_number' and "first_name" and "last_name" not in df.columns):
                return Response({
                    "error": "ستون های  ';last_name','first_name',' phone_number'  الزامی است",
                    "required_columns": ["phone_number"],
                    "available_columns": list(df.columns)
                }, status=status.HTTP_400_BAD_REQUEST)

            successful_callers = []
            failed_callers = []
            updated_callers = []

            with transaction.atomic():
                # ذخیره اطلاعات فایل آپلود شده
                uploaded_file = UploadedFile.objects.create(
                    file_name=file.name,
                    file_path=f"uploads/callers/{file.name}",
                    file_type='callers',
                    records_count=len(df),
                    project=project,
                    uploaded_by=request.user
                )

                for index, row in df.iterrows():
                    try:
                        # تمیز کردن شماره تلفن
                        phone_number = clean_string_field(str(row.get('phone_number', '')))
                        first_name = clean_string_field(str(row.get("first_name","")))
                        last_name = clean_string_field(str(row.get("last_name","")))
                        if not phone_number or phone_number == 'nan':
                            failed_callers.append({
                                'row': index + 2,
                                'phone_number': phone_number,
                                'error': 'شماره تلفن الزامی است'
                            })
                            continue


                        # نرمال‌سازی و اعتبارسنجی شماره تلفن
                        try:
                            normalized_phone = normalize_phone_number(phone_number)
                            if not validate_phone_number(normalized_phone):
                                failed_callers.append({
                                    'row': index + 2,
                                    'phone_number': phone_number,
                                    'error': 'شماره تلفن نامعتبر است'
                                })
                                continue
                        except:
                            failed_callers.append({
                                'row': index + 2,
                                'phone_number': phone_number,
                                'error': 'شماره تلفن نامعتبر است'
                            })
                            continue

                        # جستجوی کاربر بر اساس شماره تلفن
                        try:
                            normalized_phone = "0" + normalized_phone
                            user = CustomUser.objects.get(phone_number=normalized_phone)
                        except CustomUser.DoesNotExist:
                            user = CustomUser.objects.create(phone_number=normalized_phone,first_name=first_name,
                                                             last_name=last_name,username=generate_username(normalized_phone))
                        # بررسی اینکه آیا کاربر قبلاً عضو پروژه است
                        existing_membership = ProjectMembership.objects.filter(
                            project=project,
                            user=user
                        ).first()

                        if existing_membership:
                            # اگر قبلاً عضو است، نقشش را به caller تغییر می‌دهیم
                            old_role = existing_membership.role
                            if old_role != 'caller':
                                existing_membership.role = 'caller'
                                existing_membership.save()

                                updated_callers.append({
                                    'user_id': user.id,
                                    'username': user.username,
                                    'full_name': user.get_full_name() or user.username,
                                    'phone_number': user.phone_number,
                                    'old_role': old_role,
                                    'new_role': 'caller',
                                    'action': 'role_updated'
                                })
                            else:
                                # اگر قبلاً تماس‌گیرنده بوده، در لیست به‌روزرسانی قرار نمی‌گیرد
                                updated_callers.append({
                                    'user_id': user.id,
                                    'username': user.username,
                                    'full_name': user.get_full_name() or user.username,
                                    'phone_number': user.phone_number,
                                    'old_role': old_role,
                                    'new_role': 'caller',
                                    'action': 'already_caller'
                                })
                        else:
                            # اضافه کردن کاربر جدید به پروژه با نقش caller
                            ProjectMembership.objects.create(
                                project=project,
                                user=user,
                                role='caller'
                            )

                            successful_callers.append({
                                'user_id': user.id,
                                'username': user.username,
                                'full_name': user.get_full_name() or user.username,
                                'phone_number': user.phone_number,
                                'role': 'caller',
                                'action': 'added_to_project'
                            })

                    except Exception as e:
                        failed_callers.append({
                            'row': index + 2,
                            'phone_number': phone_number if 'phone_number' in locals() else 'نامشخص',
                            'error': str(e)
                        })

            # آماده کردن پاسخ
            response_data = {
                'message': 'فایل تماس‌گیرندگان با موفقیت پردازش شد',
                'file_id': uploaded_file.id,
                'total_records': len(df),
                'successful_count': len(successful_callers),
                'updated_count': len(updated_callers),
                'failed_count': len(failed_callers),
                'project_id': project.id,
                'project_name': project.name
            }

            if successful_callers:
                response_data['successful_callers'] = successful_callers

            if updated_callers:
                response_data['updated_callers'] = updated_callers

            if failed_callers:
                response_data['failed_callers'] = failed_callers

            # تنظیم وضعیت پاسخ
            if failed_callers and not successful_callers and not updated_callers:
                status_code = status.HTTP_400_BAD_REQUEST
                response_data['message'] = 'پردازش فایل با خطا مواجه شد'
            elif failed_callers:
                status_code = status.HTTP_207_MULTI_STATUS
                response_data['message'] = 'فایل با موفقیت جزئی پردازش شد'
            else:
                status_code = status.HTTP_201_CREATED

            return Response(response_data, status=status_code)

        except Exception as e:
            logger.error(f"خطا در پردازش فایل تماس‌گیرندگان: {str(e)}")
            return Response({
                "error": f"خطای داخلی سرور: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #TODO maybe need some changes
    @action(detail=True, methods=['post'], url_path='toggle-user-role',
            permission_classes=[IsAuthenticated, IsProjectAdmin])
    def toggle_user_role(self, request, pk=None):
        """
        تغییر نقش کاربر مشخص شده بین caller و contact در یک پروژه
        فقط ادمین پروژه می‌تواند نقش سایر کاربران را تغییر دهد
        کاربر ادمین در درخواست user_id کاربر دیگری را ارسال می‌کند
        """
        project = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({
                'error': 'شناسه کاربر الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # پیدا کردن کاربر
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'کاربر یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            # پیدا کردن عضویت کاربر در پروژه
            membership = ProjectMembership.objects.get(project=project, user=user)
        except ProjectMembership.DoesNotExist:
            return Response({
                'error': 'کاربر عضو این پروژه نیست'
            }, status=status.HTTP_404_NOT_FOUND)

        # بررسی اینکه نقش فعلی admin نباشد
        if membership.role == 'admin':
            return Response({
                'error': 'نمی‌توان نقش ادمین را تغییر داد'
            }, status=status.HTTP_400_BAD_REQUEST)

        # تغییر نقش
        with transaction.atomic():
            old_role = membership.role

            if membership.role == 'caller':
                # تغییر از caller به contact
                new_role = 'contact'

                # آزاد کردن تمام مخاطبینی که به این کاربر تخصیص داده شده‌اند
                assigned_contacts = Contact.objects.filter(
                    project=project,
                    assigned_caller=user
                )
                assigned_contacts_count = assigned_contacts.count()
                assigned_contacts.update(assigned_caller=None)

            elif membership.role == 'contact':
                # تغییر از contact به caller
                new_role = 'caller'
                assigned_contacts_count = 0

            else:
                return Response({
                    'error': f'نقش {membership.role} قابل تغییر نیست'
                }, status=status.HTTP_400_BAD_REQUEST)

            # به‌روزرسانی نقش
            membership.role = new_role
            membership.save()

            # لاگ کردن تغییرات
        response_data = {
            'message': 'نقش کاربر با موفقیت تغییر یافت',
            'user_id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'old_role': old_role,
            'new_role': new_role,
            'new_role_display': membership.get_role_display()
        }

        # اگر از caller به contact تغییر یافت، تعداد مخاطبین آزاد شده را اضافه کن
        if old_role == 'caller' and assigned_contacts_count > 0:
            response_data['released_contacts_count'] = assigned_contacts_count
            response_data['message'] += f' و {assigned_contacts_count} مخاطب آزاد شد'

        return Response(response_data, status=status.HTTP_200_OK)

    # اضافه کردن این اکشن به ProjectViewSet موجود
    #TODO we need to use nested routers in this
    @action(detail=True, methods=['get'], url_path='members',
            permission_classes=[IsAuthenticated, IsProjectAdmin])
    def get_project_members(self, request, pk=None):
        """
        دریافت لیست اعضای یک پروژه با اطلاعات کامل
        """
        project = self.get_object()
        # دریافت تمام اعضای پروژه از طریق ProjectMembership
        memberships = ProjectMembership.objects.filter(project=project).exclude(role="admin").select_related('user')

        members_data = []
        for membership in memberships:
            user = membership.user
            members_data.append({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name() if user.get_full_name() else user.username,
                'phone_number': user.phone_number,
                'role': membership.role,
                'role_display': membership.get_role_display(),
                'assigned_at': membership.assigned_at,
                'email': user.email
            })

        return Response({
            'project_id': project.id,
            'project_name': project.name,
            'members_count': len(members_data),
            'members': members_data
        }, status=status.HTTP_200_OK)
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsProjectAdminOrCaller])
    def statistics(self, request, pk=None):
        project = self.get_object()
        stats = project.get_statistics()
        return Response(stats)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsProjectAdmin])
    def caller_performance(self, request, pk=None):
        project = self.get_object()
        report = project.get_caller_performance_report()
        return Response(report)
    #TODO this also need to get deleted
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsProjectAdminOrCaller])
    def call_status_over_time(self, request, pk=None):
        project = self.get_object()
        # ... (منطق این اکشن از کد قبلی شما بدون تغییر باقی می‌ماند)
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

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsProjectAdmin])
    def export_report(self, request, pk=None):
        # این اکشن نیاز به تغییر نداشت و منطق آن درست است.
        # ... (کد کامل این اکشن از کد قبلی شما در اینجا قرار می‌گیرد)
        project = self.get_object()
        # ...
        return Response({"message": "گزارش با موفقیت ایجاد شد.", "download_url": "..."})


class ProjectCallerViewSet(viewsets.ModelViewSet):
    queryset = ProjectCaller.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsProjectAdmin,IsAuthenticated]


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated, IsProjectAdminOrCaller]

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }
    #TODO this also need to get some changes
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
                    contacts_qs = contacts_qs.filter(calls__status=status_filter)
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
            contacts_qs = contacts_qs.filter(calls__status=status_filter)
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
        """
        درخواست مخاطب جدید برای تماس‌گیرنده
        """
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
class CallViewSet(viewsets.ModelViewSet):
    queryset = Call.objects.all()
    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.GET.get('project_id')
        if project_id :
            project  = get_object_or_404(Project,id=project_id)
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        if project_id and project.created_by == self.request.user:
            return queryset.filter(project=project)
        # Callers can only see their own calls
        return queryset.filter(caller=self.request.user)

    def perform_create(self, serializer):
        serializer.save(caller=self.request.user)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_call(self, request):
        """
        ایجاد یک تماس جدید با بازخورد
        """
        contact_id = request.data.get('callecaller_id') or request.data.get('contact_id')
        project_id = request.data.get('project_id')


        if not contact_id:
            return Response({"error": "contact_id الزامی است"}, status=400)

        try:
            print(contact_id)
            contact = Contact.objects.get(id=contact_id)
            print("contact")
            project = Project.objects.get(id=project_id) if project_id else None
            print("project")
        except (Contact.DoesNotExist, Project.DoesNotExist):
            return Response({"error": "Contact یا Project یافت نشد"}, status=404)

        serializer_data = { "contact":contact_id,
            "caller_id":request.user.id,
            "project":project_id,
            "status":request.data.get('status', 'completed'),
            "call_result":request.data.get('call_result'),
            "notes":request.data.get('notes', ''),
            "duration":request.data.get('duration', 0),
            "follow_up_required":request.data.get('call_result') == 'callback_requested',
            "follow_up_date":request.data.get('follow_up_date'),
        }
        serializer_data.update({k: v for k, v in request.data.items() if k not in serializer_data})
        call_serializer = CallSerializer(data=serializer_data)
        if call_serializer.is_valid(raise_exception=True):
            call_serializer.save(caller_id=self.request.user.id)
            return Response(call_serializer.data, status=status.HTTP_201_CREATED)

        return Response(call_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
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
    permission_classes = [IsAuthenticated, IsProjectAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return UploadedFile.objects.all()
        admin_projects = Project.objects.filter(projectmembership__user=user, projectmembership__role='admin')
        return UploadedFile.objects.filter(project__in=admin_projects)

    @action(detail=False, methods=["post"], url_path='contacts')
    def upload_contacts(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return Response({"error": "شناسه پروژه الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
            # بررسی دسترسی ادمین بودن در پروژه
            if not (request.user.is_superuser or ProjectMembership.objects.filter(project=project, user=request.user,
                                                                                  role='admin').exists()):
                return Response({"detail": "شما ادمین این پروژه نیستید و نمی‌توانید فایل آپلود کنید."},
                                status=status.HTTP_403_FORBIDDEN)
        except Project.DoesNotExist:
            return Response({"error": "پروژه یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

        # --- اینجا کد کامل و پیچیده آپلود فایل از کد قبلی شما قرار می‌گیرد ---
        # این کد نیاز به تغییرات جزئی داشت تا به جای ProjectCaller از ProjectMembership استفاده کند.
        # من این تغییرات را اعمال کرده‌ام.

        file = request.FILES.get("file")
        if not file:
            return Response({"error": "فایل ارسال نشده است"}, status=status.HTTP_400_BAD_REQUEST)

        # ... (کد کامل پردازش فایل اکسل و ساخت مخاطبین) ...
        # در بخش تخصیص تماس‌گیرنده:
        # به جای: if is_caller_user(assigned_caller) and ProjectCaller.objects.filter(...)
        # استفاده کنید از:
        # if ProjectMembership.objects.filter(project=project, user=assigned_caller, role='caller').exists():
        #     contact.assigned_caller = assigned_caller
        # else:
        #     errors.append(...)

        # و در بخش تخصیص تصادفی:
        # به جای: assign_contacts_randomly(project, unassigned_contacts)
        # این تابع باید بازنویسی شود تا لیست تماس‌گیرندگان را از ProjectMembership بخواند.

        return Response({"message": "فایل با موفقیت پردازش شد."})  # پیام موفقیت‌آمیز


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


def assign_contacts_randomly(project, contacts_list):
    """
    تخصیص تصادفی مخاطبین به تماس‌گیرندگان پروژه
    """
    project_callers = list(ProjectMembership.objects.filter(
        project=project, role='caller'
    ).values_list('user_id', flat=True))

    if not project_callers:
        return False

    import random
    for contact in contacts_list:
        if not contact.assigned_caller:
            random_caller_id = random.choice(project_callers)
            contact.assigned_caller_id = random_caller_id
            contact.save()

    return True


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_dashboard_data(request):
    if not request.user.is_staff:
        return Response({'error': 'Access denied'}, status=403)
    start_date = request.data.get('start_date')  # میلادی: "2025-03-14"
    end_date = request.data.get('end_date')  # میلادی: "2025-03-21"
    # فیلتر تاریخی
    calls_qs = Call.objects.all()
    if start_date:
        calls_qs = calls_qs.filter(call_date__gte=start_date)
    if end_date:
        calls_qs = calls_qs.filter(call_date__lte=end_date)

    # 1. Overview Statistics
    total_projects = Project.objects.filter(status='active').count()
    total_calls = calls_qs.count()
    total_callers = CustomUser.objects.filter(
        projectmembership__role='caller'
    ).distinct().count()
    successful_calls = calls_qs.filter(status='answered').count()
    success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0


    # 2. Project Statistics
    project_stats = []
    project_stats = []
    projects = Project.objects.filter(status='active')
    for project in projects:
        project_calls = calls_qs.filter(project=project)
        total_calls_proj = project_calls.count()
        successful_calls_proj = project_calls.filter(status='answered').count()
        project_stats.append({
            'name': project.name,
            'total_calls': total_calls_proj,
            'successful_calls': successful_calls_proj
        })

    # 3. Call Status Distribution
    call_status_distribution = []
    status_counts = calls_qs.values('call_result').annotate(count=Count('id'))

    status_mapping = {
        'answered': 'موفق',
        'no_answer': 'ناموفق',
        'busy': 'مشغول',
        'unreachable': 'در دسترس نیست',
        'wrong_number': 'خطا'
    }

    for status in status_counts:
        call_status_distribution.append({
            'name': status_mapping.get(status['call_result'], status['call_result']),
            'value': status['count']
        })
    total_no_time_count = call_status_distribution[0]['value']
    total_not_intrested_count = call_status_distribution[1]['value']
    total_intrested_count = call_status_distribution[2]['value']
    no_time_rate = (total_no_time_count / total_calls) * 100 if total_calls > 0 else 0
    not_intrested_rate = (total_not_intrested_count / total_calls) * 100 if total_calls > 0 else 0
    intersted_rate = (total_intrested_count / total_calls) * 100 if total_calls > 0 else 0
    call_status_distribution[0]['value'] =  no_time_rate
    call_status_distribution[1]['value'] = not_intrested_rate
    call_status_distribution[2]['value'] = intersted_rate
    # 4. Call Trends
    call_trends = calls_qs.extra(
        select={'date': 'DATE(call_date)'}
    ).values('date').annotate(
        calls=Count('id'),
        successful=Count('id', filter=Q(call_result='answered'))
    ).order_by('date')

    # 5. Caller Performance
    caller_performance = []
    callers = CustomUser.objects.filter(projectmembership__role='caller').distinct()
    for caller in callers:
        caller_calls = calls_qs.filter(caller=caller)
        total_calls_caller = caller_calls.count()
        successful_calls_caller = caller_calls.filter(call_result='answered').count()
        avg_duration = caller_calls.aggregate(Avg('duration'))['duration__avg'] or 0
        success_rate_caller = (successful_calls_caller / total_calls_caller * 100) if total_calls_caller > 0 else 0

        caller_performance.append({
            'name': caller.get_full_name() or caller.username,
            'total_calls': total_calls_caller,
            'successful_calls': successful_calls_caller,
            'success_rate': round(success_rate_caller, 1),
            'avg_duration': round(avg_duration / 60, 1) if avg_duration else 0 ,
            #"successful_calls_rate": 0  if total_calls_caller==0 else  total_calls_caller;# دقیقه
        })

    return Response({
        'success': True,
        'data': {
            'total_projects': total_projects,
            'total_calls': total_calls,
            'total_callers': total_callers,
            'success_rate': round(success_rate, 1),
            'projectStats': project_stats,
            "projectLength":len(project_stats),
            'callStatusDistribution': call_status_distribution,
            'callTrends': list(call_trends),
            'callerPerformance': caller_performance,
            "no_time_rate" : no_time_rate,
            "not_intrested_rate":not_intrested_rate,
            "intersted_rate" : intersted_rate
        }
    })
class LargePageSizePagination(PageNumberPagination):
    page_size = 100000
    page_size_query_param = 'page_size'
    max_page_size = 100000
class CallExcelViewSet(XLSXFileMixin,viewsets.ReadOnlyModelViewSet):
    """
    Viewset برای نمایش اطلاعات تماس‌ها.
    """
    renderer_classes = (XLSXRenderer,)
    filename = f'report_in_{datetime.now()}.xlsx'
    pagination_class = LargePageSizePagination
    queryset = Call.objects.select_related('contact', 'project', 'caller',).prefetch_related('answers__question',  # Fetches Question for each CallAnswer
            'answers__selected_choice').all()
    serializer_class = CallExcelSerializer
    permission_classes = [IsAuthenticated,IsAdminUser | IsProjectAdmin]
    def get_queryset(self):
        """
        فیلتر کردن تماس‌ها بر اساس کاربر واردشده (فقط تماس‌های پروژه‌هایی که کاربر در آن‌ها عضو است).
        """
        user = self.request.user
        if user.is_superuser:

            return self.queryset
        # دریافت پروژه‌هایی که کاربر در آن‌ها نقش دارد
        project_ids = ProjectMembership.objects.filter(user=user).values_list('project_id', flat=True)
        return self.queryset.filter(project__id__in=project_ids)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dashboard_data(request):
    """
    Simple dashboard data endpoint - returns raw data for client-side filtering
    """
    project_id = request.GET.get('project_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # بررسی دسترسی کاربر
    user = request.user
    if not (user.is_superuser or user.is_staff):
        # محدود کردن به پروژه‌هایی که کاربر در آن‌ها ادمین است
        admin_projects = ProjectMembership.objects.filter(
            user=user, role='admin'
        ).values_list('project_id', flat=True)

        if not admin_projects:
            return Response({
                'error': 'شما اجازه دسترسی به این گزارش را ندارید'
            }, status=status.HTTP_403_FORBIDDEN)

    # شروع query اصلی
    calls_query = Call.objects.all().select_related('caller', 'project', 'contact')

    # اعمال فیلترهای تاریخی
    if start_date:
        calls_query = calls_query.filter(call_date__gte=start_date)
    if end_date:
        calls_query = calls_query.filter(call_date__lte=end_date)

    # فیلتر پروژه خاص
    if project_id:
        calls_query = calls_query.filter(project_id=project_id)

    # محدود کردن دسترسی برای کاربران غیر ادمین
    if not (user.is_superuser or user.is_staff):
        calls_query = calls_query.filter(project__in=admin_projects)

    # Get all data without filtering - let client handle filtering
    all_calls = Call.objects.all().select_related('contact', 'project', 'caller')
    all_projects = Project.objects.all()
    all_callers = CustomUser.objects.filter(projectmembership__role='caller')

    intersted_calls = all_calls.filter(call_result='interested').count()
    if all_calls.count() == 0:
        success_rate = 0
    else:
        success_rate = intersted_calls / all_calls.count() * 100

    # عملکرد تماس‌گیرندگان - استفاده از query بهبود یافته
    caller_stats = calls_query.values(
        'caller__id',
        'caller__username',
        'caller__first_name',
        'caller__last_name',
        'caller__phone_number'
    ).annotate(
        # تعداد کل تماس‌ها
        total_calls=Count('id'),

        # تماس‌های پاسخ داده شده (status='answered')
        answered_calls=Count(
            Case(
                When(status='answered', then=1),
                output_field=IntegerField()
            )
        ),

        # تماس‌های موفق (call_result='interested')
        successful_calls=Count(
            Case(
                When(call_result='interested', then=1),
                output_field=IntegerField()
            )
        ),

        # مجموع مدت تماس‌ها (به ثانیه)
        total_duration_seconds=Coalesce(Sum('duration'), 0),

        # میانگین مدت تماس (فقط برای تماس‌های پاسخ داده شده)
        avg_call_duration_seconds=Coalesce(
            Avg('duration', filter=Q(status='answered')), 0.0
        ),

        # تعداد پروژه‌های مختلف که در آن‌ها تماس گرفته
        project_count=Count('project', distinct=True)

    ).annotate(
        # نرخ پاسخ‌دهی (درصد تماس‌هایی که پاسخ داده شد)
        response_rate=Case(
            When(total_calls=0, then=0.0),
            default=F('answered_calls') * 100.0 / F('total_calls'),
            output_field=FloatField()
        ),

        # نرخ موفقیت (درصد تماس‌های موفق از کل تماس‌ها)
        success_rate=Case(
            When(total_calls=0, then=0.0),
            default=F('successful_calls') * 100.0 / F('total_calls'),
            output_field=FloatField()
        ),

        # نرخ تبدیل (درصد تماس‌های موفق از تماس‌های پاسخ داده شده)
        conversion_rate=Case(
            When(answered_calls=0, then=0.0),
            default=F('successful_calls') * 100.0 / F('answered_calls'),
            output_field=FloatField()
        )
    ).order_by('-total_calls')

    # تبدیل نتایج به فرمت مطلوب
    caller_performance_data = []

    for caller in caller_stats:
        # ساخت نام کامل
        full_name = f"{caller['caller__first_name'] or ''} {caller['caller__last_name'] or ''}".strip()
        if not full_name:
            full_name = caller['caller__username']

        # تبدیل ثانیه به دقیقه:ثانیه برای نمایش بهتر
        total_minutes = int(caller['total_duration_seconds'] // 60)
        total_seconds = int(caller['total_duration_seconds'] % 60)

        avg_minutes = int(caller['avg_call_duration_seconds'] // 60)
        avg_seconds_remainder = int(caller['avg_call_duration_seconds'] % 60)

        caller_performance_data.append({
            'caller_id': caller['caller__id'],
            'name': full_name,
            'username': caller['caller__username'],
            'phone_number': caller['caller__phone_number'],
            'total_calls': caller['total_calls'],
            'answered_calls': caller['answered_calls'],
            'successful_calls': caller['successful_calls'],
            'response_rate': round(caller['response_rate'], 2),
            'success_rate': round(caller['success_rate'], 2),
            'conversion_rate': round(caller['conversion_rate'], 2),
            'avg_call_duration_formatted': f"{avg_minutes}:{avg_seconds_remainder:02d}",
            'avg_call_duration_seconds': round(caller['avg_call_duration_seconds'], 2),
            'total_duration_formatted': f"{total_minutes}:{total_seconds:02d}",
            'total_duration_seconds': caller['total_duration_seconds'],
            'project_count': caller['project_count'],
            # برای سازگاری با کد قبلی
            'total_calls_all_projects': caller['total_calls'],
            'total_successful_calls_all_projects': caller['successful_calls'],
            'total_answered_calls_all_projects': caller['answered_calls'],
            'total_duration_all_projects': caller['total_duration_seconds'],
            'overall_response_rate': round(caller['response_rate'], 2),
            'overall_success_rate': round(caller['success_rate'], 2),
            'overall_conversion_rate': round(caller['conversion_rate'], 2),
            'overall_avg_duration': round(caller['avg_call_duration_seconds'], 2)
        })

    # Basic stats
    dashboard_data_response = {
        'total_projects': all_projects.count(),
        'total_calls': all_calls.count(),
        'total_callers': all_callers.count(),
        'success_rate': success_rate,

        # Project stats - raw data
        'projectStats': [
            {
                'id': project.id,
                'name': project.name,
                'total_calls': project.calls.count(),
                'successful_calls': project.calls.filter(call_result='interested').count()
            }
            for project in all_projects
        ],

        # Call status distribution - raw counts
        'callStatusDistribution': [
            {'name': 'interested', 'count': all_calls.filter(call_result='interested').count()},
            {'name': 'not_interested', 'count': all_calls.filter(call_result='not_interested').count()},
            {'name': 'no_time', 'count': all_calls.filter(call_result='no_time').count()},
        ],

        # Call trends - raw data by date
        'callTrends': list(
            all_calls.extra(select={'date': 'DATE(call_date)'})
            .values('date')
            .annotate(
                calls=Count('id'),
                successful=Count('id', filter=Q(call_result='interested'))
            )
            .order_by('date')
        ),

        # Caller performance - بر اساس query جدید
        'callerPerformance': caller_performance_data
    }

    return Response(dashboard_data_response)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_statistics_api(request, project_id):
    """
    API برای دریافت آمار کامل پروژه شامل آمار کلی و عملکرد تماس‌گیرندگان
    """
    try:
        # دریافت پروژه
        project = get_object_or_404(Project, id=project_id)

        # بررسی دسترسی کاربر به پروژه
        if not has_project_access(request.user, project):
            return Response(
                {"error": "شما دسترسی به این پروژه ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )

        # آمار کلی پروژه
        general_stats = get_project_general_statistics(project)

        # عملکرد تماس‌گیرندگان
        caller_performance = get_caller_performance(project)

        response_data = {
            "project_id": project.id,
            "project_name": project.name,
            "general_statistics": general_stats,
            "caller_performance": caller_performance
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Project.DoesNotExist:
        return Response(
            {"error": "پروژه مورد نظر یافت نشد."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"خطا در دریافت آمار: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def has_project_access(user, project):
    """بررسی دسترسی کاربر به پروژه"""
    if user.is_superuser:
        return True

    # بررسی عضویت در پروژه
    return ProjectMembership.objects.filter(
        project=project,
        user=user
    ).exists()


def get_project_general_statistics(project):
    """دریافت آمار کلی پروژه"""

    # تعداد کل مخاطبین
    total_contacts = project.contacts.filter(is_active=True).count()

    # تعداد کل تماس‌ها
    total_calls = project.calls.count()

    # تماس‌های موفق (نتیجه interested)
    successful_calls = project.calls.filter(call_result='interested').count()

    # تماس‌های پاسخ داده شده (وضعیت answered)
    answered_calls = project.calls.filter(status='answered').count()

    # محاسبه نرخ‌ها
    success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
    answer_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0

    return {
        "total_contacts": total_contacts,
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "answered_calls": answered_calls,
        "success_rate": round(success_rate, 2),
        "answer_rate": round(answer_rate, 2)
    }


def get_caller_performance(project):
    """دریافت عملکرد تماس‌گیرندگان پروژه"""

    # دریافت همه تماس‌گیرندگانی که در این پروژه تماس گرفته‌اند
    callers_with_calls = User.objects.filter(
        calls__project=project
    ).distinct()

    caller_performance = []

    for caller in callers_with_calls:
        # تماس‌های این تماس‌گیرنده در این پروژه
        caller_calls = project.calls.filter(caller=caller)

        # آمارهای پایه
        total_calls = caller_calls.count()

        # تماس‌های با نتایج مختلف
        interested_calls = caller_calls.filter(call_result='interested').count()
        no_time_calls = caller_calls.filter(call_result='no_time').count()
        not_interested_calls = caller_calls.filter(call_result='not_interested').count()

        # تماس‌های با وضعیت‌های مختلف
        answered_calls = caller_calls.filter(status='answered').count()
        no_answer_calls = caller_calls.filter(status='no_answer').count()
        wrong_number_calls = caller_calls.filter(status='wrong_number').count()
        pending_calls = caller_calls.filter(status='pending').count()

        # مدت زمان مکالمه (فقط برای تماس‌هایی که duration دارند)
        duration_stats = caller_calls.exclude(duration__isnull=True).aggregate(
            total_duration=Sum('duration'),
            avg_duration=Avg('duration')
        )

        total_duration = duration_stats['total_duration'] or 0
        avg_duration = duration_stats['avg_duration'] or 0

        # محاسبه نرخ‌ها
        success_rate = (interested_calls / total_calls * 100) if total_calls > 0 else 0
        answer_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0

        # تبدیل مدت زمان از ثانیه به دقیقه و ثانیه
        avg_duration_formatted = format_duration(avg_duration)
        total_duration_formatted = format_duration(total_duration)

        caller_data = {
            "caller_id": caller.id,
            "first_name": caller.first_name,
            "last_name": caller.last_name,
            "full_name": caller.get_full_name(),
            "username": caller.username,
            "phone_number": getattr(caller, 'phone_number', ''),
            "total_calls": total_calls,

            # تماس‌های بر اساس نتیجه
            "interested_calls": interested_calls,
            "no_time_calls": no_time_calls,
            "not_interested_calls": not_interested_calls,

            # تماس‌های بر اساس وضعیت
            "answered_calls": answered_calls,
            "no_answer_calls": no_answer_calls,
            "wrong_number_calls": wrong_number_calls,
            "pending_calls": pending_calls,

            # نرخ‌ها
            "success_rate": round(success_rate, 2),  # نرخ علاقه‌مندی
            "answer_rate": round(answer_rate, 2),  # نرخ پاسخ‌دهی

            # مدت زمان
            "total_duration_seconds": total_duration,
            "avg_duration_seconds": round(avg_duration, 2),
            "total_duration_formatted": total_duration_formatted,
            "avg_duration_formatted": avg_duration_formatted,

            # جزئیات اضافی
            "calls_with_duration": caller_calls.exclude(duration__isnull=True).count()
        }

        caller_performance.append(caller_data)

    # مرتب‌سازی بر اساس تعداد تماس‌های موفق (علاقه‌مند) نزولی
    caller_performance.sort(key=lambda x: x['interested_calls'], reverse=True)

    return caller_performance


def format_duration(seconds):
    """تبدیل ثانیه به فرمت دقیقه:ثانیه"""
    if not seconds:
        return "00:00"

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    project_count = Project.objects.count()
    calls_count = Call.objects.count()
    answered_calls_count = Call.objects.filter(status='answered').count()
    pending_calls_count = Call.objects.filter(status='pending').count()
    result = {"project_count":project_count,
              "calls_count":calls_count,
              "answered_calls_count":answered_calls_count,
              "pending_calls_count":pending_calls_count,
    }
    return Response(result,status=status.HTTP_200_OK)



class ContactImportView(APIView):
    """
    ایمپورت مخاطبین از فایل اکسل برای یک پروژه خاص
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def post(self, request, project_id):
        """
        آپلود فایل اکسل و افزودن مخاطبین جدید.
        اگر تماس‌گیرنده وجود داشته باشد، اختصاص داده می‌شود.
        """
        project = get_object_or_404(Project, id=project_id)
        file_obj = request.FILES.get("file")

        if not file_obj:
            return Response(
                {"error": "فایل اکسل ارسال نشده است."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            created_contacts = import_contacts_from_excel(file_obj, project)
            return Response(
                {
                    "message": f"{len(created_contacts)} مخاطب با موفقیت اضافه شد.",
                    "created_count": len(created_contacts),
                    "contacts": created_contacts,  # شامل شماره و نام
                    "project": project.name,
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            traceback.print_exc()
            return Response(
                {"error": f"خطا در پردازش فایل: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch
from .models import Question, AnswerChoice  # Adjust imports as needed
from .serializers import QuestionSerializer  # Assumes writable serializer with nested choices

class QuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing questions associated with a project.
    """
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated,IsProjectAdmin|IsAdminUser]  # Customize, e.g., add IsProjectAdmin

    def get_queryset(self):
        """
        Retrieve questions for the specific project from the URL.
        """
        project_id = self.kwargs['project_pk']
        return Question.objects.filter(project_id=project_id).prefetch_related(
            Prefetch('choices', queryset=AnswerChoice.objects.all())
        )

    def perform_create(self, serializer):
        """
        Automatically link the created question to the project.
        """
        project_id = self.kwargs['project_pk']
        serializer.save(project_id=project_id)

class AnswerChoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing answer choices associated with a question.
    """
    serializer_class = AnswerChoiceSerializer  # Writable serializer
    permission_classes = [IsAuthenticated,IsProjectAdmin|IsAdminUser]

    def get_queryset(self):
        """
        Retrieve answer choices for the specific question from the URL.
        """
        question_id = self.kwargs['question_pk']
        return AnswerChoice.objects.filter(question_id=question_id)

    def perform_create(self, serializer):
        """
        Automatically link the created answer choice to the question.
        """
        question_id = self.kwargs['question_pk']
        serializer.save(question_id=question_id)

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes =[IsAuthenticated]
    queryset = Ticket.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)