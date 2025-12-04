import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse

from projects.models import Project, ProjectMembership, Question, AnswerChoice

User = get_user_model()


@pytest.mark.django_db
def test_list_projects():
    client = APIClient()

    user = User.objects.create_user(
        username="admin",
        password="1234",
        phone_number="1000000001",
        is_staff=True,
        is_superuser=True,
    )

    # پروژه بساز و created_by=کاربر بالا
    project = Project.objects.create(name="Test Project", created_by=user)

    # authenticate
    client.force_authenticate(user=user)

    # گرفتن url لیست پروژه
    url = reverse("projects-list")
    response = client.get(url)
    assert response.status_code == 200

    data = response.json()
    if isinstance(data, dict) and "results" in data:
        data = data["results"]

    print("Response data:", data)
    assert any(p.get("id") == project.id for p in data), "Project not found in response"

@pytest.mark.django_db
def test_create_project(client):
    user = User.objects.create_user(username="admin", password="1234", phone_number="1000000002",
                                    can_create_projects=True)
    client.force_login(user)

    url = reverse("projects-list")
    payload = {"name": "New Project", "created_by_id": user.id
               }
    response = client.post(url, payload, content_type="application/json")
    print(response.json())
    assert response.status_code == 201
    project = Project.objects.get(name="New Project")
    assert project.created_by == user


@pytest.mark.django_db
def test_project_membership_list(client):
    user = User.objects.create_user(username="admin", password="1234", phone_number="1000000003")
    project = Project.objects.create(name="Membership Project", created_by=user)
    membership = ProjectMembership.objects.create(user=user, project=project, role="admin")

    client.force_login(user)
    url = reverse("project-memberships-list")  # مسیر دستی
    response = client.get(url, {"project_id": project.id})
    assert response.status_code == 200
    data = response.json()
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    assert any(m["id"] == membership.id for m in data)


@pytest.mark.django_db
def test_question_crud(client):
    user = User.objects.create_user(username="admin", password="1234", phone_number="1000000004")
    project = Project.objects.create(name="Question Project", created_by=user)
    client.force_login(user)

    url = reverse("project-questions-list", kwargs={"project_pk": project.id})  # nested router
    payload = {"text": "Sample Question"}
    response = client.post(url, payload, content_type="application/json")
    assert response.status_code == 201
    question = Question.objects.get(text="Sample Question")
    assert question.project == project

    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    assert any(q["id"] == question.id for q in data)


@pytest.mark.django_db
def test_answer_choice_crud(client):
    user = User.objects.create_user(username="admin", password="1234", phone_number="1000000005")
    project = Project.objects.create(name="Choice Project", created_by=user)
    question = Question.objects.create(project=project, text="Question with choices")
    client.force_login(user)

    url = reverse("project-choices-list",
                  kwargs={"project_pk": project.id, "question_pk": question.id})  # nested router
    payload = {"text": "Choice 1"}
    response = client.post(url, payload, content_type="application/json")
    assert response.status_code == 201
    choice = AnswerChoice.objects.get(text="Choice 1")
    assert choice.question == question

    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    assert any(c["id"] == choice.id for c in data)
