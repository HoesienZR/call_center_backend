import random
import requests
from django.conf import settings

OTP_EXPIRY = 300        # 5 دقیقه
OTP_REQUEST_LIMIT = 180 # 3 دقیقه

def generate_otp():
    return str(random.randint(100000, 999999))

def store_otp(request, phone, otp_code):
    request.session[f"otp:{phone}"] = otp_code
    request.session[f"otp_limit:{phone}"] = True
    request.session.set_expiry(OTP_EXPIRY)

def get_cached_otp(request, phone):
    return request.session.get(f"otp:{phone}")

def clear_otp(request, phone):
    if f"otp:{phone}" in request.session:
        del request.session[f"otp:{phone}"]
    if f"otp_limit:{phone}" in request.session:
        del request.session[f"otp_limit:{phone}"]

def can_request_otp(request, phone):
    return f"otp_limit:{phone}" not in request.session

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
