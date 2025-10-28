import logging
from datetime import datetime

from django.shortcuts import get_object_or_404
from drf_excel.mixins import XLSXFileMixin
from drf_excel.renderers import XLSXRenderer
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from core.permissions import IsProjectAdmin
from calls.models import Call
from core.pagination import LargePageSizePagination
from .models import (
    Project
)
from .serializers import CallStatisticsSerializer, CachedStatisticsSerializer, CallExcelSerializer, \
    ExportReportSerializer

# تنظیم logger
logger = logging.getLogger(__name__)


class CallStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CallStatistics.objects.all()
    serializer_class = CallStatisticsSerializer
    permission_classes = [IsAdminUser]


class ExportReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExportReport.objects.all()
    serializer_class = ExportReportSerializer
    permission_classes = [IsAdminUser]

    # TODO this is useless too
    @action(detail=False, methods=["post"], permission_classes=[IsAdminUser])
    def export_contacts(self, request):
        # Implement export logic here (similar to Flask example)
        return Response({"detail": "Export contacts endpoint not yet implemented."},
                        status=status.HTTP_501_NOT_IMPLEMENTED)

    # TODO this is also useless
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def export_calls(self, request):
        # Implement export logic here (similar to Flask example)
        return Response({"detail": "Export calls endpoint not yet implemented."},
                        status=status.HTTP_501_NOT_IMPLEMENTED)

    # TODO  this useless must get deleted
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def download(self, request, pk=None):
        # Implement download logic here (similar to Flask example)
        return Response({"detail": "Download endpoint not yet implemented."}, status=status.HTTP_501_NOT_IMPLEMENTED)


class CachedStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CachedStatistics.objects.all()
    serializer_class = CachedStatisticsSerializer
    permission_classes = [IsAdminUser]


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


class CallExcelViewSet(XLSXFileMixin, viewsets.ReadOnlyModelViewSet):
    """
    Viewset برای نمایش اطلاعات تماس‌ها.
    """
    renderer_classes = (XLSXRenderer,)
    filename = f'report_in_{datetime.now()}.xlsx'
    pagination_class = LargePageSizePagination
    queryset = Call.objects.select_related('contact', 'project', 'caller', ).prefetch_related('answers__question',
                                                                                              # Fetches Question for each CallAnswer
                                                                                              'answers__selected_choice').all()
    serializer_class = CallExcelSerializer
    permission_classes = [IsAuthenticated, IsAdminUser | IsProjectAdmin]

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
