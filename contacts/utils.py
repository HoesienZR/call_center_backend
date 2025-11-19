from contacts.models import Contact
from projects.models import Project


def check_if_available_contact(project:Project):
    available_contact = Contact.objects.filter(
        project=project,
        assigned_caller__isnull=True,
        call_status='pending',
        is_active=True
    ).first()
    return available_contact

def assign_available_contact(project, user):
    contact = check_if_available_contact(project=project)
    if contact:
        contact.assigned_caller = user
        contact.save()
        return True
    return False