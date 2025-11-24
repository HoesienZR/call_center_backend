from rest_framework.permissions import BasePermission
from contacts.models import Project, Contact
from projects.models import ProjectMembership
from rest_framework.permissions import BasePermission

from contacts.models import Project, Contact
from projects.models import ProjectMembership


class IsProjectAdmin(BasePermission):
    def has_permission(self, request, view, ):
        project_id = request.data.get('project_id')
        if id is None:
            return False
        project = Project.objects.get(id=project_id)
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='admin'
        ).exists()


class IsProjectCaller(BasePermission):
    def has_permission(self, request, view, ):
        project_id = request.data.get('project_id')
        if id is None:
            return False
        project = Project.objects.get(id=project_id)
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='caller'
        ).exists()


class ReleaseContactPermission(BasePermission):
    def has_object_permission(self, request, view, obj: Contact):
        if request.user.id == obj.assigned_caller.id:
            return True
