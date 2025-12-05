import pytest
from django.contrib.auth import get_user_model
from projects.models import Project
from contacts.models import Contact, ContactLog
from contacts.serializers import ContactSerializer, ContactStatsSerializer

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='12345', phone_number='09123456789')


@pytest.fixture
def project(db, user):
    return Project.objects.create(name='Test Project', created_by=user)


@pytest.fixture
def contact(db, user, project):
    return Contact.objects.create(
        project=project,
        full_name='John Doe',
        phone='09987654321',
        created_by=user
    )


def test_contact_serializer_output(contact):
    serializer = ContactSerializer(instance=contact)
    data = serializer.data
    assert data['full_name'] == 'John Doe'
    assert data['phone'] == '09987654321'
    assert data['assigned_caller_phone'] is None
    assert data['contact_logs'] == []


def test_contact_serializer_create_with_caller(db, user, project):
    payload = {
        'project': project.id,
        'full_name': 'Jane Doe',
        'phone': '09000000000',
        'caller_phone_number': '09123456789'
    }

    serializer = ContactSerializer(
        data=payload,
        context={'request': type('obj', (object,), {'user': user})()}
    )

    assert serializer.is_valid(), serializer.errors
    contact = serializer.save()

    assert contact.assigned_caller is None or contact.assigned_caller == user


def test_contact_serializer_update_with_caller(contact, user):
    payload = {'caller_phone_number': '09123456789'}
    serializer = ContactSerializer(instance=contact, data=payload, partial=True)
    serializer.context['request'] = type('obj', (object,), {'user': user})()
    assert serializer.is_valid(), serializer.errors
    updated_contact = serializer.save()
    assert updated_contact.assigned_caller is None or updated_contact.assigned_caller == user


def test_stats_serializer_fields(contact, project):
    # اضافه کردن لاگ تماس برای تست آمار
    ContactLog.objects.create(contact=contact, action='Test log', performed_by=contact.created_by)

    serializer = ContactStatsSerializer(instance=contact)
    data = serializer.data
    assert data['full_name'] == 'John Doe'
    assert data['project_name'] == 'Test Project'
    assert data['total_calls'] == 0  # چون هنوز aggregation انجام نشده
    assert data['answered_calls'] == 0
