from datetime import datetime

from django.shortcuts import get_object_or_404
from drf_excel.mixins import XLSXFileMixin
from drf_excel.renderers import XLSXRenderer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from core.pagination import LargePageSizePagination
from core.permissions import IsProjectAdmin, IsAdminOrProjectAdmin
from projects.models import Project, ProjectMembership
from .models import Call
from .serializers import CallSerializer, CallExcelSerializer
from .services.call_schema import call_schema, project_filter_schema, schema_call_excel


@call_schema
class CallViewSet(viewsets.ModelViewSet):
    queryset = Call.objects.select_related('contact', 'caller', 'project', 'edited_by').all()
    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]

    @project_filter_schema
    def get_queryset(self):
        project_id = self.request.GET.get('project_id')
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            return queryset.filter(project_id=project_id) if project_id else queryset

        if project_id:
            project = get_object_or_404(Project, id=project_id)
            if project.created_by == self.request.user:
                return queryset.filter(project=project)
            return queryset.filter(caller=self.request.user, project=project)

        return queryset.filter(caller=self.request.user)

    def perform_create(self, serializer):
        serializer.save(caller=self.request.user)


@schema_call_excel
class CallExcelViewSet(XLSXFileMixin, viewsets.ReadOnlyModelViewSet):
    renderer_classes = (XLSXRenderer,)
    filename = f'report_in_{datetime.now()}.xlsx'
    pagination_class = LargePageSizePagination
    queryset = Call.objects.select_related('contact', 'project', 'caller', ).prefetch_related('answers__question',
                                                                                              'answers__selected_choice').all()
    serializer_class = CallExcelSerializer
    permission_classes = [IsAuthenticated, IsAdminOrProjectAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        project_ids = ProjectMembership.objects.filter(user=user).values_list('project_id', flat=True)
        return self.queryset.filter(project__id__in=project_ids)
