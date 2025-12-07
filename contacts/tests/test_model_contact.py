from django.test import TestCase
from django.contrib.auth import get_user_model
from projects.models import Project
from contacts.models import Contact, ContactLog

User = get_user_model()

class ContactModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number='09164896609', password='12345')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)

    def test_create_contact(self):
        contact = Contact.objects.create(
            project=self.project,
            full_name='John Doe',
            phone='09123456789',
            email='john@example.com',
            created_by=self.user
        )
        self.assertEqual(str(contact), 'John Doe - 09123456789')
        self.assertEqual(contact.call_status, 'pending')
        self.assertTrue(contact.is_active)
        self.assertIsNone(contact.assigned_caller)

    def test_contactlog_creation(self):
        contact = Contact.objects.create(
            project=self.project,
            full_name='Jane Doe',
            phone='09987654321',
            created_by=self.user
        )
        log = ContactLog.objects.create(
            contact=contact,
            action='Created contact',
            performed_by=self.user
        )
        self.assertEqual(str(log), f'Created contact - {contact.full_name} at {log.timestamp}')
        self.assertEqual(log.contact, contact)
        self.assertEqual(log.performed_by, self.user)

    def test_get_last_call_empty(self):
        contact = Contact.objects.create(
            project=self.project,
            full_name='No Call User',
            phone='09000000000',
            created_by=self.user
        )
        self.assertIsNone(contact.get_last_call())
