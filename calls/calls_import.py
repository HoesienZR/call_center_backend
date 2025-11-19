# Standard package Python
from django.contrib.auth import get_user_model



# third party package
from persiantools.jdatetime import JalaliDate
from rest_framework import serializers


# local app package
from contacts.models import Contact
from files.models import Question, AnswerChoice
from projects.models import Project
from files.serializers import QuestionSerializer, AnswerChoiceSerializer
from users.serializers import CustomUserSerializer

