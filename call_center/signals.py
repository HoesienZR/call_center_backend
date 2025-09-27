from django.db.models.signals import post_save
from django.dispatch import receiver

from call_center.models import Call

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Call, Contact

@receiver(post_save, sender=Call)
def update_contact_call_status(sender, instance, created, **kwargs):
    """
    بعد از ذخیره هر تماس، وضعیت تماس مخاطب را به‌روزرسانی کن
    """
    if instance.contact:
        instance.contact.call_status = instance.status
        instance.contact.last_call_date = instance.call_date
        instance.contact.save(update_fields=['call_status', 'last_call_date'])


# signals.py



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