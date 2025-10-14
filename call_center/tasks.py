# call_center/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Contact, ContactLog
from .tasks_utils import reassign_uncontacted_after_24h_logic
import random
import logging


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def remove_inactive_callers(self, days=7):
    try:
        # محاسبه زمان آستانه بی‌فعالیتی
        inactivity_threshold = timezone.now() - timedelta(days=days)

        # پیدا کردن مخاطبینی که باید تماس‌گیرنده آن‌ها حذف شود
        inactive_contacts = Contact.objects.filter(
            call_status='pending',
            assigned_caller__isnull=False,
            is_active=True,
            updated_at__lt=inactivity_threshold
        )

        updated_count = 0
        for contact in inactive_contacts:
            caller = contact.assigned_caller
            # ثبت لاگ
            ContactLog.objects.create(
                contact=contact,
                action=f"تماس‌گیرنده {caller.username} به دلیل بی‌فعالیتی پس از {days} روز حذف شد",
                performed_by=None
            )
            contact.assigned_caller = None
            contact.save()
            updated_count += 1

        print(f"Updated {updated_count} contacts by removing their assigned callers.")
        return updated_count
    except Exception as e:
        print(f"Error in remove_inactive_callers: {str(e)}")
        self.retry(countdown=60)  # تلاش مجدد پس از 60 ثانیه


@shared_task(bind=True, name="reassign_uncontacted_after_24h_task")
def reassign_uncontacted_after_24h_task(self):
    """
    تسک دوره‌ای برای بررسی مخاطبین بدون تماس پس از 24 ساعت.
    """
    try:
        count = reassign_uncontacted_after_24h_logic()
        return count
    except Exception as e:
        logger.error(f"Error in reassign_uncontacted_after_24h_task: {str(e)}", exc_info=True)
        raise self.retry(countdown=60)  # تلاش مجدد بعد از 60 ثانیه


def reassign_uncontacted_contacts(project):
    """
    بازتخصیص مخاطبین تماس‌نگرفته که بیش از 24 ساعت از آخرین تماس گذشته است.
    بازتخصیص به اولین تماس‌گیرنده فعال دیگر در همان پروژه.
    برمی‌گرداند تعداد مخاطبین بازتخصیص شده.
    """
    now = timezone.now()
    threshold_time = now - timedelta(hours=24)

    # مخاطبین در وضعیت pending یا contacted که بیش از 24 ساعت بدون تماس مانده‌اند
    uncontacted_contacts = Contact.objects.filter(
        project=project,
        is_active=True,
        updated_at__lte=threshold_time,
        call_status__in=['pending', 'contacted']
    )

    reassigned_count = 0

    for contact in uncontacted_contacts:
        # لیست تماس‌گیرندگان فعال پروژه به جز تماس‌گیرنده فعلی
        active_callers = project.project_callers.filter(is_active=True).exclude(caller=contact.assigned_caller)
        if not active_callers.exists():
            continue  # اگر تماس‌گیرنده دیگر موجود نیست، عبور کن

        # تخصیص به اولین تماس‌گیرنده موجود
        new_caller = active_callers.first().caller
        contact.assigned_caller = new_caller
        contact.updated_at = now  # به‌روزرسانی timestamp
        contact.save()
        reassigned_count += 1

    return reassigned_count

def unassign_inactive_special_contacts():
    """
    بررسی مخاطبین خاص (is_special=True) که تماس‌گیرنده دارند
    و در ۷۲ ساعت اخیر هیچ تماسی نداشتند → تماس‌گیرنده نال می‌شود.
    """
    now = timezone.now()
    threshold = now - timedelta(hours=72)

    # فقط مخاطبینی که تماس‌گیرنده دارند و ویژه هستند
    contacts = Contact.objects.filter(
        is_special=True,
        assigned_caller__isnull=False
    ).exclude(
        last_call_date__gte=threshold
    )

    for contact in contacts:
        contact.assigned_caller = None      # ✅ تماس‌گیرنده حذف شود
        contact.is_special = False          # ✅ دیگر خاص نیست
        contact.save(update_fields=['assigned_caller', 'is_special'])
        print(f"📞 تماس‌گیرنده از مخاطب '{contact.full_name}' جدا شد (تماسی در ۷۲ ساعت اخیر نداشته).")


from celery import shared_task

@shared_task
def check_special_contacts():
    unassign_inactive_special_contacts()