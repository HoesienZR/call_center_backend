import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from calls.calls_import import Contact, Project, Question, AnswerChoice
from calls.models import Call, CallAnswer
from projects.models import ProjectMembership

User = get_user_model()


class CallAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(phone_number="1000000001", password="password1")
        self.user2 = User.objects.create_user(phone_number="1000000002", password="password2")
        self.admin_user = User.objects.create_superuser(phone_number="1000000000",
                                                        password="admin123")

        self.project = Project.objects.create(name="Test Project", created_by=self.user1)
        self.contact = Contact.objects.create(full_name="Test Contact", phone="2000000001", project=self.project)
        self.call = Call.objects.create(contact=self.contact, caller=self.user1, project=self.project,
                                        status="pending", call_result="interested", duration=120)
        self.question = Question.objects.create(text="Did you like the service?", project=self.project)
        self.answer_choice = AnswerChoice.objects.create(text="Yes", question=self.question)

    def test_list_calls(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/calls/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_list_calls_by_project(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/calls/?project_id={self.project.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for call in response.data['results']:
            self.assertEqual(call['project'], self.project.id)


@pytest.mark.django_db
class TestCallExcelViewSet:

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        return User.objects.create_superuser(
            phone_number="09120000000",
            password="adminpass",
            email="admin@example.com"
        )

    @pytest.fixture
    def project_admin(self):
        return User.objects.create_user(
            phone_number="09120000001",
            password="pass",
            email="pa@example.com"
        )

    @pytest.fixture
    def caller_user(self):
        return User.objects.create_user(
            phone_number="09120000002",
            password="pass",
            email="caller@example.com"
        )

    @pytest.fixture
    def project(self, project_admin):
        p = Project.objects.create(name="Excel Project", created_by=project_admin)
        ProjectMembership.objects.create(user=project_admin, project=p, role="admin")
        return p

    @pytest.fixture
    def sample_call(self, project, project_admin):
        contact = Contact.objects.create(
            project=project,
            full_name="John Wick",
            phone="09123334444"
        )

        call = Call.objects.create(
            project=project,
            caller=project_admin,
            contact=contact,
            call_result="success",
            status="completed",
            call_date=timezone.now(),
            duration=80,
        )

        q = Question.objects.create(project=project, text="Rate us")
        choice = AnswerChoice.objects.create(question=q, text="Great")

        CallAnswer.objects.create(
            call=call,
            question=q,
            selected_choice=choice
        )

        return call

    # ------------------------------------------------------
    # 1) Superuser → باید کل تماس‌ها را ببیند
    # ------------------------------------------------------
    def test_excel_list_as_admin(self, api_client, admin_user, sample_call):
        api_client.force_authenticate(admin_user)

        url = reverse("excel-list")
        response = api_client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert len(response.content) > 100  # فایل خالی نیست

    # ------------------------------------------------------
    # 2) ProjectAdmin → فقط تماس‌های پروژه خودش
    # ------------------------------------------------------
    def test_excel_list_as_project_admin(self, api_client, project_admin, project, sample_call):
        api_client.force_authenticate(project_admin)

        url = reverse("excel-list")
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.content) > 100

    # ------------------------------------------------------
    # 3) Caller → اجازه دسترسی ندارد
    # ------------------------------------------------------
    def test_excel_list_as_caller_forbidden(self, api_client, caller_user, project):
        # caller در پروژه عضو نیست و نقش admin ندارد
        ProjectMembership.objects.create(user=caller_user, project=project, role="caller")

        api_client.force_authenticate(caller_user)

        url = reverse("excel-list")
        response = api_client.get(url)

        assert response.status_code in (403, 401)
