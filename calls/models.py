from django.conf import settings
from django.db import models

from calls.calls_import import Contact, Question, AnswerChoice, Project, ProjectMembership


# Model for storing call records
class Call(models.Model):
    """Model for storing call records"""

    CALL_RESULT_CHOICES = [
        ('interested', 'Interested'),
        ('no_time', 'No time'),
        ('not_interested', 'Not interested'),
    ]

    CALL_STATUS_CHOICES = [
        ('wrong_number', 'Wrong number'),
        ('answered', 'Answered'),
        ('no_answer', 'No answer'),
        ('pending', "Pending"),
    ]

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='calls', verbose_name="مخاطب")
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calls',
        verbose_name="تماس گیرنده"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='calls',
        verbose_name="پروژه"
    )
    call_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ تماس",
        db_index=True
    )
    call_result = models.CharField(
        max_length=50,
        choices=CALL_RESULT_CHOICES,
        verbose_name="جزییات تماس",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=CALL_STATUS_CHOICES,
        default='pending',
        verbose_name="وضعیت"
    )
    notes = models.TextField(blank=True, verbose_name="یادداشت")
    feedback = models.TextField(blank=True, verbose_name="بازخورد")
    detailed_report = models.TextField(blank=True, verbose_name="جزییات گزارش")
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="مدت تماس(به ثانیه)"
    )
    follow_up_required = models.BooleanField(default=False, verbose_name="نیاز به پیگیری دارد")
    follow_up_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پیگیری")

    is_editable = models.BooleanField(default=True, verbose_name="قابل تغییر")
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="تغییر داده شده در")
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_calls',
        verbose_name="تغییر کرده توسط"
    )
    edit_reason = models.TextField(blank=True, verbose_name="دلیل تغییر")

    original_data = models.JSONField(blank=True, verbose_name="داده اورجینال")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="ایجاد شده در")

    def can_edit(self, user):
        if not self.is_editable:
            return False
        if user.is_superuser:
            return True
        try:
            membership = ProjectMembership.objects.get(project=self.project, user=user)
            if membership.role == 'admin' or self.caller == user:
                return True
        except ProjectMembership.DoesNotExist:
            return False
        return False

    def save_original_data_if_first_edit(self):
        """Store original call data only on first edit"""
        if not self.original_data:
            original = {
                'call_result': self.call_result,
                'notes': self.notes,
                'duration': self.duration,
                'follow_up_required': self.follow_up_required,
                'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None
            }
            self.original_data = original

    def save(self, *args, **kwargs):
        self.save_original_data_if_first_edit()
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "تماسس"
        verbose_name_plural = "تماس ها"
        ordering = ['-call_date']
        indexes = [
            models.Index(fields=['call_date']),
            models.Index(fields=['contact']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f"{self.contact.full_name} - {self.caller.get_full_name()} - {self.get_call_result_display()}"

    def get_original_data(self):
        """Return original data as dict"""
        return self.original_data if self.original_data else {}

    def set_original_data(self, data_dict):
        """Set original data"""
        self.original_data = data_dict if data_dict else {}



# Model for storing answers to call questions
class CallAnswer(models.Model):
    """Model for storing answers to questions asked during a call"""

    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='answers', verbose_name="تماس")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="سوال")
    selected_choice = models.ForeignKey(
        AnswerChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="گزینه انتخاب شده"
    )

    class Meta:
        unique_together = ('call', 'question')  # Prevent duplicate answers for same call-question pair
        verbose_name = "پاسخ تماس"
        verbose_name_plural = "پاسخ تماس ها"

    def __str__(self):
        return f"{self.call} - {self.question.text}"
