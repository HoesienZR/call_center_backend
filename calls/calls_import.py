# Standard package Python
from django.contrib.auth import get_user_model



# third party package
from persiantools.jdatetime import JalaliDate
from rest_framework import serializers


# local app package
from contacts.models import Contact
from projects.models import Question, AnswerChoice, Project
from projects.serializers import QuestionSerializer, AnswerChoiceSerializer
from users.serializers import CustomUserSerializer

