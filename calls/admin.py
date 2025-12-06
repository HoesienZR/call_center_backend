from django.contrib import admin

from .models import Call, CallAnswer


# Admin configuration for CallAnswer
@admin.register(CallAnswer)
class CallAnswerAdmin(admin.ModelAdmin):
    list_display = ['call', 'question', 'selected_choice']
    search_fields = ['call__contact__full_name', 'question__text', 'selected_choice__text']
    list_filter = ('call__project', 'selected_choice')


# Admin configuration for Call
@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('contact', 'caller', 'project', 'call_date', 'call_result', 'status', 'duration', 'created_at')
    list_filter = ('project', 'call_result', 'status', 'call_date')
    search_fields = ('contact__full_name', 'caller__username', 'notes')
    autocomplete_fields = ['contact', 'caller', 'project']  # Optimizes selection fields
    readonly_fields = ('edited_at', 'edited_by', 'original_data')  # Prevents modification of system fields
    ordering = ('-call_date',)  # Sort by latest call date
    list_display_links = ('contact', 'caller')  # Makes these fields clickable

