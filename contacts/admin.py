from django.contrib import admin
from .models import Contact, ContactLog

# ثبت مدل مخاطب برای پنل ادمین
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل مخاطب.
    """
    list_display = (
        'full_name', 'phone', 'project', 'call_status', 'assigned_caller',
        'assigned_caller_phone', 'last_call_date', 'birth_date', 'gender'
    )
    list_filter = ('project', 'call_status', 'is_active')
    search_fields = ('full_name', 'phone', 'email', 'project__name')

    # برای بهبود عملکرد، فیلدهای سنگین را در لیست نمایش ندهید
    # raw_id_fields = ('membership',)  # اگر مدل‌های سنگین‌تری دارید که نیاز به نمایش‌ ندارند

    @admin.display(description="شماره تماس‌گیرنده تخصیص داده‌شده")
    def assigned_caller_phone(self, obj):
        """نمایش شماره تلفن تماس‌گیرنده تخصیص داده‌شده"""
        if obj.assigned_caller and hasattr(obj.assigned_caller, "phone_number"):
            return obj.assigned_caller.phone_number
        return "-"

    # استفاده از `list_display_links` برای لینک دار کردن نام کامل
    list_display_links = ('full_name',)

    # بهینه‌سازی عملکرد با `get_queryset` در صورت لزوم
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # می‌توانید فیلترهایی به queryset اضافه کنید
        return queryset

# ثبت مدل ContactLog برای پنل ادمین
@admin.register(ContactLog)
class ContactLogAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل ContactLog.
    """
    list_display = ('contact', 'action', 'performed_by', 'timestamp')
    readonly_fields = [field.name for field in ContactLog._meta.fields]

    # بهینه‌سازی عملکرد با استفاده از `get_queryset`
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # فیلتر کردن به‌صورت دلخواه
        return queryset
