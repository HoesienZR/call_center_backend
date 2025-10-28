from rest_framework import serializers
from persiantools.jdatetime import JalaliDate
from files.serializers import QuestionSerializer, AnswerChoiceSerializer
from .models import *
from contacts.models import Contact
from contacts.serializers import ContactSerializer
from users.serializers import CustomUserSerializer
from projects.serializers import ProjectSerializer
from users.models import CustomUser

class CallAnswerSummarySerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_choice = AnswerChoiceSerializer(read_only=True)
    # Aggregate fields: e.g., count of selections per choice
    choice_counts = serializers.SerializerMethodField()

    class Meta:
        model = CallAnswer
        fields = ['question', 'selected_choice', 'choice_counts']

    # TODO useless method field no use at all
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


class CallAnswerSerializer(serializers.ModelSerializer):
    """Serializer for call answers (used internally)."""
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    question_text = serializers.CharField(source='question.text', read_only=True)
    selected_choice = serializers.PrimaryKeyRelatedField(queryset=AnswerChoice.objects.all(), allow_null=True,
                                                         required=False)
    selected_choice_text = serializers.CharField(source='selected_choice.text', read_only=True)

    class Meta:
        model = CallAnswer
        fields = ['question', 'selected_choice', 'question_text', 'selected_choice_text', "question_text",
                  'selected_choice_text']


class CallSerializer(serializers.ModelSerializer):

    # todo this need to get damn optimised as ssoooooon as possible
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

    def get_persian_call_date(self, obj):
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

#TODO maybe this is useless
# 6. سایر سریالایزرها با ارجاعات اصلاح شده
class CallEditHistorySerializer(serializers.ModelSerializer):
    edited_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='edited_by', write_only=True
    )
    class Meta:
        model = CallEditHistory
        fields = '__all__'
