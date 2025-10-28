from django.conf import settings
from django.db import models

from contacts.models import Contact
from files.models import Question, AnswerChoice
from projects.models import Project


# Create your models here.

class Call(models.Model):
    """مدل برای ثبت تماس‌ها"""
    CALL_RESULT_CHOICES = [
        ('interested', 'علاقه‌مند هست'),
        ('no_time', 'وقت ندارد'),
        ('not_interested', 'علاقه‌مند نیست'),
    ]

    CALL_STATUS_CHOICES = [
        ('wrong_number', 'شماره اشتباه'),
        ('answered', 'پاسخ داد'),
        ('no_answer', 'پاسخ نداد'),
        ('pending', "در انتظار")
    ]
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='calls', verbose_name="مخاطب")
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calls',
                               verbose_name="تماس‌گیرنده")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='calls', verbose_name="پروژه")
    call_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تماس")
    call_result = models.CharField(max_length=50, choices=CALL_RESULT_CHOICES, verbose_name="نتیجه تماس", blank=True,
                                   null=True)
    status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    notes = models.TextField(blank=True, verbose_name="یادداشت‌ها")
    feedback = models.TextField(blank=True, verbose_name="بازخورد")
    detailed_report = models.TextField(blank=True, verbose_name="گزارش تفصیلی")
    duration = models.PositiveIntegerField(null=True, blank=True, verbose_name="مدت تماس (ثانیه)")
    follow_up_required = models.BooleanField(default=False, verbose_name="نیاز به پیگیری")
    follow_up_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پیگیری")
    is_editable = models.BooleanField(default=True, verbose_name="قابل ویرایش")
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ ویرایش")
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_calls',
        verbose_name="ویرایش شده توسط"
    )
    edit_reason = models.TextField(blank=True, verbose_name="دلیل ویرایش")
    original_data = models.TextField(blank=True, verbose_name="داده‌های اصلی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    def can_edit(self, user):
        if not self.is_editable:
            return False
        if user.is_superuser:
            return True
        # بررسی اینکه آیا کاربر ادمین پروژه است یا همان تماس‌گیرنده است
        try:
            membership = ProjectMembership.objects.get(project=self.project, user=user)
            if membership.role == 'admin' or self.caller == user:
                return True
        except ProjectMembership.DoesNotExist:
            return False
        return False

    class Meta:
        verbose_name = "تماس"
        verbose_name_plural = "تماس‌ها"
        ordering = ['-call_date']

    def __str__(self):
        return f"{self.contact.full_name} - {self.caller.get_full_name()} - {self.get_call_result_display()}"

    def get_original_data(self):
        """دریافت داده‌های اصلی به صورت dict"""
        if self.original_data:
            try:
                return json.loads(self.original_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_original_data(self, data_dict):
        """تنظیم داده‌های اصلی"""
        if data_dict:
            self.original_data = json.dumps(data_dict, ensure_ascii=False)
        else:
            self.original_data = ""

    def save_original_data_if_first_edit(self):
        """ذخیره داده‌های اصلی در صورت اولین ویرایش"""
        if not self.original_data:
            original = {
                'call_result': self.call_result,
                'notes': self.notes,
                'duration': self.duration,
                'follow_up_required': self.follow_up_required,
                'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None
            }
            self.set_original_data(original)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # به‌روزرسانی آمار پس از ذخیره
        self.update_call_statistics()

    def update_call_statistics(self):
        """به‌روزرسانی آمار تماس‌ها"""
        stats, created = CallStatistics.objects.get_or_create(
            contact=self.contact,
            project=self.project
        )
        stats.update_statistics()


class CallEditHistory(models.Model):
    """مدل برای تاریخچه ویرایش تماس‌ها"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='edit_history', verbose_name="تماس")
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='call_edits',
                                  verbose_name="ویرایش شده توسط")
    edit_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ویرایش")
    field_name = models.CharField(max_length=50, verbose_name="نام فیلد")
    old_value = models.TextField(blank=True, verbose_name="مقدار قبلی")
    new_value = models.TextField(blank=True, verbose_name="مقدار جدید")
    edit_reason = models.TextField(blank=True, verbose_name="دلیل ویرایش")

    class Meta:
        verbose_name = "تاریخچه ویرایش تماس"
        verbose_name_plural = "تاریخچه ویرایش تماس‌ها"
        ordering = ['-edit_date']

    def __str__(self):
        return f"{self.call.id} - {self.field_name} - {self.edited_by.get_full_name()}"


class CallAnswer(models.Model):
    """مدل واسط برای پاسخ‌های تماس به سوالات"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='answers', verbose_name="تماس")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="سوال")
    selected_choice = models.ForeignKey(AnswerChoice, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name="گزینه انتخاب‌شده")

    class Meta:
        unique_together = ('call', 'question')  # Prevent duplicate answers per call-question pair
        verbose_name = "پاسخ تماس"
        verbose_name_plural = "پاسخ‌های تماس"

    def __str__(self):
        return f"{self.call} - {self.question.text}"
