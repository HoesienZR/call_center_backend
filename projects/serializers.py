from persiantools.jdatetime import JalaliDate
from rest_framework import serializers

from calls.serializers import CallAnswer
from users.models import *
from .models import *


class ProjectMembershipSerializer(serializers.ModelSerializer):
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


class ProjectSerializer(serializers.ModelSerializer):
    call_answers_summary = serializers.SerializerMethodField()
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='created_by', write_only=True
    )
    # TODO we must nested router for  this one
    members = ProjectMembershipSerializer(source='projectmembership_set', many=True, read_only=True)

    # TODO this three maybe need to get fixed by select_ralated and prefetch_related
    project_statistics = serializers.SerializerMethodField()
    persian_updated_at = serializers.SerializerMethodField()
    # TODO before change date to djangojalali don't  change this
    persian_created_at = serializers.SerializerMethodField()

    def get_project_statistics(self, obj):
        return obj.get_statistics()

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
            'created_by_id', 'members',
            "show", "call_answers_summary", 'persian_updated_at'
            , 'persian_created_at', 'project_statistics'
        )
        read_only_fields = ('created_at', 'updated_at', 'members')

    def get_persian_updated_at(self, obj):
        return str(JalaliDate(obj.updated_at.date()))

    def get_persian_created_at(self, obj):
        return str(JalaliDate(obj.created_at.date()))
