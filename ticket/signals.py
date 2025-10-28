from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Ticket


@receiver(post_save, sender=Ticket)
def send_message_to_developer(sender, instance: Ticket, created, **kwargs):
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
