from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from projects.models import Project
from .models import Call
from .serializers import CallSerializer
from .services.call_schema import call_schema, project_filter_schema


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
            # admin همه کال‌ها را می‌تواند ببیند
            return queryset.filter(project_id=project_id) if project_id else queryset

        if project_id:
            project = get_object_or_404(Project, id=project_id)
            if project.created_by == self.request.user:
                return queryset.filter(project=project)
            return queryset.filter(caller=self.request.user, project=project)

        return queryset.filter(caller=self.request.user)

    def perform_create(self, serializer):
        serializer.save(caller=self.request.user)
