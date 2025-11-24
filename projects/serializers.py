from django.contrib.auth import get_user_model
from persiantools.jdatetime import JalaliDate
from rest_framework import serializers

from users.serializers import CustomUserSerializer
from .models import Project, ProjectMembership, Question, AnswerChoice

User = get_user_model()


class AnswerChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerChoice
        fields = ['id', 'text']


class QuestionSerializer(serializers.ModelSerializer):
    choices = AnswerChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'choices']

class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )

    class Meta:
        model = ProjectMembership
        fields = ('id', 'project_id', 'user', 'user_id', 'role', 'assigned_at')
        read_only_fields = ('assigned_at',)


class ProjectSerializer(serializers.ModelSerializer):
    call_answers_summary = AnswerChoiceSerializer(many=True, read_only=True)
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='created_by', write_only=True
    )
    project_statistics = serializers.SerializerMethodField()
    persian_updated_at = serializers.SerializerMethodField()
    persian_created_at = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status', 'created_by',
            'created_by_id', 'show', 'call_answers_summary', 'persian_updated_at',
            'persian_created_at', 'project_statistics'
        )
        read_only_fields = ('created_at', 'updated_at',)

    def get_project_statistics(self, obj):
        """دریافت آمار پروژه"""
        return obj.get_statistics() if hasattr(obj, 'get_statistics') else {}

    def get_persian_updated_at(self, obj):
        """تبدیل تاریخ به فرمت جلالی"""
        return self._get_persian_date(obj.updated_at)

    def get_persian_created_at(self, obj):
        """تبدیل تاریخ به فرمت جلالی"""
        return self._get_persian_date(obj.created_at)

    def _get_persian_date(self, date_obj):
        """کمک به تبدیل تاریخ به فرمت جلالی"""
        return str(JalaliDate(date_obj.date())) if date_obj else None



