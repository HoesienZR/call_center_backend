from django.contrib import admin

from .models import *


# Register your models here.


@admin.register(CallAnswer)
class CallAnswerAdmin(admin.ModelAdmin):
    list_display = ['call', 'question', 'selected_choice']


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل تماس.
    """
    list_display = ('contact', 'caller', 'project', 'call_date', 'call_result', 'status', 'duration', 'created_at')
    list_filter = ('project', 'call_result', 'status', 'call_date')
    search_fields = ('contact__full_name', 'caller__username', 'notes')
    autocomplete_fields = ['contact', 'caller', 'project']
    readonly_fields = ('edited_at', 'edited_by', 'original_data')  # فیلدهای فقط خواندنی


# 3. ثبت سایر مدل‌ها با تنظیمات پیش‌فرض یا ساده
@admin.register(CallEditHistory)
class CallEditHistoryAdmin(admin.ModelAdmin):
    list_display = ('call', 'edited_by', 'edit_date', 'field_name')
    readonly_fields = [field.name for field in CallEditHistory._meta.fields]  # همه فیلدها فقط خواندنی




