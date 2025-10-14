from django.db.models.signals import post_save
from django.dispatch import receiver

from call_center.models import Call
import requests
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Call, Contact,Ticket
from django.conf import settings
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

@receiver(post_save, sender=Ticket)
def send_message_to_developer(sender, instance:Ticket, created, **kwargs):
    user = instance.user.first_name + " " + instance.user.last_name
    phone_number = instance.user.phone_number
    title = instance.title
    description = instance.description
    username = settings.TSMS_USERNAME
    password = settings.TSMS_PASSWORD
    from_number = settings.TSMS_FROM_NUMBER
    dev_number = settings.DEV_PHONE
    send_sms_url = (
        f"http://tsms.ir/url/tsmshttp.php?"
        f"from={from_number}&to={dev_number}&username={username}&password={password}&"
        f"message=کاربر با شماره: {phone_number}\n"
        f"نام کاربری: {user}\n"
        f"یک درخواست با عنوان: {title}\n"
        f"و محتوا: {description}\n"
        f"ارسال کرد."
    )
    result = requests.get(send_sms_url)
    print(result)
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