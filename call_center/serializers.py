# call_center/serializers.py

from rest_framework import serializers
from django.conf import settings
from .models import (
    CustomUser,
    Project,
    ProjectMembership,
    Contact,
    Call,
    CallEditHistory,
    CallStatistics,
    SavedSearch,
    UploadedFile,
    ExportReport,
    CachedStatistics,
)
from rest_framework import serializers
# 1. سریالایزر برای مدل کاربر سفارشی
class CustomUserSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل CustomUser که شامل فیلدهای سفارشی است.
    """
    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'date_joined', 'last_login',
            'phone_number', 'can_create_projects'
        )
        read_only_fields = (
            'is_staff', 'is_active', 'date_joined', 'last_login'
        )

# 2. سریالایزر برای مدیریت نقش کاربران در پروژه
class ProjectMembershipSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل ProjectMembership.
    """
    user = CustomUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='user', write_only=True
    )
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )

    class Meta:
        model = ProjectMembership
        fields = ('id', 'project_id', 'user', 'user_id', 'role', 'assigned_at')
        read_only_fields = ('assigned_at',)

# 3. سریالایزر پروژه با اطلاعات اعضا
class ProjectSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Project.
    """
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='created_by', write_only=True
    )
    # نمایش اعضای پروژه با نقش‌هایشان
    members = ProjectMembershipSerializer(source='projectmembership_set', many=True, read_only=True)

    # فیلدهای آماری
    contacts_count = serializers.IntegerField(source='contacts.count', read_only=True)
    calls_count = serializers.IntegerField(source='calls.count', read_only=True)
    completed_calls_count = serializers.SerializerMethodField()

    def get_completed_calls_count(self, obj):
        return obj.calls.filter(status="completed").count()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status', 'created_by',
            'created_by_id', 'created_at', 'updated_at', 'members',
            'contacts_count', 'calls_count', 'completed_calls_count'
        )
        read_only_fields = ('created_at', 'updated_at', 'members')


# 4. سریالایزر مخاطبین


# فایل: serializers.py

from rest_framework import serializers
from .models import Contact, Project, CustomUser, ProjectMembership  # ProjectMembership را اضافه کنید


class ContactSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Contact.
    """
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )
    assigned_caller_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='assigned_caller', write_only=True, allow_null=True, required=False
    )
    custom_fields = serializers.JSONField(required=False)
    # این فیلد برای تخصیص توسط ادمین استفاده می‌شود
    caller_phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)

    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            'id', 'project_id', 'full_name', 'phone', 'email',
            'address', 'assigned_caller_id', 'call_status',
            'custom_fields', 'is_active', 'created_at', 'updated_at',
            'caller_phone_number', 'created_by'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'created_by'
        )

    def validate(self, data):
        caller_phone_number = data.get('caller_phone_number')
        # اگر شماره تماس گیرنده ارسال شده باشد، آن را به کاربر تبدیل می‌کنیم
        if caller_phone_number:
            try:
                caller_user = CustomUser.objects.get(phone_number=caller_phone_number)
                data['assigned_caller'] = caller_user
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({
                    'caller_phone_number': 'کاربری با این شماره تماس گیرنده یافت نشد.'
                })

        # بقیه اعتبارسنجی‌ها بدون تغییر باقی می‌مانند
        phone = data.get('phone')
        project = data.get('project')
        if phone and project:
            if self.instance is None:
                if Contact.objects.filter(project=project, phone=phone).exists():
                    raise serializers.ValidationError({
                        'phone': 'مخاطبی با این شماره تلفن در این پروژه قبلاً ثبت شده است.'
                    })
            else:
                if Contact.objects.filter(project=project, phone=phone).exclude(pk=self.instance.pk).exists():
                    raise serializers.ValidationError({
                        'phone': 'مخاطبی با این شماره تلفن در این پروژه قبلاً ثبت شده است.'
                    })

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        project = validated_data.get('project')

        # کاربر ایجاد کننده را ثبت می‌کنیم
        validated_data['created_by'] = user

        # اگر از طریق فیلد caller_phone_number کاربری برای تخصیص مشخص شده، از آن استفاده می‌شود
        # در غیر این صورت، بررسی می‌کنیم که آیا کاربر ایجادکننده، یک تماس‌گیرنده در این پروژه است یا خیر
        if 'assigned_caller' not in validated_data:
            try:
                # بررسی می‌کنیم آیا کاربر عضو پروژه با نقش 'caller' است
                membership = ProjectMembership.objects.get(project=project, user=user)
                if membership.role == 'caller':
                    validated_data['assigned_caller'] = user
            except ProjectMembership.DoesNotExist:
                # اگر کاربر عضو پروژه نباشد، هیچ تخصیصی صورت نمی‌گیرد
                pass

        # فیلد موقت را حذف می‌کنیم
        validated_data.pop('caller_phone_number', None)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # فیلد موقت را در زمان آپدیت نیز حذف می‌کنیم
        validated_data.pop('caller_phone_number', None)
        return super().update(instance, validated_data)


class CallSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Call.
    """
    contact = ContactSerializer(read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.all(), source='contact', write_only=True
    )
    caller = CustomUserSerializer(read_only=True)
    caller_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='caller', write_only=True
    )
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )
    edited_by = CustomUserSerializer(read_only=True)
    edited_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='edited_by', write_only=True, allow_null=True, required=False
    )
    original_data = serializers.JSONField(required=False)

    class Meta:
        model = Call
        fields = (
            'id', 'contact', 'contact_id', 'caller', 'caller_id', 'project',
            'project_id', 'call_date', 'call_result', 'status', 'notes', 'feedback',
            'detailed_report', 'duration', 'follow_up_required', 'follow_up_date',
            'is_editable', 'edited_at', 'edited_by', 'edited_by_id', 'edit_reason',
            'original_data', 'created_at'
        )
        read_only_fields = ('call_date', 'created_at', 'edited_at')

    # متد validate شما بدون تغییر باقی می‌ماند چون منطق درستی دارد
    def validate(self, data):
        # ... (کد validate شما در اینجا قرار می‌گیرد)
        return data


# 6. سایر سریالایزرها با ارجاعات اصلاح شده
class CallEditHistorySerializer(serializers.ModelSerializer):
    edited_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='edited_by', write_only=True
    )
    class Meta:
        model = CallEditHistory
        fields = '__all__'

class CallStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallStatistics
        fields = '__all__'

class SavedSearchSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='user', write_only=True
    )
    search_criteria = serializers.JSONField(required=False)
    class Meta:
        model = SavedSearch
        fields = '__all__'

class UploadedFileSerializer(serializers.ModelSerializer):
    uploaded_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='uploaded_by', write_only=True
    )
    class Meta:
        model = UploadedFile
        fields = '__all__'

class ExportReportSerializer(serializers.ModelSerializer):
    exported_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='exported_by', write_only=True
    )
    filters = serializers.JSONField(required=False)
    class Meta:
        model = ExportReport
        fields = '__all__'

class CachedStatisticsSerializer(serializers.ModelSerializer):
    stat_value = serializers.JSONField(required=False)
    class Meta:
        model = CachedStatistics
        fields = '__all__'


