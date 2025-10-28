from rest_framework import serializers

from .models import CustomUser

from persiantools.jdatetime import JalaliDate

class CustomUserSerializer(serializers.ModelSerializer):

    persian_date_joined = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'date_joined', 'last_login',
            'phone_number', 'can_create_projects', 'phone_number',
            'persian_date_joined'
        )
        read_only_fields = (
            'is_staff', 'is_active', 'date_joined', 'last_login'
        )

    def get_persian_date_joined(self, obj):
        return str(JalaliDate((obj.date_joined.date())))
