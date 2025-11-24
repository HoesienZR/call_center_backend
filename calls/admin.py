from django.contrib import admin
from .models import Call, CallAnswer, CallEditHistory

# ثبت مدل CallAnswer
@admin.register(CallAnswer)
class CallAnswerAdmin(admin.ModelAdmin):
    list_display = ['call', 'question', 'selected_choice']
    search_fields = ['call__contact__full_name', 'question__text', 'selected_choice__text']
    list_filter = ('call__project', 'selected_choice')

# ثبت مدل Call
@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('contact', 'caller', 'project', 'call_date', 'call_result', 'status', 'duration', 'created_at')
    list_filter = ('project', 'call_result', 'status', 'call_date')
    search_fields = ('contact__full_name', 'caller__username', 'notes')
    autocomplete_fields = ['contact', 'caller', 'project']  # برای فیلتر کردن پروژه و تماس‌ها
    readonly_fields = ('edited_at', 'edited_by', 'original_data')  # فیلدهای فقط خواندنی
    ordering = ('-call_date',)  # مرتب‌سازی پیش‌فرض بر اساس تاریخ تماس
    list_display_links = ('contact', 'caller')  # لینک دادن به فیلدهای تماس و تماس‌گیرنده

# ثبت مدل CallEditHistory
@admin.register(CallEditHistory)
class CallEditHistoryAdmin(admin.ModelAdmin):
    list_display = ('call', 'edited_by', 'edit_date', 'field_name')
    readonly_fields = [field.name for field in CallEditHistory._meta.fields]
    search_fields = ['call__contact__full_name', 'field_name', 'old_value', 'new_value']
    ordering = ('-edit_date',)
