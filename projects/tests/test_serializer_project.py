import pytest
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectMembership, Question, AnswerChoice
from projects.serializers import (
    ProjectSerializer,
    ProjectMembershipSerializer,
    QuestionSerializer,
    AnswerChoiceSerializer
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        phone_number="+989123456789",
        password="password123"
    )


@pytest.fixture
def project(user):
    return Project.objects.create(
        name="Test Project",
        description="Test project description",
        status="active",
        created_by=user
    )


@pytest.fixture
def membership(user, project):
    return ProjectMembership.objects.create(
        user=user,
        project=project,
        role="caller"
    )


@pytest.fixture
def question(project):
    return Question.objects.create(
        text="What is your opinion?",
        project=project
    )


@pytest.fixture
def answer_choice(question):
    return AnswerChoice.objects.create(
        text="Good",
        question=question
    )


# ---------------------------- TESTS -----------------------------------


@pytest.mark.django_db
def test_project_serializer(project, membership):
    serializer = ProjectSerializer(project)
    data = serializer.data

    assert data["name"] == project.name
    assert "created_by" in data
    assert data["created_by"]["email"] == project.created_by.email
    assert "project_statistics" in data  # because it uses get_statistics()
    assert isinstance(data["persian_created_at"], str)
    assert isinstance(data["persian_updated_at"], str)


@pytest.mark.django_db
def test_project_membership_serializer(membership):
    serializer = ProjectMembershipSerializer(membership)
    data = serializer.data

    assert data["role"] == membership.role
    assert isinstance(data["user"], dict)
    assert data["user"]["phone_number"] == membership.user.phone_number


@pytest.mark.django_db
def test_question_serializer_with_choices(question, answer_choice):
    AnswerChoice.objects.create(text="Bad", question=question)

    serializer = QuestionSerializer(question)
    data = serializer.data

    assert data["text"] == question.text
    assert len(data["choices"]) == 2


@pytest.mark.django_db
def test_answer_choice_serializer(answer_choice):
    serializer = AnswerChoiceSerializer(answer_choice)
    data = serializer.data

    assert data["id"] == answer_choice.id
    assert data["text"] == answer_choice.text
