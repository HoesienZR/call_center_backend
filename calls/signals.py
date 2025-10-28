from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Call


@receiver(post_save, sender=Call)
def update_contact_call_status(sender, instance, created, **kwargs):
    """
    بعد از ذخیره هر تماس، وضعیت تماس مخاطب را به‌روزرسانی کن
    """
    if instance.contact:
        instance.contact.call_status = instance.status
        instance.contact.last_call_date = instance.call_date
        instance.contact.save(update_fields=['call_status', 'last_call_date'])
