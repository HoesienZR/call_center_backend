import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from contacts.models import Contact
from projects.models import Project, ProjectMembership
from users.models import CustomUser


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(
        phone_number="09120000001",
        is_staff=True,
        password="12345"
    )


@pytest.fixture
def caller_user(db):
    return CustomUser.objects.create_user(
        phone_number="09120000002",
        password="12345"
    )


@pytest.fixture
def project(db, admin_user):
    project = Project.objects.create(name="Test Project", created_by=admin_user)
    ProjectMembership.objects.create(project=project, user=admin_user, role="admin")
    return project


@pytest.fixture
def caller_membership(db, caller_user, project):
    return ProjectMembership.objects.create(project=project, user=caller_user, role="caller")


@pytest.fixture
def contact(db, project, caller_user):
    return Contact.objects.create(
        full_name="Ali",
        phone="09125556677",
        project=project,
        assigned_caller=caller_user,
        call_status="pending"
    )


# ------------------- LIST -------------------
def test_contact_list_as_admin(api_client, admin_user, contact):
    api_client.force_authenticate(admin_user)
    url = reverse("contacts-list")
    response = api_client.get(url)
    assert response.status_code == 200
    results = response.data['results']
    assert any(c['id'] == contact.id for c in results)


def test_contact_list_as_caller_only_own(api_client, caller_user, caller_membership, contact):
    api_client.force_authenticate(caller_user)
    url = reverse("contacts-list")
    response = api_client.get(url)
    assert response.status_code == 200

    results = response.data['results']

    for item in results:
        assert item["assigned_caller_id"] == caller_user.id


# ------------------- CREATE -------------------
def test_contact_create_as_admin(api_client, admin_user, project):
    api_client.force_authenticate(admin_user)
    url = reverse("contacts-list")

    data = {
        "full_name": "Sara",
        "phone": "09123334455",
        "project": project.id
    }

    response = api_client.post(url, data)
    assert response.status_code == 201
    assert response.data["full_name"] == "Sara"


# ------------------- REQUEST NEW -------------------
def test_request_new_contact(api_client, caller_user, caller_membership, project):
    api_client.force_authenticate(caller_user)

    # یک مخاطب آزاد برای اختصاص
    Contact.objects.create(
        full_name="New User",
        phone="09129998877",
        project=project,
        call_status="pending",
        is_active=True
    )

    url = reverse("contacts-request-new-contact")
    response = api_client.post(url, {"project_id": project.id})
    assert response.status_code == 200
    assert response.data["detail"] == "A new contact has been assigned to you."


# ------------------- RELEASE -------------------
def test_release_contact(api_client, caller_user, caller_membership, contact):
    api_client.force_authenticate(caller_user)
    url = reverse("contacts-release-contact", kwargs={"pk": contact.id})
    response = api_client.post(url)
    assert response.status_code == 200
    contact.refresh_from_db()
    assert contact.assigned_caller is None


# ------------------- STATS -------------------
def test_contact_stats(api_client, admin_user, contact):
    api_client.force_authenticate(admin_user)
    url = reverse("contacts-get-contact-stats", kwargs={"pk": contact.id})
    response = api_client.get(url)
    assert response.status_code == 200
    assert "total_calls" in response.data


# ------------------- FILTERS -------------------
def test_filter_by_status(api_client, admin_user, project):
    api_client.force_authenticate(admin_user)
    Contact.objects.create(
        full_name="Test User",
        phone="09128889977",
        project=project,
        call_status="pending"
    )
    url = reverse("contacts-filter-by-status")
    response = api_client.get(url, {"status": "pending"})
    assert response.status_code == 200
    for item in response.data:
        assert item["call_status"] == "pending"


def test_filter_by_project(api_client, admin_user, project):
    api_client.force_authenticate(admin_user)
    url = reverse("contacts-filter-by-project")
    response = api_client.get(url, {"project_id": project.id})
    assert response.status_code == 200
