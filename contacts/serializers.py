from rest_framework import serializers
from .models import Contact
from calls.models import Call
from users.models import CustomUser
from persiantools.jdatetime import JalaliDate
from django.db.models import Count, Q


class ContactSerializer(serializers.ModelSerializer):
    assigned_caller_phone = serializers.CharField(source='assigned_caller.phone', read_only=True)
    call_notes = serializers.SerializerMethodField(read_only=True)
    contact_calls_count = serializers.IntegerField(read_only=True)
    contacts_calls_answered_count = serializers.IntegerField(read_only=True)
    contacts_calls_not_answered_count = serializers.IntegerField(read_only=True)
    contacts_calls_rate = serializers.FloatField(read_only=True)
    persian_updated_at = serializers.SerializerMethodField(read_only=True)
    persian_created_by = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            'id', 'project_id', 'full_name', 'phone', 'email', 'address', 'assigned_caller_id', 'assigned_caller',
            'assigned_caller_phone', 'call_status', 'call_notes', 'custom_fields', 'is_active', 'created_at',
            'updated_at', 'created_by', "contact_calls_count",
            'contacts_calls_answered_count', 'contacts_calls_not_answered_count',
            'contacts_calls_rate', "is_special", "gender", "birth_date", 'persian_created_by', 'persian_updated_at'
        )
        read_only_fields = ('created_at', 'updated_at', 'created_by')

    def get_queryset(self):
        """
        بهینه‌سازی کوئری‌ها با استفاده از annotate برای محاسبات تماس‌ها
        """
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            contact_calls_count=Count('calls'),
            contacts_calls_answered_count=Count('calls', filter=Q(calls__status="answered")),
            contacts_calls_not_answered_count=Count('calls', filter=Q(calls__status="no_answer")),
            contacts_calls_rate=Count('calls', filter=Q(calls__status="answered")) / Count('calls')
        )
        return queryset

    def get_call_notes(self, obj):
        """یادداشت‌های تماس"""
        calls = Call.objects.filter(contact=obj, notes__isnull=False).exclude(notes='').order_by('-call_date')
        return [
            {
                'caller_name': call.caller.get_full_name() if call.caller else 'ناشناس',
                'note': call.notes,
                'created_at': str(JalaliDate(call.created_at.date())),
                'call_result': call.get_call_result_display() if hasattr(call, 'get_call_result_display') else call.call_result
            }
            for call in calls
        ]

    def get_persian_updated_at(self, obj):
        """تبدیل تاریخ به فرمت جلالی"""
        return str(JalaliDate(obj.updated_at.date()))

    def get_persian_created_by(self, obj):
        """تبدیل تاریخ به فرمت جلالی برای created_by"""
        return str(JalaliDate(obj.created_at.date()))

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

    def get_queryset(self):
        """
        بهینه‌سازی کوئری‌ها با استفاده از annotate برای محاسبات تماس‌ها
        """
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            total_calls=Count('calls'),
            answered_calls=Count('calls', filter=Q(calls__status="answered")),
            not_answered_calls=Count('calls', filter=Q(calls__status="no_answer")),
            interested_calls=Count('calls', filter=Q(calls__call_result="interested")),
            not_interested_calls=Count('calls', filter=Q(calls__call_result="not_interested")),
            no_time_calls=Count('calls', filter=Q(calls__call_result="no_time")),
        )
        return queryset

    def get_total_calls(self, obj):
        return obj.total_calls

    def get_answered_calls(self, obj):
        return obj.answered_calls

    def get_not_answered_calls(self, obj):
        return obj.not_answered_calls

    def get_interested_calls(self, obj):
        return obj.interested_calls

    def get_not_interested_calls(self, obj):
        return obj.not_interested_calls

    def get_no_time_calls(self, obj):
        return obj.no_time_calls
