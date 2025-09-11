from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.fields import SerializerMethodField

from .models import (
    Project, ProjectCaller, Contact, Call, CallEditHistory,
    CallStatistics, SavedSearch, UploadedFile, ExportReport, CachedStatistics,UserProfile
)
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'date_joined', 'last_login',
            'profile'
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
    contacts_count = serializers.SerializerMethodField()
    callers_count = serializers.SerializerMethodField()
    completed_calls_count = serializers.SerializerMethodField()
    calls_count = serializers.SerializerMethodField()
    def get_completed_calls_count(self, obj):
        return obj.calls.filter(status="completed").count()
    def get_calls_count(self,obj):
        return obj.calls.count()
    def get_callers_count(self,obj):
        return obj.project_callers.count()
    def get_contacts_count(self,obj):
        return obj.contacts.count()
    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status', 'created_by',
            'created_by_id', 'created_at', 'updated_at',
            'contacts_count',"callers_count",'calls_count',
            "completed_calls_count"

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
    #assigned_caller = UserSerializer(read_only=True)
    assigned_caller_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assigned_caller', write_only=True, allow_null=True, required=False
    )
    #project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )
    custom_fields = serializers.JSONField(binary=False, required=False)
    user_id = serializers.SerializerMethodField()
    class Meta:
        model = Contact
        fields = (
            'id', 'project_id', 'full_name', 'phone', 'email',
            'address', 'assigned_caller_id',"user_id"
            'custom_fields', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, data):
        """
        Ensure project_id is provided and valid.
        """
        if 'project' not in data or data['project'] is None:
            raise serializers.ValidationError({"project_id": "This field is required."})
        return data

    def get_user_id(self, obj):
        return User.objects.get(phone=obj.phone)

# call_center/serializers.py
from rest_framework import serializers
from .models import Call, Contact, Project, User
from .serializers import ContactSerializer, ProjectSerializer, UserSerializer
from django.utils import timezone

# call_center/serializers.py
from rest_framework import serializers
from .models import Call, Contact, Project, User
from .serializers import ContactSerializer, ProjectSerializer, UserSerializer
from django.utils import timezone

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
            'original_data', 'created_at', 'status', 'feedback', 'detailed_report'
        )
        read_only_fields = ('call_date', 'created_at', 'edited_at')

    def validate(self, data):
        # نگاشت result به call_result
        if 'result' in data:
            data['call_result'] = data.pop('result')

        # تنظیم پیش‌فرض برای follow_up_required
        if 'follow_up_required' not in data:
            data['follow_up_required'] = data.get('call_result') == 'callback_requested'

        # نگاشت follow_up_notes به edit_reason
        if 'follow_up_notes' in data:
            data['edit_reason'] = data.pop('follow_up_notes') or ''

        # بررسی وجود contact_id و project_id
        if not data.get('contact') or not data.get('project'):
            raise serializers.ValidationError({"contact_id": "مخاطب و پروژه باید مشخص شوند."})

        # اعتبارسنجی call_status
        valid_statuses = [choice[0] for choice in Call.CALL_STATUS_CHOICES]
        if data.get('status') and data.get('status') not in valid_statuses:
            raise serializers.ValidationError({"status": f"مقدار نامعتبر. باید یکی از {valid_statuses} باشد."})

        # اعتبارسنجی call_result
        valid_results = [choice[0] for choice in Call.CALL_RESULT_CHOICES]
        if data.get('call_result') and data.get('call_result') not in valid_results:
            raise serializers.ValidationError({"call_result": f"مقدار نامعتبر. باید یکی از {valid_results} باشد."})

        # تبدیل follow_up_date به فرمت ISO 8601 اگر DateTimeField باشد
        if data.get('follow_up_date') and isinstance(data['follow_up_date'], str):
            try:
                # اگر تاریخ ساده (YYYY-MM-DD) ارسال شده، به DateTime تبدیل شود
                from datetime import datetime
                date_obj = datetime.strptime(data['follow_up_date'], '%Y-%m-%d')
                data['follow_up_date'] = date_obj.isoformat()  # به فرمت ISO 8601
            except ValueError:
                raise serializers.ValidationError({"follow_up_date": "فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید."})

        return data

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



