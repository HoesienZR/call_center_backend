from django.contrib.auth import get_user_model
from django.db import models

from projects.models import Project

User = get_user_model()


class Contact(models.Model):
    CALL_STATUS_CHOICES = [
        ('answered', 'پاسخ داد'),
        ('no_answer', 'پاسخ نداد'),
        ('pending', 'در حال انتظار')
    ]
    GENDER_CHOICES = [
        ('male', 'مرد'),
        ("female", "زن"),
        ("none", "ترجیح میدهم که نگویم")
    ]

    is_special = models.BooleanField(default=False)
    birth_date = models.DateField(null=True, blank=True, verbose_name="تاریخ تولد")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="contacts", verbose_name="پروژه")
    full_name = models.CharField(max_length=100, verbose_name="نام کامل")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    email = models.EmailField(blank=True, verbose_name="ایمیل")
    address = models.TextField(blank=True, verbose_name="آدرس")
    assigned_caller = models.ForeignKey(
        User,
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
    created_by = models.ForeignKey(get_user_model(), related_name="created_contacts", null=True, blank=True,
                                   on_delete=models.CASCADE, verbose_name="ایجاد شده توسط")
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default="none")

    class Meta:
        indexes = [
            models.Index(fields=['project', 'assigned_caller', 'call_status', 'is_active']),
            models.Index(fields=['gender']),
        ]
        verbose_name = "مخاطب"
        verbose_name_plural = "مخاطبین"
        unique_together = ["project", "phone"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} - {self.phone}"

    def get_last_call(self):
        return self.calls.order_by("-call_date").first()


class ContactLog(models.Model):
    action = models.CharField(verbose_name="اقدام", max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان")
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE, related_name='logs', verbose_name="مخاطب")
    performed_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="انجام شده توسط"
    )

    class Meta:
        verbose_name = "لاگ مخاطب"
        verbose_name_plural = "لاگ‌های مخاطب"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.action} - {self.contact.full_name} at {self.timestamp}"
