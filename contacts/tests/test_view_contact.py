import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from contacts.models import Contact
from projects.models import ProjectMembership, Project

User = get_user_model()

@pytest.fixture
def setup_users_projects_contacts(db):
    # Users
    admin_user = User.objects.create_user(username='adminuser', password='12345', phone_number='09120000001', is_active=True)
    caller_user = User.objects.create_user(username='calleruser', password='12345', phone_number='09120000002', is_active=True)
    viewer_user = User.objects.create_user(username='vieweruser', password='12345', phone_number='09120000003', is_active=True)
    super_user = User.objects.create_superuser(username='superuser', password='12345', phone_number='09120000004', is_superuser=True, is_active=True, is_staff=True)

    # Project
    project = Project.objects.create(name='Sample Project', created_by=admin_user)

    # Memberships
    ProjectMembership.objects.get_or_create(project=project, user=admin_user, role='admin')
    ProjectMembership.objects.get_or_create(project=project, user=caller_user, role='caller')
    ProjectMembership.objects.get_or_create(project=project, user=viewer_user, role='viewer')

    # Contacts
    contact1 = Contact.objects.create(full_name="John Doe", phone="09112223344",
                                      project=project, assigned_caller=caller_user,
                                      call_status="pending", is_active=True)
    contact2 = Contact.objects.create(full_name="Jane Smith", phone="09113334455",
                                      project=project, assigned_caller=None,
                                      call_status="pending", is_active=True)

    return {
        'admin': admin_user,
        'caller': caller_user,
        'viewer': viewer_user,
        'superuser': super_user,
        'project': project,
        'contacts': [contact1, contact2]
    }

@pytest.fixture
def api_client():
    return APIClient()


# ----------------- TESTS -----------------
@pytest.mark.django_db
def test_list_contacts_permissions(setup_users_projects_contacts, api_client):
    users = setup_users_projects_contacts

    url = reverse('contacts-list')
    print(url)

    # Admin sees all project contacts
    api_client.force_authenticate(users['admin'])
    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) == 2

    # Caller sees only assigned contacts
    api_client.force_authenticate(users['caller'])
    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert all(c['assigned_caller'] is not None for c in res.data)

    # Viewer sees only assigned contacts (یا none)
    api_client.force_authenticate(users['viewer'])
    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK

    # Superuser sees all
    api_client.force_authenticate(users['superuser'])
    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) == 2


@pytest.mark.django_db
def test_request_new_contact_permission(setup_users_projects_contacts, api_client):
    users = setup_users_projects_contacts
    project = users['project']
    url = reverse('contacts-request-new')  # نام action باید تو viewset مشخص باشه: @action(detail=False, name='request-new')

    # Caller can request new contact
    api_client.force_authenticate(users['caller'])
    res = api_client.post(url, {'project_id': project.id})
    assert res.status_code == status.HTTP_200_OK

    # Admin cannot request new contact
    api_client.force_authenticate(users['admin'])
    res = api_client.post(url, {'project_id': project.id})
    assert res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

    # Viewer cannot request
    api_client.force_authenticate(users['viewer'])
    res = api_client.post(url, {'project_id': project.id})
    assert res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]


@pytest.mark.django_db
def test_release_contact_permission(setup_users_projects_contacts, api_client):
    users = setup_users_projects_contacts
    contact = users['contacts'][0]  # assigned to caller
    url = reverse('contacts-release', args=[contact.id])  # @action(detail=True, name='release')

    # Assigned caller can release
    api_client.force_authenticate(users['caller'])
    res = api_client.post(url)
    assert res.status_code == status.HTTP_200_OK
    contact.refresh_from_db()
    assert contact.assigned_caller is None

    # Admin cannot release
    api_client.force_authenticate(users['admin'])
    res = api_client.post(url)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Viewer cannot release
    api_client.force_authenticate(users['viewer'])
    res = api_client.post(url)
    assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_contact_stats_access(setup_users_projects_contacts, api_client):
    users = setup_users_projects_contacts
    contact = users['contacts'][0]
    url = reverse('contacts-stats', args=[contact.id])  # @action(detail=True, name='stats')

    # All project members and superuser can access stats
    for key in ['admin', 'caller', 'viewer', 'superuser']:
        api_client.force_authenticate(users[key])
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        assert "total_calls" in res.data


@pytest.mark.django_db
def test_filter_by_status_and_project(setup_users_projects_contacts, api_client):
    users = setup_users_projects_contacts
    project = users['project']
    Contact.objects.create(full_name="C1", phone="0900", project=project, call_status="pending")
    Contact.objects.create(full_name="C2", phone="0901", project=project, call_status="done")

    api_client.force_authenticate(users['admin'])
    # filter_by_status
    url_status = reverse('contacts-filter-by-status') + '?status=pending'
    res = api_client.get(url_status)
    assert res.status_code == status.HTTP_200_OK
    for item in res.data:
        assert item["call_status"] == "pending"

    # filter_by_project
    url_project = reverse('contacts-filter-by-project') + f'?project_id={project.id}'
    res = api_client.get(url_project)
    assert res.status_code == status.HTTP_200_OK
    for item in res.data:
        assert item["project"] == project.id


@pytest.mark.django_db
def test_crud_contacts_permissions(setup_users_projects_contacts, api_client):
    users = setup_users_projects_contacts
    project = users['project']
    url_list = reverse('contacts-list')

    # Create contact as admin
    api_client.force_authenticate(users['admin'])
    res = api_client.post(url_list, {
        "full_name": "New Contact",
        "phone": "09124445566",
        "project": project.id
    })
    assert res.status_code == status.HTTP_201_CREATED

    contact_id = res.data['id']
    url_detail = reverse('contacts-detail', args=[contact_id])

    # Retrieve contact
    res = api_client.get(url_detail)
    assert res.status_code == status.HTTP_200_OK

    # Update contact
    res = api_client.patch(url_detail, {"full_name": "Updated Contact"})
    assert res.status_code == status.HTTP_200_OK
    assert res.data['full_name'] == "Updated Contact"

    # Delete contact (if allowed)
    res = api_client.delete(url_detail)
    assert res.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN]
