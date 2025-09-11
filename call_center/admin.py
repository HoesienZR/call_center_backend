from django.contrib import admin
from django.contrib.auth.models import User
from .models import (
    Project, ProjectCaller, Contact, Call, CallEditHistory,
    CallStatistics, SavedSearch, UploadedFile, ExportReport, CachedStatistics, UserProfile
)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id','name', 'status', 'created_by', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'created_by']
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user','role']

@admin.register(ProjectCaller)
class ProjectCallerAdmin(admin.ModelAdmin):
    list_display = ['project', 'caller', 'assigned_at', 'is_active']
    list_filter = ['project', 'is_active', 'assigned_at']
    search_fields = ['project__name', 'caller__first_name', 'caller__last_name']
    ordering = ['-assigned_at']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["id",'full_name', 'phone', 'project', 'assigned_caller', 'is_active', 'created_at']
    list_filter = ['project', 'assigned_caller', 'is_active', 'created_at']
    search_fields = ['full_name', 'phone', 'email']
    ordering = ['full_name']
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project', 'assigned_caller')


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['contact', 'caller', 'project', 'call_result', 'call_date', 'duration', 'follow_up_required']
    list_filter = ['call_result', 'follow_up_required', 'project', 'call_date']
    search_fields = ['contact__full_name', 'caller__first_name', 'caller__last_name', 'notes']
    ordering = ['-call_date']
    readonly_fields = ['call_date', 'created_at', 'edited_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('contact', 'caller', 'project')


@admin.register(CallEditHistory)
class CallEditHistoryAdmin(admin.ModelAdmin):
    list_display = ['call', 'edited_by', 'field_name', 'edit_date']
    list_filter = ['field_name', 'edit_date', 'edited_by']
    search_fields = ['call__contact__full_name', 'edited_by__first_name', 'edited_by__last_name']
    ordering = ['-edit_date']
    readonly_fields = ['edit_date']


@admin.register(CallStatistics)
class CallStatisticsAdmin(admin.ModelAdmin):
    list_display = ['contact', 'project', 'total_calls', 'successful_calls', 'response_rate', 'last_call_date']
    list_filter = ['project', 'last_call_date', 'updated_at']
    search_fields = ['contact__full_name', 'project__name']
    ordering = ['-updated_at']
    readonly_fields = ['updated_at']


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ['search_name', 'user', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at', 'user']
    search_fields = ['search_name', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'project', 'file_type', 'uploaded_by', 'records_count', 'upload_date']
    list_filter = ['file_type', 'project', 'upload_date']
    search_fields = ['file_name', 'project__name', 'uploaded_by__first_name', 'uploaded_by__last_name']
    ordering = ['-upload_date']


@admin.register(ExportReport)
class ExportReportAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'project', 'export_type', 'exported_by', 'records_count', 'export_date']
    list_filter = ['export_type', 'project', 'export_date']
    search_fields = ['file_name', 'project__name', 'exported_by__first_name', 'exported_by__last_name']
    ordering = ['-export_date']


@admin.register(CachedStatistics)
class CachedStatisticsAdmin(admin.ModelAdmin):
    list_display = ['stat_type', 'stat_key', 'calculated_at', 'expires_at', 'is_expired']
    list_filter = ['stat_type', 'calculated_at', 'expires_at']
    search_fields = ['stat_type', 'stat_key']
    ordering = ['-calculated_at']
    readonly_fields = ['calculated_at']

    def is_expired(self, obj):
        return obj.is_expired()

    is_expired.boolean = True
    is_expired.short_description = 'منقضی شده'
