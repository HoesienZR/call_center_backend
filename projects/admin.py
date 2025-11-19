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
    list_display = ('name', "id", 'status', 'created_by', 'created_at')  # نمایش فیلدهای اصلی پروژه
    list_filter = ('status', 'created_at')  # فیلتر بر اساس وضعیت و تاریخ ایجاد
    search_fields = ('name', 'description')  # جستجو بر اساس نام و توضیحات
    autocomplete_fields = ['created_by']  # برای جستجوی سریع ایجادکننده پروژه
    inlines = [ProjectMembershipInline]  # اضافه کردن اعضا به صورت درون‌خطی

    def get_full_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    get_full_name.short_description = 'Created By'  # نمایش عنوان مناسب در پنل مدیریت


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل عضویت در پروژه.
    """
    list_display = ('project', 'user', 'role', 'assigned_at')  # نمایش پروژه، کاربر، نقش و تاریخ اختصاص
    list_filter = ('role', 'project')  # فیلتر بر اساس نقش و پروژه
    search_fields = ('project__name', 'user__username')  # جستجو بر اساس نام پروژه و نام کاربری
    autocomplete_fields = ['project', 'user']  # برای جستجوی سریع پروژه و کاربر
