# call_center/serializers.py
import re

from django.db.models import Count
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
            'phone_number', 'can_create_projects','phone_number'
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
            'contacts_count', 'calls_count', 'completed_calls_count',
            "show"
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

    # فیلدهای اضافی برای نمایش بهتر در فرانت‌اند
    assigned_caller = serializers.SerializerMethodField(read_only=True)
    assigned_caller_phone = serializers.SerializerMethodField(read_only=True)
    can_call = serializers.SerializerMethodField(read_only=True)
    call_statistics = serializers.SerializerMethodField(read_only=True)
    call_notes = serializers.SerializerMethodField(read_only=True)
    # این فیلد برای تخصیص توسط ادمین استفاده می‌شود
    caller_phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    contact_calls_count = serializers.SerializerMethodField()
    contacts_calls_answered_count = serializers.SerializerMethodField()
    contact_calls_not_answered_count = serializers.SerializerMethodField()
    contacts_calls_rate = serializers.SerializerMethodField()
    class Meta:
        model = Contact
        fields = (
            'id', 'project_id', 'full_name', 'phone', 'email',
            'address', 'assigned_caller_id', 'assigned_caller',
            'assigned_caller_phone', 'can_call', 'call_status',
            'call_statistics', 'call_notes', 'custom_fields',
            'is_active', 'created_at', 'updated_at',
            'caller_phone_number', 'created_by',
            "contact_calls_count",'contacts_calls_answered_count',
            'contact_calls_not_answered_count','contacts_calls_rate'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'created_by'
        )
    def get_contacts_calls_answered_count(self,obj):
        phone_number = obj.phone
        answered_calls = Call.objects.filter(
            contact__phone=phone_number,
            status="answered"
        ).count()
        return answered_calls

    def get_contact_calls_not_answered_count(self,obj):
        phone_number = obj.phone
        not_answered_calls = Call.objects.filter(
            contact__phone=phone_number,
            status="not_answered"
        ).count()
        print(not_answered_calls)
        return not_answered_calls

    def get_contact_calls_count(self, obj):
        phone_number = obj.phone
        all_call_count = Call.objects.filter(contact__phone=phone_number).count()

        return all_call_count
    def get_contacts_calls_rate(self,obj):
        phone_number = obj.phone
        answered_calls = Call.objects.filter(
            contact__phone=phone_number,
            status="answered"
        ).count()
        print("answer",answered_calls)
        # تعداد کل تماس‌ها
        total_calls = Call.objects.filter(contact__phone=phone_number).count()

        # تعداد تماس‌های پاسخ داده شده

        # اگر تماسی نباشد، نرخ صفر است
        if total_calls == 0:
            return 0.0
        print("natayeg rate",answered_calls / total_calls)
        # محاسبه درصد و گرد کردن به دو رقم اعشار
        rate = int((answered_calls / total_calls) * 100)
        return rate


    def get_contact_notes(self,obj):
        """تمام یادداشت‌های تماس مرتبط با شماره تلفن این مخاطب"""
        try:
            phone_number = obj.phone
            calls = Call.objects.filter(contact__phone=phone_number).filter(notes__isnull=False).exclude(
                notes='').order_by('-call_date')
            return [
                {
                    'caller_name': call.caller.get_full_name() if call.caller else 'ناشناس',
                    'note': call.notes,
                    'created_at': call.call_date.strftime('%Y-%m-%d %H:%M') if call.call_date else '',
                    'call_result': call.get_call_result_display() if hasattr(call,
                                                                             'get_call_result_display') else call.call_result
                }
                for call in calls
            ]
        except:
            return []

    def get_assigned_caller(self, obj):
        """نام کامل تماس‌گیرنده تخصیص یافته"""
        if obj.assigned_caller:
            return obj.assigned_caller.get_full_name() or obj.assigned_caller.username
        return None

    def get_assigned_caller_phone(self, obj):
        """شماره تلفن تماس‌گیرنده تخصیص یافته"""
        if obj.assigned_caller and hasattr(obj.assigned_caller, 'phone_number'):
            return obj.assigned_caller.phone_number
        return None

    def get_can_call(self, obj):
        """آیا کاربر فعلی می‌تواند با این مخاطب تماس بگیرد"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        user = request.user

        # سوپر یوزر همیشه می‌تواند تماس بگیرد
        if user.is_superuser:
            return True

        # بررسی عضویت در پروژه
        try:
            membership = ProjectMembership.objects.get(project=obj.project, user=user)

            # ادمین یا تماس‌گیرنده تخصیص یافته می‌توانند تماس بگیرند
            if membership.role == 'admin':
                # ادمین فقط با مخاطبین تخصیص یافته به خودش یا بدون تخصیص
                if not obj.assigned_caller or obj.assigned_caller == user:
                    return True
                # اگر ادمین شماره تلفن دارد، با مطابقت شماره تلفن چک کن
                if hasattr(user, 'phone') and user.phone and obj.assigned_caller:
                    user_phone = re.sub(r'\D', '', user.phone)  # حذف کاراکترهای غیر عددی
                    if hasattr(obj.assigned_caller, 'phone') and obj.assigned_caller.phone:
                        assigned_phone = re.sub(r'\D', '', obj.assigned_caller.phone)
                        return user_phone == assigned_phone
                return False

            elif membership.role == 'caller':
                # تماس‌گیرنده فقط با مخاطبین تخصیص یافته به خودش
                return obj.assigned_caller == user

        except ProjectMembership.DoesNotExist:
            pass

        return False

    def get_call_statistics(self, obj):
        """آمار تماس‌های مخاطب"""
        try:
            from django.db.models import Count, Q
            calls = obj.calls.all()

            return {
                'total_calls': calls.count(),
                'answered_calls': calls.filter(call_result='answered').count(),
                'unanswered_calls': calls.filter(call_result='no_answer').count(),
                'unreachable_calls': calls.filter(
                    Q(call_result='unreachable') | Q(call_result='wrong_number')
                ).count(),
            }
        except:
            return {
                'total_calls': 0,
                'answered_calls': 0,
                'unanswered_calls': 0,
                'unreachable_calls': 0,
            }

    def get_call_notes(self, obj):
        """یادداشت‌های تماس"""
        try:
            recent_calls = obj.calls.filter(notes__isnull=False).exclude(notes='').order_by('-call_date')[:5]
            return [
                {
                    'caller_name': call.caller.get_full_name() if call.caller else 'ناشناس',
                    'note': call.notes,
                    'created_at': call.call_date.strftime('%Y-%m-%d %H:%M') if call.call_date else '',
                    'call_result': call.get_call_result_display() if hasattr(call,
                                                                             'get_call_result_display') else call.call_result
                }
                for call in recent_calls
            ]
        except:
            return []

    def validate(self, data):
        """اعتبارسنجی داده‌ها"""
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
        """ایجاد مخاطب جدید"""
        user = self.context['request'].user
        project = validated_data.get('project')

        # کاربر ایجاد کننده را ثبت می‌کنیم
        validated_data['created_by'] = user

        # منطق تخصیص تماس‌گیرنده
        # اگر caller_phone_number داده شده، سعی در یافتن کاربر با آن شماره
        caller_phone_number = validated_data.pop('caller_phone_number', None)
        if caller_phone_number and 'assigned_caller' not in validated_data:
            try:
                # جستجو بر اساس فیلد phone در مدل کاربر
                caller_user = CustomUser.objects.get(phone=caller_phone_number)
                # بررسی عضویت در پروژه
                if ProjectMembership.objects.filter(
                        project=project, user=caller_user, role__in=['caller', 'admin']
                ).exists():
                    validated_data['assigned_caller'] = caller_user
            except CustomUser.DoesNotExist:
                pass  # اگر کاربری یافت نشد، تخصیص انجام نمی‌شود

        # اگر هنوز تخصیص نشده و کاربر ایجادکننده تماس‌گیرنده است
        if 'assigned_caller' not in validated_data:
            try:
                membership = ProjectMembership.objects.get(project=project, user=user)
                if membership.role == 'caller':
                    validated_data['assigned_caller'] = user
            except ProjectMembership.DoesNotExist:
                pass

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """به‌روزرسانی مخاطب"""
        # منطق مشابه create برای caller_phone_number
        caller_phone_number = validated_data.pop('caller_phone_number', None)
        if caller_phone_number:
            try:
                caller_user = CustomUser.objects.get(phone=caller_phone_number)
                if ProjectMembership.objects.filter(
                        project=instance.project, user=caller_user, role__in=['caller', 'admin']
                ).exists():
                    validated_data['assigned_caller'] = caller_user
            except CustomUser.DoesNotExist:
                pass

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


