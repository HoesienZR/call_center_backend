from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import  UploadedFile, SavedSearch



# TODO maybe and this also be useless too
class SavedSearchSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), source='user', write_only=True
    )
    search_criteria = serializers.JSONField(required=False)

    class Meta:
        model = SavedSearch
        fields = '__all__'


# TODO maybe this be useless too
class UploadedFileSerializer(serializers.ModelSerializer):
    uploaded_by_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), source='uploaded_by', write_only=True
    )

    class Meta:
        model = UploadedFile
        fields = '__all__'
