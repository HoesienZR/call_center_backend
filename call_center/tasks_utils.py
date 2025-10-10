from datetime import timedelta
import random
from django.utils import timezone
from .models import Contact
from .utils import get_available_callers_for_project
import logging

logger = logging.getLogger(__name__)

def reassign_uncontacted_after_24h_logic():
    """
    بررسی مخاطبین که پس از 24 ساعت هنوز تماس نگرفته‌اند و بازتخصیص آن‌ها.
    """
    threshold_time = timezone.now() - timedelta(hours=24)
    stale_contacts = Contact.objects.filter(
        call_status='pending',
        is_active=True,
        updated_at__lt=threshold_time
    )

    reassigned_count = 0
    for contact in stale_contacts:
        project = contact.project
        available_callers = get_available_callers_for_project(project)

        if contact.assigned_caller in available_callers:
            available_callers.remove(contact.assigned_caller)

        if not available_callers:
            logger.warning(f"No available callers to reassign contact {contact.id}")
            continue

        new_caller = random.choice(available_callers)
        old_caller = contact.assigned_caller
        contact.assigned_caller = new_caller
        contact.save(update_fields=['assigned_caller'])

        contact.logs.create(
            action=(
                f"مخاطب به تماس‌گیرنده {new_caller.username} "
                f"پس از 24 ساعت بدون تماس از {old_caller.username if old_caller else 'None'} منتقل شد"
            ),
            performed_by=None
        )
        reassigned_count += 1

    logger.info(f"Reassigned {reassigned_count} contacts after 24h of no contact.")
    return reassigned_count
