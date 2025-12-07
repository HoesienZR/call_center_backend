from django.conf import settings
from django.db import models
from django.db.models import Sum


class Project(models.Model):
    """Model for managing different call projects."""
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('completed', 'تکمیل شده'),
    ]
    show = models.BooleanField(default=False)
    name = models.CharField(max_length=100, verbose_name="نام پروژه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="وضعیت")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_projects',
        verbose_name="ایجاد شده توسط"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectMembership',
        related_name='projects',
        verbose_name="اعضای پروژه"
    )

    class Meta:
        verbose_name = "پروژه"
        verbose_name_plural = "پروژه‌ها"
        ordering = ['-created_at']
        permissions = [
            ('manage_project', 'Can manage project'),
        ]

    def __str__(self):
        return self.name

    def get_statistics(self):
        """Retrieve overall project statistics."""
        total_calls = self.calls.count()

        answered_calls = self.calls.filter(call_result='answered').count()
        no_answer_calls = self.calls.filter(call_result='no_answer').count()
        busy_calls = self.calls.filter(call_result='busy').count()
        unreachable_calls = self.calls.filter(call_result='unreachable').count()
        wrong_number_calls = self.calls.filter(call_result='wrong_number').count()
        not_interested_calls = self.calls.filter(call_result='not_interested').count()
        callback_requested_calls = self.calls.filter(call_result='callback_requested').count()

        total_duration = self.calls.aggregate(Sum('duration'))['duration__sum'] or 0
        average_duration = (total_duration / total_calls) if total_calls > 0 else 0

        success_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0

        return {
            'total_calls': total_calls,
            'call_results_distribution': {
                'answered': answered_calls,
                'no_answer': no_answer_calls,
                'busy': busy_calls,
                'unreachable': unreachable_calls,
                'wrong_number': wrong_number_calls,
                'not_interested': not_interested_calls,
                'callback_requested': callback_requested_calls,
            },
            'total_duration_seconds': total_duration,
            'average_call_duration_seconds': round(average_duration, 2),
            'success_rate': round(success_rate, 2)
        }

    def get_caller_performance_report(self):
        """Retrieve caller performance report for this project."""
        caller_performance = []
        for project_caller in self.project_callers.filter(user__is_active=True):
            caller = project_caller.user
            calls_by_caller = self.calls.filter(caller=caller)

            total_calls = calls_by_caller.count()
            answered_calls = calls_by_caller.filter(call_result='answered').count()
            total_duration = calls_by_caller.aggregate(Sum('duration'))['duration__sum'] or 0

            success_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0
            average_duration = (total_duration / total_calls) if total_calls > 0 else 0

            caller_performance.append({
                'caller_id': caller.id,
                'caller_phone': caller.phone_number,
                'caller_full_name': caller.get_full_name(),
                'total_calls': total_calls,
                'answered_calls': answered_calls,
                'success_rate': round(success_rate, 2),
                'total_duration_seconds': total_duration,
                'average_call_duration_seconds': round(average_duration, 2),
            })
        return caller_performance


class ProjectMembership(models.Model):
    """
    Intermediate model for defining user roles within each project.
    """
    ROLE_CHOICES = [
        ('admin', 'ادمین'),
        ('caller', 'تماس‌گیرنده'),
        ('contact', 'مخاطب'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name="پروژه", related_name="project_callers")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="نقش در پروژه")
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تخصیص")

    class Meta:
        verbose_name = "عضویت در پروژه"
        verbose_name_plural = "عضویت‌ها در پروژه‌ها"
        unique_together = ('project', 'user')
        indexes = [
            models.Index(fields=['role'])
        ]
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.user.username} as {self.get_role_display()} in {self.project.name}"


class Question(models.Model):
    """Model for project-related questions."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='questions', verbose_name="پروژه")
    text = models.CharField(max_length=200, verbose_name="متن سوال")

    class Meta:
        verbose_name = "سوال"
        verbose_name_plural = "سوالات"

    def __str__(self):
        return self.text


class AnswerChoice(models.Model):
    """Model for answer choices for each question."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices', verbose_name="سوال")
    text = models.CharField(max_length=100, verbose_name="متن گزینه")

    class Meta:
        verbose_name = "گزینه پاسخ"
        verbose_name_plural = "گزینه‌های پاسخ"

    def __str__(self):
        return self.text
