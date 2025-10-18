# call_center/tasks.py
from django.utils import timezone
from datetime import timedelta
from .models import Contact

import logging
from celery import shared_task

logger = logging.getLogger(__name__)
def unassign_inactive_special_contacts():
    """
    بررسی مخاطبین خاص (is_special=True) که تماس‌گیرنده دارند
    و در ۷۲ ساعت اخیر هیچ تماسی نداشتند → تماس‌گیرنده نال می‌شود.
    """
    now = timezone.now()
    threshold = now - timedelta(hours=72)

    # فقط مخاطبینی که تماس‌گیرنده دارند و ویژه هستند
    contacts = Contact.objects.filter(
        is_special=True,
        assigned_caller__isnull=False
    ).exclude(
        last_call_date__gte=threshold
    )

    for contact in contacts:
        contact.assigned_caller = None      # ✅ تماس‌گیرنده حذف شود
        contact.is_special = False          # ✅ دیگر خاص نیست
        contact.save(update_fields=['assigned_caller', 'is_special'])
        print(f"📞 تماس‌گیرنده از مخاطب '{contact.full_name}' جدا شد (تماسی در ۷۲ ساعت اخیر نداشته).")

@shared_task
def check_special_contacts():
    unassign_inactive_special_contacts()