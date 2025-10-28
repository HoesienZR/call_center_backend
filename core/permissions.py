from rest_framework.permissions import BasePermission, SAFE_METHODS
from contacts.models import Contact
from calls.models import Call
from projects.models import Project, ProjectMembership

class ProjectPermissionMixin:
    """Mixin برای استخراج پروژه از آبجکت و بررسی دسترسی"""
    def get_project(self, obj):
        if isinstance(obj, Project):
            return obj
        if hasattr(obj, 'project'):
            return obj.project
        return None


class IsProjectAdmin(ProjectPermissionMixin, BasePermission):
    """
    دسترسی ادمین پروژه.
    ادمین پروژه دسترسی کامل به آن پروژه و تمام اشیاء مرتبط دارد.
    """
    message = "شما باید ادمین این پروژه باشید تا بتوانید این عملیات را انجام دهید."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project(obj)
        if not project:
            return False

        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='admin'
        ).exists()


class IsProjectCaller(ProjectPermissionMixin, BasePermission):
    """
    دسترسی تماس‌گیرنده پروژه.
    تماس‌گیرنده می‌تواند عملیات مربوط به نقش خود را انجام دهد.
    """
    message = "شما باید به عنوان تماس‌گیرنده به این پروژه تخصیص داده شده باشید."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project(obj)
        if not project:
            return False

        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='caller'
        ).exists()


class IsProjectAdminOrCaller(ProjectPermissionMixin, BasePermission):
    """
    دسترسی ادمین یا تماس‌گیرنده پروژه.
    برای عملیاتی که هر دو می‌توانند انجام دهند.
    """
    message = "شما باید ادمین یا تماس‌گیرنده این پروژه باشید."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project(obj)
        if not project:
            return False

        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role__in=['admin', 'caller']
        ).exists()


class IsReadOnlyOrProjectAdmin(ProjectPermissionMixin, BasePermission):
    """
    دسترسی خواندن برای همه اعضای پروژه، اما نوشتن فقط برای ادمین‌ها.
    """
    message = "فقط ادمین‌های پروژه می‌توانند تغییرات ایجاد کنند."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project(obj)
        if not project:
            return False

        is_member = ProjectMembership.objects.filter(
            project=project,
            user=request.user
        ).exists()

        if request.method in SAFE_METHODS:
            return is_member

        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='admin'
        ).exists()
