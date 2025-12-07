from django.db.models.signals import post_save
from django.dispatch import receiver

from calls.models import Call


@receiver(post_save, sender=Call)
def update_contact_status_on_callback_request(sender, instance, created, **kwargs):
    """
    Signal: Update contact status to "pending" when the call result is "callback_requested".
    """
    if instance.call_result == 'callback_requested':
        # Update the contact's status to "pending"
        contact = instance.contact
        contact.call_status = 'pending'
        contact.save(update_fields=['call_status'])

        from .models import ContactLog
        ContactLog.objects.create(
            contact=contact,
            action=(
                f"Call status changed to 'pending' due to a callback request "
                f"from call ID {instance.id}"
            ),
            performed_by=instance.caller
        )
