from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

# Register your models here.


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    نمایش مدل کاربر سفارشی در پنل ادمین.
    فیلدهای جدید (phone_number, can_create_projects) به آن اضافه شده است.
    """
    # فیلدهایی که در فرم ویرایش کاربر نمایش داده می‌شوند
    fieldsets = UserAdmin.fieldsets + (
        ('اطلاعات تکمیلی', {'fields': ('phone_number', 'can_create_projects')}),
    )
    # فیلدهایی که هنگام ساخت کاربر جدید نمایش داده می‌شوند
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('اطلاعات تکمیلی', {'fields': ('phone_number', 'can_create_projects')}),
    )
    # فیلدهایی که در لیست کاربران نمایش داده می‌شوند
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'phone_number', 'can_create_projects')
    # فیلدهایی که می‌توان بر اساس آن‌ها جستجو کرد
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
