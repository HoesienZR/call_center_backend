# call_center/serializers.py
import re
from persiantools.jdatetime import JalaliDate
from django.db import transaction
from django.db.models import Count, Prefetch
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
    CachedStatistics, Question, AnswerChoice, CallAnswer, Ticket,
)
from rest_framework import serializers
# 1. سریالایزر برای مدل کاربر سفارشی
class CustomUserSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل CustomUser که شامل فیلدهای سفارشی است.
    """
    persian_date_joined = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'date_joined', 'last_login',
            'phone_number', 'can_create_projects','phone_number',
            'persian_date_joined'
        )
        read_only_fields = (
            'is_staff', 'is_active', 'date_joined', 'last_login'
        )
    def get_persian_date_joined(self, obj):
        return str(JalaliDate((obj.date_joined.date())))
# your_app/serializers.py
from rest_framework import serializers
from .models import Call, Contact, Project, ProjectMembership
import json
class AnswerChoiceSerializer(serializers.ModelSerializer):
    """Serializer for answer choices."""
    class Meta:
        model = AnswerChoice
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for questions, including choices."""
    choices = AnswerChoiceSerializer(many=True,read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'choices']
class CallAnswerSummarySerializer(serializers.ModelSerializer):
    """Serializer for summarizing answers per question in a project."""
    question = QuestionSerializer(read_only=True)
    selected_choice = AnswerChoiceSerializer(read_only=True)
    # Aggregate fields: e.g., count of selections per choice
    choice_counts = serializers.SerializerMethodField()

    class Meta:
        model = CallAnswer
        fields = ['question', 'selected_choice', 'choice_counts']

    def get_choice_counts(self, obj):
        # Optional: Aggregate counts for this answer's choice across the project
        project = self.context['project']
        if obj.selected_choice:
            count = CallAnswer.objects.filter(
                call__project=project,
                selected_choice=obj.selected_choice
            ).count()
            return {'count': count, 'choice_id': obj.selected_choice.id}
        return None

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
    questions = QuestionSerializer(many=True,read_only=True)
    call_answers_summary = serializers.SerializerMethodField()
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
    project_statistics = serializers.SerializerMethodField()
    persian_updated_at = serializers.SerializerMethodField()
    persian_created_at = serializers.SerializerMethodField()
    def get_project_statistics(self,obj):
        return obj.get_statistics()
    def get_completed_calls_count(self, obj):
        return obj.calls.filter(status="completed").count()

    def get_call_answers_summary(self, obj):
        """Custom field to retrieve all answers from the project's calls, grouped by question."""
        project = obj  # The project instance
        # Fetch answers with prefetch for efficiency
        answers = CallAnswer.objects.filter(
            call__project=project
        ).select_related(
            'question', 'selected_choice'
        ).prefetch_related(
            Prefetch('question__choices')
        )

        # Group by question for structured output
        grouped_answers = {}
        for answer in answers:
            q_id = answer.question.id
            if q_id not in grouped_answers:
                grouped_answers[q_id] = {
                    'question': QuestionSerializer(answer.question).data,
                    'answers': []
                }
            grouped_answers[q_id]['answers'].append(
                CallAnswerSummarySerializer(answer, context={'project': project}).data
            )

        # Convert to list for serialization
        summary_list = list(grouped_answers.values())
        return summary_list

    def update(self, instance, validated_data):
        """
        Custom update method to handle nested questions and answer choices.
        """
        # Extract nested questions data
        questions_data = validated_data.pop('questions', None)

        # Update the base project instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle questions and choices within a transaction
        if questions_data is not None:
            with transaction.atomic():
                # Track existing question IDs in payload for updates/deletions
                question_ids_in_payload = {q.get('id') for q in questions_data if q.get('id')}

                # Update or create questions
                for question_data in questions_data:
                    question_id = question_data.pop('id', None)
                    if question_id:
                        # Update existing question
                        question = Question.objects.get(id=question_id, project=instance)
                        for attr, value in question_data.items():
                            setattr(question, attr, value)
                        question.save()
                    else:
                        # Create new question
                        question = Question.objects.create(project=instance, **question_data)

                    # Handle nested choices for this question
                    self._update_choices(question, question_data.pop('choices', []))

                # Optional: Delete questions not in payload (full replacement logic)
                # existing_questions = Question.objects.filter(project=instance)
                # for q in existing_questions:
                #     if q.id not in question_ids_in_payload:
                #         q.delete()

        return instance

    def _update_choices(self, question, choices_data):
        """
        Helper method to update or create answer choices for a question.
        """
        choice_ids_in_payload = {c.get('id') for c in choices_data if c.get('id')}

        for choice_data in choices_data:
            choice_id = choice_data.pop('id', None)
            if choice_id:
                # Update existing choice
                choice = AnswerChoice.objects.get(id=choice_id, question=question)
                for attr, value in choice_data.items():
                    setattr(choice, attr, value)
                choice.save()
            else:
                # Create new choice
                AnswerChoice.objects.create(question=question, **choice_data)

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        # Create the project instance (created_by will be set in perform_create)
        project = Project.objects.create(**validated_data)

        # Create questions and their choices within a transaction for atomicity
        with transaction.atomic():
            for question_data in questions_data:
                # Extract nested choices
                choices_data = question_data.pop('choices', [])
                print(questions_data)
                # Create question linked to project
                question = Question.objects.create(project=project, **question_data)
                # Create choices linked to question
                print("this is choices",choices_data)
                for choice_data in choices_data:
                    print(choice_data)
                    AnswerChoice.objects.create(question=question, **choice_data)

        return project
    def to_representation(self, instance):
        """Ensure active questions are filtered."""
        representation = super().to_representation(instance)
        if 'questions' in representation:
            representation['questions'] = [
                q for q in representation['questions']
            ]
        return representation
    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status', 'created_by',
            'created_by_id', 'created_at', 'updated_at', 'members',
            'contacts_count', 'calls_count', 'completed_calls_count',
            "show","call_answers_summary","questions",'persian_updated_at'
            ,'persian_created_at','project_statistics'
        )
        read_only_fields = ('created_at', 'updated_at', 'members')
    def get_persian_updated_at(self,obj):
        return str(JalaliDate(obj.updated_at.date()))
    def get_persian_created_at(self,obj):
        return str(JalaliDate(obj.created_at.date()))


# 4. سریالایزر مخاطبین


# فایل: serializers.py

from rest_framework import serializers
from .models import Contact, Project, CustomUser, ProjectMembership  # ProjectMembership را اضافه کنید

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("title", "description",)

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
    persian_updated_at = serializers.SerializerMethodField(read_only=True)
    persian_created_by = serializers.SerializerMethodField(read_only=True)
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
            'contact_calls_not_answered_count','contacts_calls_rate', "is_special",
            "gender","birth_date",'persian_created_by','persian_updated_at'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'created_by'
        )
    def get_persian_updated_at(self,obj):
        return str(JalaliDate(obj.updated_at.date()))
    def get_persian_created_by(self,obj):
        return str(JalaliDate(obj.created_at.date()))

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

        # تعداد کل تماس‌ها
        total_calls = Call.objects.filter(contact__phone=phone_number).count()

        # تعداد تماس‌های پاسخ داده شده

        # اگر تماسی نباشد، نرخ صفر است
        if total_calls == 0:
            return 0.0
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
            # Eager loading for efficiency: prefetch answers and related fields
            recent_calls = obj.calls.prefetch_related(
                'answers__question',
                'answers__selected_choice'
            ).filter(
                notes__isnull=False
            ).exclude(
                notes=''
            ).order_by('-call_date')[:5]

            return [
                {
                    'caller_name': call.caller.get_full_name() if call.caller else 'ناشناس',
                    'note': call.notes,
                    'created_at':  str(JalaliDate(call.call_date.date())),
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



class CallAnswerSerializer(serializers.ModelSerializer):
    """Serializer for call answers (used internally)."""
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    question_text = serializers.CharField(source='question.text', read_only=True)
    selected_choice = serializers.PrimaryKeyRelatedField(queryset=AnswerChoice.objects.all(), allow_null=True, required=False)
    selected_choice_text = serializers.CharField(source='selected_choice.text', read_only=True)
    class Meta:
        model = CallAnswer
        fields = ['question', 'selected_choice','question_text','selected_choice_text',"question_text",'selected_choice_text']


class CallSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Call.
    """
    answers = CallAnswerSerializer(many=True, required=False)
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
    persian_call_date = serializers.SerializerMethodField()
    original_data = serializers.JSONField(required=False)
    class Meta:
        model = Call
        fields = (
            'id', 'contact', 'contact_id', 'caller', 'caller_id', 'project',
            'project_id', 'call_date', 'call_result', 'status', 'notes', 'feedback',
            'detailed_report', 'duration', 'follow_up_required', 'follow_up_date',
            'is_editable', 'edited_at', 'edited_by', 'edited_by_id', 'edit_reason',
            'original_data',
            'answers',
            'persian_call_date'
        )
        read_only_fields = ('call_date', 'created_at', 'edited_at')
    def get_persian_call_date(self,obj):
        return str(JalaliDate(obj.call_date.date()))
    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        call = Call.objects.create(**validated_data)
        for answer_data in answers_data:
            answer_data['call'] = call
            CallAnswer.objects.create(**answer_data)
        return call

    def validate(self, data):
        project = data.get('project')
        if not project:
            raise serializers.ValidationError("Project is required.")
        if answers_data := data.get('answers'):
            question_ids = [a['question'].id for a in answers_data if isinstance(a['question'], Question)]
            project_question_ids = set(project.questions.values_list('id', flat=True))
            invalid_questions = set(question_ids) - project_question_ids
            if invalid_questions:
                raise serializers.ValidationError(f"Invalid questions: {list(invalid_questions)}")
        return data
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


class GeneralStatisticsSerializer(serializers.Serializer):
    total_contacts = serializers.IntegerField()
    total_calls = serializers.IntegerField()
    successful_calls = serializers.IntegerField()
    answered_calls = serializers.IntegerField()
    success_rate = serializers.FloatField()
    answer_rate = serializers.FloatField()


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


class ProjectStatisticsSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    general_statistics = GeneralStatisticsSerializer()
    caller_performance = CallerPerformanceSerializer(many=True)
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
    answers =serializers.SerializerMethodField()
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
    def get_persian_date(self,obj):
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
# 2. سریالایزر برای مدیریت نقش کاربران در پروژه