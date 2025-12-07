import pandas as pd
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from io import BytesIO

from projects.models import Project, ProjectMembership
from users.models import CustomUser


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(phone_number="09120000001", is_staff=True, password="12345")


@pytest.fixture
def project(db, admin_user):
    p = Project.objects.create(name="Excel Project", created_by=admin_user)
    ProjectMembership.objects.create(project=p, user=admin_user, role="admin")
    return p


def generate_xlsx_file():
    data = {
        "full_name": ["Test User 1", "Test User 2"],
        "contact_phone": ["09123456789", "09129876543"]
    }

    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return output


def test_import_contacts_success(api_client, admin_user, project):
    api_client.force_authenticate(admin_user)
    url = reverse("import-contacts", kwargs={"project_id": project.id})
    excel_file = generate_xlsx_file()
    response = api_client.post(url, {"file": excel_file}, format="multipart")
    assert response.status_code == 201
    assert response.data["created_count"] == 2
    assert response.data["project"] == project.name
