import pytest
import random
from django.contrib.auth import get_user_model
from calls.models import Call, CallAnswer
from calls.calls_import import Contact, Project, Question, AnswerChoice, ProjectMembership

User = get_user_model()

# Patch update_call_statistics to avoid CallStatistics dependency
Call.update_call_statistics = lambda self: None

@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        password="pass123",
        phone_number=f"0912{random.randint(1000000,9999999)}"
    )

@pytest.fixture
def test_project(test_user):
    return Project.objects.create(name=f"Test Project {random.randint(1,1000)}", created_by=test_user)

@pytest.fixture
def test_contact(test_project):
    return Contact.objects.create(
        full_name=f"John Doe {random.randint(1,1000)}",
        phone=f"0912{random.randint(1000000,9999999)}",
        project=test_project
    )

@pytest.fixture
def test_question(test_project):
    return Question.objects.create(
        text=f"Sample question? {random.randint(1,1000)}",
        project=test_project
    )

@pytest.fixture
def test_choice(test_question):
    return AnswerChoice.objects.create(
        question=test_question,
        text="Option A"
    )


@pytest.mark.django_db
def test_call_model_create(test_user, test_project, test_contact):
    call = Call.objects.create(
        contact=test_contact,
        caller=test_user,
        project=test_project,
        call_result="interested",
        status="answered",
        notes="Test notes",
        duration=60
    )

    assert call.id is not None
    assert call.contact == test_contact
    assert call.caller == test_user
    assert call.project == test_project
    assert call.get_original_data()['call_result'] == "interested"


@pytest.mark.django_db
def test_call_can_edit(test_user, test_project, test_contact):
    call = Call.objects.create(contact=test_contact, caller=test_user, project=test_project)

    # Superuser can edit
    admin_user = User.objects.create_superuser(
        password="adminpass",
        phone_number=f"0912{random.randint(1000000,9999999)}"
    )
    assert call.can_edit(admin_user) is True

    # Caller can edit (no ProjectMembership, so default False)
    assert call.can_edit(test_user) is False



@pytest.mark.django_db
def test_call_answer_model(test_user, test_project, test_contact, test_question, test_choice):
    call = Call.objects.create(contact=test_contact, caller=test_user, project=test_project)

    answer = CallAnswer.objects.create(
        call=call,
        question=test_question,
        selected_choice=test_choice
    )

    assert answer.id is not None
    assert answer.call == call
    assert answer.question == test_question
    assert answer.selected_choice == test_choice
