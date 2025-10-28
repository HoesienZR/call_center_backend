from django.conf import settings
from django.db import models

from projects.models import Project


# Create your models here.

class Contact(models.Model):
    CALL_STATUS_CHOICES = [
        ('wrong_number', 'شماره اشتباه'),
        ('answered', 'پاسخ داد'),
        ('no_answer', 'پاسخ نداد'),
        ('pending', 'در حال انتظار')
    ]
    is_special = models.BooleanField(default=False)
    GENDER_CHOICES = [
        ('male', 'مرد'),
        ("female", "زن"),
        ("none", "ترجیح میدهم که نگویم")
    ]
    birth_date = models.DateField(null=True, blank=True, verbose_name="تاریخ تولد")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_contact",
                                verbose_name="کاربر مخاطب", blank=True, null=True)
    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="contacts", verbose_name="پروژه")
    full_name = models.CharField(max_length=100, verbose_name="نام کامل")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    email = models.EmailField(blank=True, verbose_name="ایمیل")
    address = models.TextField(blank=True, verbose_name="آدرس")
    assigned_caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_contacts",
        verbose_name="تماس‌گیرنده تخصیص داده شده"
    )
    call_status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default="pending",
                                   verbose_name="وضعیت تماس")
    last_call_date = models.DateTimeField(null=True, blank=True, verbose_name="آخرین تماس")
    custom_fields = models.TextField(blank=True, verbose_name="فیلدهای سفارشی", null=True)
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="created_contacts", null=True, blank=True,
                                   on_delete=models.CASCADE, verbose_name="ایجاد شده توسط")
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default="none")

    class Meta:
        verbose_name = "مخاطب"
        verbose_name_plural = "مخاطبین"
        unique_together = ["project", "phone"]
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} - {self.phone}"

    def get_custom_fields(self):
        if self.custom_fields:
            try:
                return json.loads(self.custom_fields)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_custom_fields(self, fields_dict):
        if fields_dict:
            self.custom_fields = json.dumps(fields_dict, ensure_ascii=False)
        else:
            self.custom_fields = ""

    def get_call_statistics(self):
        try:
            stats = self.call_statistics.get(project=self.project)
            return {
                "total_calls": stats.total_calls,
                "successful_calls": stats.successful_calls,
                "response_rate": float(stats.response_rate),
                "last_call_date": stats.last_call_date,
                "last_call_result": stats.last_call_result
            }
        except CallStatistics.DoesNotExist:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "response_rate": 0.0,
                "last_call_date": None,
                "last_call_result": None
            }

    def get_last_call(self):
        last_call = self.calls.order_by("-call_date").first()
        return last_call


class ContactLog(models.Model):
    action = models.CharField(verbose_name="اقدام", max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان")
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE, related_name='logs', verbose_name="مخاطب")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="انجام شده توسط"
    )

    class Meta:
        verbose_name = "لاگ مخاطب"
        verbose_name_plural = "لاگ‌های مخاطب"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} - {self.contact.full_name} at {self.timestamp}"
