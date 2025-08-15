from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Project, ProjectCaller, Contact, Call, CallEditHistory,
    CallStatistics, SavedSearch, UploadedFile, ExportReport, CachedStatistics
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'date_joined', 'last_login'
        )
        read_only_fields = (
            'username', 'email', 'is_staff', 'is_active',
            'date_joined', 'last_login'
        )


class ProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='created_by', write_only=True, required=False
    )

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status', 'created_by',
            'created_by_id', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')


class ProjectCallerSerializer(serializers.ModelSerializer):
    caller = UserSerializer(read_only=True)
    caller_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='caller', write_only=True
    )
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )

    class Meta:
        model = ProjectCaller
        fields = (
            'id', 'project', 'project_id', 'caller', 'caller_id',
            'assigned_at', 'is_active'
        )
        read_only_fields = ('assigned_at',)


class ContactSerializer(serializers.ModelSerializer):
    assigned_caller = UserSerializer(read_only=True)
    assigned_caller_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assigned_caller', write_only=True, allow_null=True, required=False
    )
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )
    custom_fields = serializers.JSONField(binary=False, required=False)

    class Meta:
        model = Contact
        fields = (
            'id', 'project', 'project_id', 'full_name', 'phone', 'email',
            'address', 'assigned_caller', 'assigned_caller_id',
            'custom_fields', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')


class CallSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.all(), source='contact', write_only=True
    )
    caller = UserSerializer(read_only=True)
    caller_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='caller', write_only=True
    )
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )
    edited_by = UserSerializer(read_only=True)
    edited_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='edited_by', write_only=True, allow_null=True, required=False
    )
    original_data = serializers.JSONField(binary=False, required=False)

    class Meta:
        model = Call
        fields = (
            'id', 'contact', 'contact_id', 'caller', 'caller_id', 'project',
            'project_id', 'call_date', 'call_result', 'notes', 'duration',
            'follow_up_required', 'follow_up_date', 'is_editable',
            'edited_at', 'edited_by', 'edited_by_id', 'edit_reason',
            'original_data', 'created_at'
        )
        read_only_fields = ('call_date', 'created_at', 'edited_at')


class CallEditHistorySerializer(serializers.ModelSerializer):
    call = CallSerializer(read_only=True)
    call_id = serializers.PrimaryKeyRelatedField(
        queryset=Call.objects.all(), source='call', write_only=True
    )
    edited_by = UserSerializer(read_only=True)
    edited_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='edited_by', write_only=True
    )

    class Meta:
        model = CallEditHistory
        fields = (
            'id', 'call', 'call_id', 'edited_by', 'edited_by_id',
            'edit_date', 'field_name', 'old_value', 'new_value', 'edit_reason'
        )
        read_only_fields = ('edit_date',)


class CallStatisticsSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.all(), source='contact', write_only=True
    )
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )

    class Meta:
        model = CallStatistics
        fields = (
            'id', 'contact', 'contact_id', 'project', 'project_id',
            'total_calls', 'successful_calls', 'last_call_date',
            'last_call_result', 'response_rate', 'updated_at'
        )
        read_only_fields = (
            'total_calls', 'successful_calls', 'last_call_date',
            'last_call_result', 'response_rate', 'updated_at'
        )


class SavedSearchSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )
    search_criteria = serializers.JSONField(binary=False, required=False)

    class Meta:
        model = SavedSearch
        fields = (
            'id', 'user', 'user_id', 'search_name', 'search_criteria',
            'is_public', 'created_at'
        )
        read_only_fields = ('created_at',)


class UploadedFileSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )
    uploaded_by = UserSerializer(read_only=True)
    uploaded_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='uploaded_by', write_only=True
    )

    class Meta:
        model = UploadedFile
        fields = (
            'id', 'project', 'project_id', 'file_name', 'file_path',
            'file_type', 'uploaded_by', 'uploaded_by_id', 'records_count',
            'upload_date'
        )
        read_only_fields = ('upload_date', 'file_path', 'records_count')


class ExportReportSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True, allow_null=True, required=False
    )
    exported_by = UserSerializer(read_only=True)
    exported_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='exported_by', write_only=True
    )
    filters = serializers.JSONField(binary=False, required=False)

    class Meta:
        model = ExportReport
        fields = (
            'id', 'project', 'project_id', 'exported_by', 'exported_by_id',
            'export_type', 'file_name', 'file_path', 'filters',
            'records_count', 'export_date'
        )
        read_only_fields = ('export_date', 'file_path', 'records_count')


class CachedStatisticsSerializer(serializers.ModelSerializer):
    stat_value = serializers.JSONField(binary=False, required=False)

    class Meta:
        model = CachedStatistics
        fields = (
            'id', 'stat_type', 'stat_key', 'stat_value', 'calculated_at',
            'expires_at'
        )
        read_only_fields = ('calculated_at',)



