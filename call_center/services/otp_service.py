import random
import requests
from django.conf import settings
from django.core.cache import cache

OTP_EXPIRY = 300        # 5 دقیقه
OTP_REQUEST_LIMIT = 180 # 3 دقیقه

def generate_otp():
    return str(random.randint(100000, 999999))

def store_otp(phone, otp_code):
    cache.set(f"otp:{phone}", otp_code, timeout=OTP_EXPIRY)
    cache.set(f"otp_limit:{phone}", True, timeout=OTP_REQUEST_LIMIT)

def get_cached_otp(phone):
    return cache.get(f"otp:{phone}")

def clear_otp(phone):
    cache.delete(f"otp:{phone}")

def can_request_otp(phone):
    return cache.get(f"otp_limit:{phone}") is None

def send_sms(phone, otp_code):
    username = settings.TSMS_USERNAME
    password = settings.TSMS_PASSWORD
    from_number = settings.TSMS_FROM_NUMBER
    message = f"کد تایید شما: {otp_code}"

    send_sms_url = (
        f"http://tsms.ir/url/tsmshttp.php?"
        f"from={from_number}&to={phone}&username={username}&password={password}&message={message}"
    )

    resp = requests.get(send_sms_url)
    return resp.status_code == 200
