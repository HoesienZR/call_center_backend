from django.db.models.signals import post_save
from django.dispatch import receiver

from calls.models import Call


@receiver(post_save, sender=Call)
def update_contact_status_on_callback_request(sender, instance, created, **kwargs):
    """
    سیگنال برای تغییر وضعیت مخاطب به "pending" زمانی که نتیجه تماس "callback_requested" باشد
    """
    if instance.call_result == 'callback_requested':
        # به‌روزرسانی وضعیت مخاطب به "در انتظار تماس"
        contact = instance.contact
        contact.call_status = 'pending'
        contact.save(update_fields=['call_status'])

        # اختیاری: ثبت لاگ برای این تغییر
        from .models import ContactLog
        ContactLog.objects.create(
            contact=contact,
            action=f"وضعیت تماس به 'در انتظار' تغییر یافت بدلیل درخواست تماس مجدد در تماس شماره {instance.id}",
            performed_by=instance.caller
        )
