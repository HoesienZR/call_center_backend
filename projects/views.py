import logging
from io import BytesIO

import jdatetime
import pandas as pd
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsReadOnlyOrProjectAdmin, IsProjectAdmin
from files.models import Question, UploadedFile
from .serializers import *

logger = logging.getLogger(__name__)


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

    # TODO must  change this and just check this on s
    def perform_create(self, serializer):
        user = self.request.user
        if not user.can_create_projects:
            raise PermissionDenied("شما اجازه ساخت پروژه جدید را ندارید.")

        with transaction.atomic():
            project = serializer.save(created_by=user)
            ProjectMembership.objects.create(project=project, user=user, role='admin')

    # --- اکشن‌های گزارش‌گیری با پرمیشن‌های صحیح ---

    # در ProjectViewSet اضافه کنید:
    # TODO must change to  to drf nested routers
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
                "phone": user.phone_number
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

    # TODO this must change to nested router
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
                        first_name = clean_string_field(str(row.get("first_name", "")))
                        last_name = clean_string_field(str(row.get("last_name", "")))
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
                            user = CustomUser.objects.create(phone_number=normalized_phone, first_name=first_name,
                                                             last_name=last_name,
                                                             username=generate_username(normalized_phone))
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

    # TODO maybe need some changes
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
    # TODO we need to use nested routers in this
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

    # TODO this also need to get deleted
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
    permission_classes = [IsProjectAdmin, IsAuthenticated]
