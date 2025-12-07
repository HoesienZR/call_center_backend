from calls.calls_import import (
    get_user_model,
    JalaliDate,
    serializers,
    Contact,
    Question,
    AnswerChoice,
    Project,
    CustomUserSerializer, QuestionSerializer, AnswerChoiceSerializer, ContactSerializer
)

from .models import CallAnswer, Call

User = get_user_model()


class CallAnswerSummarySerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_choice = AnswerChoiceSerializer(read_only=True)

    class Meta:
        model = CallAnswer
        fields = ['question', 'selected_choice']


class CallAnswerSerializer(serializers.ModelSerializer):
    """Serializer for call answers (used internally)."""
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    question_text = serializers.CharField(source='question.text', read_only=True)
    selected_choice = serializers.PrimaryKeyRelatedField(queryset=AnswerChoice.objects.all(), allow_null=True,
                                                         required=False)
    selected_choice_text = serializers.SerializerMethodField()

    class Meta:
        model = CallAnswer
        fields = ['question', 'selected_choice', 'question_text', 'selected_choice_text']

    def get_selected_choice_text(self, obj):
        return obj.selected_choice.text if obj.selected_choice else None


class CallSerializer(serializers.ModelSerializer):
    answers = CallAnswerSerializer(many=True, required=False, read_only=True)
    contact = serializers.SerializerMethodField()
    caller = CustomUserSerializer(read_only=True)
    project = serializers.PrimaryKeyRelatedField(read_only=True)
    edited_by = CustomUserSerializer(read_only=True)
    persian_call_date = serializers.SerializerMethodField()
    original_data = serializers.JSONField(required=False)

    contact_id = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.all(), source='contact', write_only=True)
    caller_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='caller', write_only=True)
    project_id = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all(), source='project', write_only=True)
    edited_by_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='edited_by', write_only=True,
                                                      allow_null=True, required=False)

    class Meta:
        model = Call
        fields = (
            'id', 'contact', 'contact_id', 'caller', 'caller_id', 'project', 'project_id', 'call_date', 'call_result',
            'status', 'notes', 'feedback', 'detailed_report', 'duration', 'follow_up_required', 'follow_up_date',
            'is_editable', 'edited_at', 'edited_by', 'edited_by_id', 'edit_reason', 'original_data', 'answers',
            'persian_call_date'
        )
        read_only_fields = ('call_date', 'created_at', 'edited_at')

    def get_contact(self, obj):
        """Efficiently fetch the contact data."""
        return ContactSerializer(obj.contact).data

    def get_persian_call_date(self, obj):
        return str(JalaliDate(obj.call_date.date()))

    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        call = Call.objects.create(**validated_data)
        answers_bulk = []
        for answer_data in answers_data:
            answer_data['call'] = call
            answers_bulk.append(CallAnswer(**answer_data))
        CallAnswer.objects.bulk_create(answers_bulk)
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
        return obj.caller.phone_number

    def get_custom_fields(self, obj):
        return obj.contact.custom_fields

    def get_answers(self, obj):
        # Assuming Call has a related manager to CallAnswer instances, e.g., callanswer_set
        # Adjust the related_name if necessary based on your model's ForeignKey definition
        formatted_answers = []
        for answer in obj.answers.all():
            question_text = getattr(answer, 'question', '')
            selected_choice_text = getattr(answer, 'selected_choice', '')
            formatted_answers.append(f"{question_text} {selected_choice_text}  |")
        return "\n".join(formatted_answers) if formatted_answers else ""
