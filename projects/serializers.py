from django.contrib.auth import get_user_model
from rest_framework import serializers

from calls.serializers import CallAnswer, CallAnswerSummarySerializer
from files.serializers import QuestionSerializer, AnswerChoiceSerializer
from django.contrib.auth import get_user_model
from users.serializers import CustomUserSerializer
from .models import *
from persiantools.jdatetime import JalaliDate

User = get_user_model()

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

    def get_project_statistics(self, obj):
        # اطمینان از اینکه متد `get_statistics` در مدل Project پیاده‌سازی شده است
        return obj.get_statistics() if hasattr(obj, 'get_statistics') else {}

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status', 'created_by',
            'created_by_id', "show", "call_answers_summary", 'persian_updated_at',
            'persian_created_at', 'project_statistics'
        )
        read_only_fields = ('created_at', 'updated_at',)

    def get_persian_updated_at(self, obj):
        # تبدیل تاریخ به فرمت جلالی
        return str(JalaliDate(obj.updated_at.date())) if obj.updated_at else None

    def get_persian_created_at(self, obj):
        # تبدیل تاریخ به فرمت جلالی
        return str(JalaliDate(obj.created_at.date())) if obj.created_at else None
