import re

from persiantools.jdatetime import JalaliDate
from rest_framework import serializers

from calls.models import Call
from projects.models import Project, ProjectMembership
from users.models import CustomUser
from .models import *


class ContactSerializer(serializers.ModelSerializer):
    # TODO this serializer is damn helll need to get fixed as soon as possible
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )
    assigned_caller_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='assigned_caller', write_only=True, allow_null=True, required=False
    )

    # فیلدهای اضافی برای نمایش بهتر در فرانت‌اند
    assigned_caller_phone = serializers.CharField(source='assigned_caller.phone',read_only=True)
    call_notes = serializers.SerializerMethodField(read_only=True)
    # این فیلد برای تخصیص توسط ادمین استفاده می‌شود
    caller_phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    persian_updated_at = serializers.SerializerMethodField(read_only=True)
    persian_created_by = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            'id', 'project_id', 'full_name', 'phone', 'email',
            'address', 'assigned_caller_id', 'assigned_caller',
            'assigned_caller_phone', 'call_status',
             'call_notes', 'custom_fields',
            'is_active', 'created_at', 'updated_at',
            'caller_phone_number', 'created_by',
            "contact_calls_count", 'contacts_calls_answered_count',
            'contact_calls_not_answered_count', 'contacts_calls_rate', "is_special",
            "gender", "birth_date", 'persian_created_by', 'persian_updated_at'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'created_by'
        )

    def get_persian_updated_at(self, obj):
        return str(JalaliDate(obj.updated_at.date()))

    def get_persian_created_by(self, obj):
        return str(JalaliDate(obj.created_at.date()))

    def get_contacts_calls_answered_count(self, obj):
        phone_number = obj.phone
        answered_calls = Call.objects.filter(
            contact__phone=phone_number,
            status="answered"
        ).count()
        return answered_calls

    def get_contact_calls_not_answered_count(self, obj):
        phone_number = obj.phone
        not_answered_calls = Call.objects.filter(
            contact__phone=phone_number,
            status="not_answered"
        ).count()
        return not_answered_calls

    def get_contact_calls_count(self, obj):
        phone_number = obj.phone
        all_call_count = Call.objects.filter(contact__phone=phone_number).count()

        return all_call_count

    def get_contacts_calls_rate(self, obj):
        phone_number = obj.phone
        answered_calls = Call.objects.filter(
            contact__phone=phone_number,
            status="answered"
        ).count()

        # تعداد کل تماس‌ها
        total_calls = Call.objects.filter(contact__phone=phone_number).count()

        # تعداد تماس‌های پاسخ داده شده

        # اگر تماسی نباشد، نرخ صفر است
        if total_calls == 0:
            return 0.0
        # محاسبه درصد و گرد کردن به دو رقم اعشار
        rate = int((answered_calls / total_calls) * 100)
        return rate

    def get_contact_notes(self, obj):
        """تمام یادداشت‌های تماس مرتبط با شماره تلفن این مخاطب"""
        try:
            phone_number = obj.phone
            calls = Call.objects.filter(contact__phone=phone_number).filter(notes__isnull=False).exclude(
                notes='').order_by('-call_date')

            return [
                {
                    'caller_name': call.caller.get_full_name() if call.caller else 'ناشناس',
                    'note': call.notes,
                    'created_at': str(JalaliDate(call.created_at.date())),
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

    def get_call_notes(self, obj):
        """یادداشت‌های تماس"""
        try:
            # Eager loading for efficiency: prefetch answers and related fields
            recent_calls = obj.calls.prefetch_related(
                'answers__question',
                'answers__selected_choice'
            ).exclude(
                notes=''
            ).order_by('-call_date')[:5]

            return [
                {
                    'caller_name': call.caller.get_full_name() if call.caller else 'ناشناس',
                    'note': call.notes,
                    'created_at': str(JalaliDate(call.call_date.date())),
                    'call_result': call.get_call_result_display() if hasattr(call,
                                                                             'get_call_result_display') else call.call_result,
                    # New: List of answers with question and choice details
                    'answers': [
                        {
                            'question_text': answer.question.text,
                            'selected_choice_text': answer.selected_choice.text if answer.selected_choice else None
                        }
                        for answer in call.answers.all()
                    ]
                }
                for call in recent_calls
            ]
        except Exception:  # Broad exception handling retained; consider specifying types for precision
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
                caller_user = CustomUser.objects.get(phone_number=caller_phone_number)
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

class ContactStatsSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    projectId = serializers.IntegerField(source='project.id', read_only=True)

    class Meta:
        model = Contact
        fields = ("id",
            "full_name",
            "phone",
            "project_id",
            "project_name",
            "total_calls",
            "answered_calls",
            "not_answered_calls",
            "interested_calls",
            "not_interested_calls",
            "no_time_calls",)