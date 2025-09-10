# call_center/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Contact, ContactLog


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