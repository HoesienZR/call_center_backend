from rest_framework import serializers

from .models import CallStatistics, CachedStatistics, ExportReport
from calls.models import Call


# TODO  maybe and this also is useless
class CallStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallStatistics
        fields = '__all__'


class ExportReportSerializer(serializers.ModelSerializer):
    exported_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='exported_by', write_only=True
    )
    filters = serializers.JSONField(required=False)

    class Meta:
        model = ExportReport
        fields = '__all__'


# TODO maybe this is useless also


class CachedStatisticsSerializer(serializers.ModelSerializer):
    stat_value = serializers.JSONField(required=False)

    class Meta:
        model = CachedStatistics
        fields = '__all__'


class GeneralStatisticsSerializer(serializers.Serializer):
    total_contacts = serializers.IntegerField()
    total_calls = serializers.IntegerField()
    successful_calls = serializers.IntegerField()
    answered_calls = serializers.IntegerField()
    success_rate = serializers.FloatField()
    answer_rate = serializers.FloatField()


class ProjectStatisticsSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    general_statistics = GeneralStatisticsSerializer()
    caller_performance = CallerPerformanceSerializer(many=True)


class CallerPerformanceSerializer(serializers.Serializer):
    caller_id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.CharField()
    username = serializers.CharField()
    phone_number = serializers.CharField()
    total_calls = serializers.IntegerField()

    # تماس‌های بر اساس نتیجه
    interested_calls = serializers.IntegerField()
    no_time_calls = serializers.IntegerField()
    not_interested_calls = serializers.IntegerField()

    # تماس‌های بر اساس وضعیت
    answered_calls = serializers.IntegerField()
    no_answer_calls = serializers.IntegerField()
    wrong_number_calls = serializers.IntegerField()
    pending_calls = serializers.IntegerField()

    # نرخ‌ها
    success_rate = serializers.FloatField()
    answer_rate = serializers.FloatField()

    # مدت زمان
    total_duration_seconds = serializers.IntegerField()
    avg_duration_seconds = serializers.FloatField()
    total_duration_formatted = serializers.CharField()
    avg_duration_formatted = serializers.CharField()
    calls_with_duration = serializers.IntegerField()


class CallExcelSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    contact_phone = serializers.CharField(source='contact.phone', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    contact_gender = serializers.CharField(source='contact.gender', read_only=True)
    special_contact = serializers.CharField(source='contact.is_special', read_only=True)
    contact_birth_date = serializers.CharField(source='contact.birth_date', read_only=True)
    caller_phone = serializers.SerializerMethodField()
    call_result_display = serializers.CharField(source='get_call_result_display', read_only=True)
    call_status_display = serializers.CharField(source='get_status_display', read_only=True)
    custom_fields = serializers.SerializerMethodField()
    caller_name = serializers.CharField(source='caller.get_full_name', read_only=True)
    address = serializers.CharField(source="contact.address", read_only=True)
    answers = serializers.SerializerMethodField()
    persian_date = serializers.SerializerMethodField()

    class Meta:
        model = Call
        fields = [
            "caller_name",
            'contact_name',
            'contact_phone',
            "contact_gender",
            "special_contact",
            "contact_birth_date",
            'project_name',
            'caller_phone',
            'call_result_display',
            'call_status_display',
            'notes',
            'duration',
            'call_date',
            "persian_date",
            'custom_fields',
            "address",
            "answers",

        ]

    def get_persian_date(self, obj):
        return str(JalaliDate(obj.call_date.date()))

    def get_caller_phone(self, obj):
        # فرض می‌کنیم مدل User یک فیلد پروفایل دارد که شماره تماس در آن ذخیره شده است
        return obj.caller.phone_number

    def get_custom_fields(self, obj):
        # دریافت فیلدهای سفارشی از مدل Contact
        return obj.contact.custom_fields

    def get_answers(self, obj):
        # Assuming Call has a related manager to CallAnswer instances, e.g., callanswer_set
        # Adjust the related_name if necessary based on your model's ForeignKey definition
        formatted_answers = []
        for answer in obj.answers.all():
            # Replace 'callanswer_set' with the actual related_name if different
            question_text = getattr(answer, 'question', '')  # Adjust attribute name if different
            selected_choice_text = getattr(answer, 'selected_choice', '')  # Adjust attribute name if different
            formatted_answers.append(f"{question_text} {selected_choice_text}  |")
        return "\n".join(formatted_answers) if formatted_answers else ""
