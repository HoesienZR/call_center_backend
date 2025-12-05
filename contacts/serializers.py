from django.db.models import Count, Q
from persiantools.jdatetime import JalaliDate
from rest_framework import serializers

from users.models import CustomUser
from .models import Contact, ContactLog


class ContactSerializer(serializers.ModelSerializer):
    # اطلاعات تماس‌گیرنده
    assigned_caller_phone = serializers.CharField(source='assigned_caller.phone_number', read_only=True, allow_null=True)
    # یادداشت تماس‌ها
    call_notes = serializers.SerializerMethodField(read_only=True)
    # آمار تماس‌ها
    contact_calls_count = serializers.IntegerField(read_only=True)
    contacts_calls_answered_count = serializers.IntegerField(read_only=True)
    contacts_calls_not_answered_count = serializers.IntegerField(read_only=True)
    contacts_calls_rate = serializers.FloatField(read_only=True)
    # نمایش تاریخ‌ها به صورت جلالی
    persian_updated_at = serializers.SerializerMethodField(read_only=True)
    persian_created_by = serializers.SerializerMethodField(read_only=True)
    # لاگ‌ها
    contact_logs = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            'id', 'project', 'full_name', 'phone', 'email', 'address',
            'assigned_caller_id', 'assigned_caller', 'assigned_caller_phone',
            'call_status', 'call_notes', 'custom_fields', 'is_active',
            'created_at', 'updated_at', 'created_by',
            "contact_calls_count", 'contacts_calls_answered_count',
            'contacts_calls_not_answered_count', 'contacts_calls_rate',
            "is_special", "gender", "birth_date",
            'persian_created_by', 'persian_updated_at', 'contact_logs'
        )
        read_only_fields = ('created_at', 'updated_at', 'created_by')

    def get_call_notes(self, obj):
        from calls.models import Call  # در صورت وجود
        calls = Call.objects.filter(contact=obj, notes__isnull=False).exclude(notes='').order_by('-call_date')
        return [
            {
                'caller_name': call.caller.get_full_name() if call.caller else 'Unknown',
                'note': call.notes,
                'created_at': str(JalaliDate(call.created_at.date())),
                'call_result': getattr(call, 'get_call_result_display', lambda: call.call_result)()
            }
            for call in calls
        ]

    def get_persian_updated_at(self, obj):
        return str(JalaliDate(obj.updated_at.date()))

    def get_persian_created_by(self, obj):
        return str(JalaliDate(obj.created_at.date()))

    def get_contact_logs(self, obj):
        logs = ContactLog.objects.filter(contact=obj).select_related('performed_by').order_by('-timestamp')
        return [
            {
                'action': log.action,
                'timestamp': str(JalaliDate(log.timestamp.date())),
                'performed_by': log.performed_by.get_full_name() if log.performed_by else 'Unknown'
            }
            for log in logs
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user

        caller_phone_number = validated_data.pop('caller_phone_number', None)
        if caller_phone_number and 'assigned_caller' not in validated_data:
            try:
                caller_user = CustomUser.objects.get(phone=caller_phone_number)
                validated_data['assigned_caller'] = caller_user
            except CustomUser.DoesNotExist:
                pass

        return super().create(validated_data)

    def update(self, instance, validated_data):
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

    def get_total_calls(self, obj):
        return getattr(obj, 'total_calls', 0)

    def get_answered_calls(self, obj):
        return getattr(obj, 'answered_calls', 0)

    def get_not_answered_calls(self, obj):
        return getattr(obj, 'not_answered_calls', 0)

    def get_interested_calls(self, obj):
        return getattr(obj, 'interested_calls', 0)

    def get_not_interested_calls(self, obj):
        return getattr(obj, 'not_interested_calls', 0)

    def get_no_time_calls(self, obj):
        return getattr(obj, 'no_time_calls', 0)
