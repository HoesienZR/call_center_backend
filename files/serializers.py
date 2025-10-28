from rest_framework import serializers
from calls.models import Call
from persiantools.jdatetime import JalaliDate
from .models import *


class AnswerChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerChoice
        fields = ['id', 'text']


class QuestionSerializer(serializers.ModelSerializer):
    choices = AnswerChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'choices']


# TODO maybe and this also be useless too
class SavedSearchSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='user', write_only=True
    )
    search_criteria = serializers.JSONField(required=False)

    class Meta:
        model = SavedSearch
        fields = '__all__'


# TODO maybe this be useless too
class UploadedFileSerializer(serializers.ModelSerializer):
    uploaded_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='uploaded_by', write_only=True
    )

    class Meta:
        model = UploadedFile
        fields = '__all__'
