from rest_framework.permissions import BasePermission
from .models import UserProfile, ProjectCaller, Project


class IsProjectCaller(BasePermission):
    def has_object_permission(self, request, view, obj:Project):
        try :
            if  request.user in obj.project_callers.caller :
                print(True)
                return True
        except AttributeError:

            return False
#TODO fix this permission
#class IsProjectManager(BasePermission):
#    def has_object_permission(self, request, view, obj:Project):
#        try :
#            request
#            if request.user in obj.proproject :
class IsAdminOrCaller(BasePermission):
    """
    اجازه می‌دهد ادمین یا تماس‌گیرندگان به پروژه‌ها و عملیات مرتبط دسترسی داشته باشند.
    """
    def has_permission(self, request, view):
        # ادمین دسترسی کامل دارد
        if request.user.is_superuser:
            return True
        # تماس‌گیرنده باید نقش 'caller' داشته باشد
        return hasattr(request.user, 'profile') and request.user.profile.role == 'caller'

    def has_object_permission(self, request, view, obj):
        # ادمین دسترسی کامل دارد
        if request.user.is_superuser:
            return True
        # تماس‌گیرنده فقط به پروژه‌های تخصیص‌یافته دسترسی دارد
        if isinstance(obj, Project):
            return ProjectCaller.objects.filter(
                project=obj, caller=request.user, is_active=True
            ).exists()
        return False

class IsRegularUser(BasePermission):
    """
    اجازه می‌دهد کاربران معمولی فقط به مشاهده اطلاعات دسترسی داشته باشند.
    """
    def has_permission(self, request, view):
        # فقط برای متدهای امن (GET, HEAD, OPTIONS)
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return hasattr(request.user, 'profile') and request.user.profile.role == 'regular'
        return False

    def has_object_permission(self, request, view, obj):
        # کاربران معمولی فقط می‌توانند مشاهده کنند
        return request.method in ['GET', 'HEAD', 'OPTIONS']