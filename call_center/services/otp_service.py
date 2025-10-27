import random
import requests
from django.conf import settings
from django.core.cache import cache

OTP_EXPIRY = 300        # 5 دقیقه
OTP_REQUEST_LIMIT = 180 # 3 دقیقه

def generate_otp():
    """تولید عدد تصادفی ۶ رقمی"""
    return f"{random.randint(0, 999999):06d}"

def store_otp(phone, otp_code):
    """ذخیره OTP در Redis"""
    cache.set(f"otp:{phone}", otp_code, timeout=OTP_EXPIRY)
    set_otp_request_limit(phone)

def get_cached_otp(phone):
    """خواندن OTP از Redis"""
    return cache.get(f"otp:{phone}")

def clear_otp(phone):
    """حذف OTP"""
    cache.delete(f"otp:{phone}")
    cache.delete(f"otp_limit:{phone}")

def can_request_otp(phone):
    """آیا مجاز به درخواست OTP جدید هست؟"""
    return cache.get(f"otp_limit:{phone}") is None

def set_otp_request_limit(phone):
    """تنظیم محدودیت برای جلوگیری از اسپم"""
    cache.set(f"otp_limit:{phone}", True, timeout=OTP_REQUEST_LIMIT)

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
