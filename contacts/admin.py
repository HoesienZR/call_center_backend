from django.contrib import admin

from .models import *


# Register your models here.


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل مخاطب.
    """
    list_display = (
        'full_name', 'phone', 'project', 'call_status', 'assigned_caller', 'assigned_caller_phone', 'last_call_date',
        "birth_date", "gender")
    list_filter = ('project', 'call_status', 'is_active')
    search_fields = ('full_name', 'phone', 'email', 'project__name')

    # برای بهبود عملکرد، فیلدهای سنگین را در لیست نمایش ندهید
    # raw_id_fields = ('membership',)

    @admin.display(description="شماره تماس‌گیرنده تخصیص داده‌شده")
    def assigned_caller_phone(self, obj):
        """نمایش شماره تلفن تماس‌گیرنده تخصیص داده‌شده"""
        if obj.assigned_caller and hasattr(obj.assigned_caller, "phone_number"):
            return obj.assigned_caller.phone_number
        return "-"


@admin.register(ContactLog)
class ContactLogAdmin(admin.ModelAdmin):
    list_display = ('contact', 'action', 'performed_by', 'timestamp')
    readonly_fields = [field.name for field in ContactLog._meta.fields]
