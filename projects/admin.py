from django.contrib import admin
from .models import ProjectMembership, Project

# Register your models here.


class ProjectMembershipInline(admin.TabularInline):
    """
    امکان افزودن و ویرایش اعضای پروژه به صورت مستقیم در صفحه همان پروژه.
    """
    model = ProjectMembership
    extra = 1  # نمایش یک فرم خالی برای افزودن عضو جدید
    autocomplete_fields = ['user']  # برای جستجوی سریع کاربران


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل پروژه.
    """
    list_display = ('name', "id", 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description')
    autocomplete_fields = ['created_by']
    inlines = [ProjectMembershipInline]  # اضافه کردن اعضا به صورت درون‌خطی

@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل عضویت در پروژه.
    """
    list_display = ('project', 'user', 'role', 'assigned_at')
    list_filter = ('role', 'project')
    search_fields = ('project__name', 'user__username')
    autocomplete_fields = ['project', 'user']

