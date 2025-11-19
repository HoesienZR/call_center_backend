from rest_framework import serializers
from .models import Contact
from calls.models import Call
from projects.models import Project
from users.models import CustomUser
from persiantools.jdatetime import JalaliDate


class ContactSerializer(serializers.ModelSerializer):
    # فیلدهای اضافی برای نمایش بهتر در فرانت‌اند
    assigned_caller_phone = serializers.CharField(source='assigned_caller.phone', read_only=True)
    call_notes = serializers.SerializerMethodField(read_only=True)
    contact_calls_count = serializers.SerializerMethodField(read_only=True)

    # فیلدهایی برای تخصیص تماس‌گیرنده
    caller_phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    persian_updated_at = serializers.SerializerMethodField(read_only=True)
    persian_created_by = serializers.SerializerMethodField(read_only=True)
    contacts_calls_answered_count = serializers.SerializerMethodField(read_only=True)
    contacts_calls_not_answered_count = serializers.SerializerMethodField(read_only=True)
    contacts_calls_rate = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            'id', 'project_id', 'full_name', 'phone', 'email', 'address', 'assigned_caller_id', 'assigned_caller',
            'assigned_caller_phone', 'call_status', 'call_notes', 'custom_fields', 'is_active', 'created_at',
            'updated_at', 'caller_phone_number', 'created_by', "contact_calls_count",
            'contacts_calls_answered_count', 'contacts_calls_not_answered_count',
            'contacts_calls_rate', "is_special", "gender", "birth_date", 'persian_created_by', 'persian_updated_at'
        )
        read_only_fields = ('created_at', 'updated_at', 'created_by')

    def get_contact_calls_count(self, obj):
        """شمارش تعداد تماس‌ها"""
        return obj.calls.count()  # مطمئن شوید که مدل Contact دارای ارتباط با مدل Call است

    def get_persian_updated_at(self, obj):
        """تبدیل تاریخ به فرمت جلالی"""
        return str(JalaliDate(obj.updated_at.date()))

    def get_persian_created_by(self, obj):
        """تبدیل تاریخ به فرمت جلالی برای created_by"""
        return str(JalaliDate(obj.created_at.date()))

    def get_contacts_calls_answered_count(self, obj):
        """تعداد تماس‌های پاسخ داده شده"""
        phone_number = obj.phone
        answered_calls = Call.objects.filter(contact__phone=phone_number, status="answered").count()
        return answered_calls

    def get_contacts_calls_not_answered_count(self, obj):
        """تعداد تماس‌های پاسخ داده نشده"""
        phone_number = obj.phone
        not_answered_calls = Call.objects.filter(contact__phone=phone_number, status="no_answer").count()
        return not_answered_calls

    def get_contacts_calls_rate(self, obj):
        """نرخ تماس‌های پاسخ داده شده"""
        phone_number = obj.phone
        answered_calls = Call.objects.filter(contact__phone=phone_number, status="answered").count()
        total_calls = Call.objects.filter(contact__phone=phone_number).count()

        if total_calls == 0:
            return 0.0

        rate = (answered_calls / total_calls) * 100
        return round(rate, 2)

    def get_call_notes(self, obj):
        """یادداشت‌های تماس"""
        try:
            phone_number = obj.phone
            calls = Call.objects.filter(contact__phone=phone_number).filter(notes__isnull=False).exclude(notes='').order_by('-call_date')

            return [
                {
                    'caller_name': call.caller.get_full_name() if call.caller else 'ناشناس',
                    'note': call.notes,
                    'created_at': str(JalaliDate(call.created_at.date())),
                    'call_result': call.get_call_result_display() if hasattr(call, 'get_call_result_display') else call.call_result
                }
                for call in calls
            ]
        except Exception:
            return []

    def create(self, validated_data):
        """ایجاد مخاطب جدید"""
        user = self.context['request'].user
        project = validated_data.get('project')
        validated_data['created_by'] = user

        # تخصیص تماس‌گیرنده
        caller_phone_number = validated_data.pop('caller_phone_number', None)
        if caller_phone_number and 'assigned_caller' not in validated_data:
            try:
                caller_user = CustomUser.objects.get(phone_number=caller_phone_number)
                if ProjectMembership.objects.filter(project=project, user=caller_user, role__in=['caller', 'admin']).exists():
                    validated_data['assigned_caller'] = caller_user
            except CustomUser.DoesNotExist:
                pass

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """به‌روزرسانی مخاطب"""
        caller_phone_number = validated_data.pop('caller_phone_number', None)
        if caller_phone_number:
            try:
                caller_user = CustomUser.objects.get(phone=caller_phone_number)
                if ProjectMembership.objects.filter(project=instance.project, user=caller_user, role__in=['caller', 'admin']).exists():
                    validated_data['assigned_caller'] = caller_user
            except CustomUser.DoesNotExist:
                pass

        return super().update(instance, validated_data)


class ContactStatsSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_id = serializers.IntegerField(source='project.id', read_only=True)
    total_calls = serializers.SerializerMethodField(read_only=True)
    answered_calls = serializers.SerializerMethodField(read_only=True)
    not_answered_calls = serializers.SerializerMethodField(read_only=True)
    interested_calls = serializers.SerializerMethodField(read_only=True)
    not_interested_calls = serializers.SerializerMethodField(read_only=True)
    no_time_calls = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            "id", "full_name", "phone", "project_id", "project_name",
            "total_calls", "answered_calls", "not_answered_calls",
            "interested_calls", "not_interested_calls", "no_time_calls"
        )

    def get_total_calls(self, obj):
        return Call.objects.filter(contact=obj).count()

    def get_answered_calls(self, obj):
        return Call.objects.filter(contact=obj, status="answered").count()

    def get_not_answered_calls(self, obj):
        return Call.objects.filter(contact=obj, status="no_answer").count()

    def get_interested_calls(self, obj):
        return Call.objects.filter(contact=obj, call_result="interested").count()

    def get_not_interested_calls(self, obj):
        return Call.objects.filter(contact=obj, call_result="not_interested").count()

    def get_no_time_calls(self, obj):
        return Call.objects.filter(contact=obj, call_result="no_time").count()

