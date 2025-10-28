import re

def normalize_phone_number(phone):

    if not phone:
        return phone

    # حذف فاصله‌ها و کاراکترهای اضافی
    phone = re.sub(r'[\s\-\(\)]', '', phone)

    # تبدیل به فرمت استاندارد
    if phone.startswith('+98'):
        phone = '0' + phone[3:]
    elif phone.startswith('0098'):
        phone = '0' + phone[4:]
    elif phone.startswith('98') and len(phone) == 12:
        phone = '0' + phone[2:]

    return phone


def validate_phone_number(phone):
    """
    اعتبارسنجی شماره تلفن
    فرمت‌های مجاز: 09123456789, +989123456789, 00989123456789
    """
    if not phone:
        return False, "شماره تلفن خالی است"

    # حذف فاصله‌ها و کاراکترهای اضافی
    phone = re.sub(r'[\s\-\(\)]', '', phone)

    # بررسی فرمت‌های مختلف شماره تلفن ایرانی
    patterns = [
        r'^09\d{9}$',  # 09123456789
        r'^\+989\d{9}$',  # +989123456789
        r'^00989\d{9}$',  # 00989123456789
    ]

    for pattern in patterns:
        if re.match(pattern, phone):
            return True, phone

    return False, "فرمت شماره تلفن نامعتبر است"
