import pytest
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectMembership, Question, AnswerChoice
from calls.models import Call
from contacts.models import Contact

User = get_user_model()


# ---------------------------------------------------------
# 1) Basic Project Creation Test
# ---------------------------------------------------------
@pytest.mark.django_db
def test_project_creation():
    user = User.objects.create_user(password="1234", phone_number="09164896609")

    project = Project.objects.create(
        name="Test Project",
        description="Some description",
        created_by=user,
    )

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.description == "Some description"
    assert project.created_by == user


# ---------------------------------------------------------
# 2) Test Project Membership Relationship
# ---------------------------------------------------------
@pytest.mark.django_db
def test_project_membership_relationship():
    user = User.objects.create_user(password="1234", phone_number="0123456789")
    admin = User.objects.create_user(password="1234", phone_number="01234567890")

    project = Project.objects.create(name="Project 1", created_by=admin)

    membership = ProjectMembership.objects.create(
        project=project,
        user=user,
        role="caller"
    )

    assert membership in project.project_callers.all()
    assert project in user.projects.all()
    assert membership.role == "caller"


# ---------------------------------------------------------
# 3) Project Statistics Test
# ---------------------------------------------------------
@pytest.mark.django_db
def test_project_statistics():
    admin = User.objects.create_user( password="1234", phone_number="012345678")
    caller = User.objects.create_user(password="1234", phone_number="01234567891")

    project = Project.objects.create(name="Stats Project", created_by=admin)

    # Create a contact to satisfy NOT NULL constraint
    contact = Contact.objects.create(
        project=project,
        full_name="John Doe",
        phone="1234567890",
        created_by=admin
    )

    # Create sample calls
    Call.objects.create(
        project=project,
        caller=caller,
        contact=contact,
        call_result="answered",
        duration=30
    )
    Call.objects.create(
        project=project,
        caller=caller,
        contact=contact,
        call_result="busy",
        duration=0
    )

    stats = project.get_statistics()

    assert stats["total_calls"] == 2
    assert stats["call_results_distribution"]["answered"] == 1
    assert stats["call_results_distribution"]["busy"] == 1
    assert stats["total_duration_seconds"] == 30
    assert stats["average_call_duration_seconds"] == 15.0
    assert stats["success_rate"] == 50.0


# ---------------------------------------------------------
# 4) Caller Performance Report Test
# ---------------------------------------------------------
@pytest.mark.django_db
def test_caller_performance_report():
    admin = User.objects.create_user(password="1234", phone_number="01234567")
    caller = User.objects.create_user(password="1234", phone_number="0123456789")

    project = Project.objects.create(name="Perf Project", created_by=admin)

    ProjectMembership.objects.create(
        project=project,
        user=caller,
        role="caller"
    )

    contact = Contact.objects.create(
        project=project,
        full_name="Jane Doe",
        phone="0987654321",
        created_by=admin
    )

    Call.objects.create(
        project=project,
        caller=caller,
        contact=contact,
        call_result="answered",
        duration=20
    )
    Call.objects.create(
        project=project,
        caller=caller,
        contact=contact,
        call_result="no_answer",
        duration=0
    )

    report = project.get_caller_performance_report()

    assert len(report) == 1
    caller_stats = report[0]

    assert caller_stats["caller_phone"] == "0123456789"
    assert caller_stats["total_calls"] == 2
    assert caller_stats["answered_calls"] == 1
    assert caller_stats["total_duration_seconds"] == 20
    assert caller_stats["success_rate"] == 50.0


# ---------------------------------------------------------
# 5) Question & AnswerChoice Creation Test
# ---------------------------------------------------------
@pytest.mark.django_db
def test_question_and_answer_choice():
    admin = User.objects.create_user(password="1234", phone_number="09164896609")
    project = Project.objects.create(name="Q Project", created_by=admin)

    question = Question.objects.create(
        project=project,
        text="How satisfied are you?"
    )

    choice1 = AnswerChoice.objects.create(question=question, text="Very satisfied")
    choice2 = AnswerChoice.objects.create(question=question, text="Not satisfied")

    assert question in project.questions.all()
    assert choice1 in question.choices.all()
    assert choice2 in question.choices.all()
    assert choice1.text == "Very satisfied"
    assert choice2.text == "Not satisfied"
