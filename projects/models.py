from django.conf import settings
from django.db import models


# Create your models here.

class Project(models.Model):
    """مدل برای مدیریت پروژه‌های تماس مختلف"""
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('completed', 'تکمیل شده'),
    ]
    show = models.BooleanField(default=False)
    name = models.CharField(max_length=100, verbose_name="نام پروژه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="وضعیت")
    # ForeignKey به مدل کاربر سفارشی تغییر یافت
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_projects',
                                   verbose_name="ایجاد شده توسط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")
    # ارتباط با کاربران از طریق مدل واسط ProjectMembership
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ProjectMembership', related_name='projects',
                                     verbose_name="اعضای پروژه")

    # TODO it must get  queries optimised
    def get_statistics(self):
        """دریافت آمار کلی پروژه"""
        total_contacts = self.contacts.count()
        total_callers = self.project_callers.filter(is_active=True).count()
        total_calls = self.calls.count()

        answered_calls = self.calls.filter(call_result='answered').count()
        no_answer_calls = self.calls.filter(call_result='no_answer').count()
        busy_calls = self.calls.filter(call_result='busy').count()
        unreachable_calls = self.calls.filter(call_result='unreachable').count()
        wrong_number_calls = self.calls.filter(call_result='wrong_number').count()
        not_interested_calls = self.calls.filter(call_result='not_interested').count()
        callback_requested_calls = self.calls.filter(call_result='callback_requested').count()

        total_duration = self.calls.aggregate(models.Sum('duration'))['duration__sum'] or 0
        average_duration = (total_duration / total_calls) if total_calls > 0 else 0

        success_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0

        return {
            'total_contacts': total_contacts,
            'total_callers': total_callers,
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

    # TODO  it's must get optimised also
    def get_caller_performance_report(self):
        """دریافت گزارش عملکرد تماس‌گیرندگان برای این پروژه"""
        caller_performance = []
        for project_caller in self.project_callers.filter(is_active=True):
            caller = project_caller.caller
            calls_by_caller = self.calls.filter(caller=caller)

            total_calls = calls_by_caller.count()
            answered_calls = calls_by_caller.filter(call_result='answered').count()
            total_duration = calls_by_caller.aggregate(models.Sum('duration'))['duration__sum'] or 0

            success_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0
            average_duration = (total_duration / total_calls) if total_calls > 0 else 0

            caller_performance.append({
                'caller_id': caller.id,
                'caller_username': caller.username,
                'caller_full_name': caller.get_full_name(),
                'total_calls': total_calls,
                'answered_calls': answered_calls,
                'success_rate': round(success_rate, 2),
                'total_duration_seconds': total_duration,
                'average_call_duration_seconds': round(average_duration, 2),
            })
        return caller_performance

    # TODO it's must get deleted  have no use
    def get_call_status_over_time(self, start_date=None, end_date=None, interval='day'):
        """
        دریافت وضعیت تماس‌ها در طول زمان برای داشبورد.
        interval می‌تواند 'day', 'week', 'month' باشد.
        """
        calls = self.calls.all()
        if start_date:
            calls = calls.filter(call_date__gte=start_date)
        if end_date:
            calls = calls.filter(call_date__lte=end_date)

        if interval == 'day':
            date_format = '%Y-%m-%d'
        elif interval == 'week':
            date_format = '%Y-%W'
        elif interval == 'month':
            date_format = '%Y-%m'
        else:
            raise ValueError("Invalid interval. Must be 'day', 'week', or 'month'.")

        # Group by date and call result
        data = calls.annotate(
            date=functions.Extract('call_date', interval)
        ).values('date', 'call_result').annotate(count=models.Count('id')).order_by('date', 'call_result')

        # Format for chart
        chart_data = {}
        for item in data:
            date_key = item['date']
            if date_key not in chart_data:
                chart_data[date_key] = {
                    'date': item['date'],
                    'total_calls': 0
                }
                for choice, _ in Call.CALL_RESULT_CHOICES:
                    chart_data[date_key][choice] = 0

            chart_data[date_key][item['call_result']] = item['count']
            chart_data[date_key]['total_calls'] += item['count']

        return list(chart_data.values())

    class Meta:
        verbose_name = "پروژه"
        verbose_name_plural = "پروژه‌ها"
        ordering = ['-created_at']
        permissions = [
            ('manage_project', 'Can manage project'),
        ]

    def __str__(self):
        return self.name

    # ... (متدهای دیگر مدل Project بدون تغییر باقی می‌مانند)


# 2. مدل جدید برای مدیریت سطوح دسترسی کاربران در هر پروژه
class ProjectMembership(models.Model):
    """
    مدل واسط برای تعیین نقش کاربران در هر پروژه.
    """
    ROLE_CHOICES = [
        ('admin', 'ادمین'),
        ('caller', 'تماس‌گیرنده'),
        ('contact', 'مخاطب'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name="پروژه")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="نقش در پروژه")
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تخصیص")

    class Meta:
        verbose_name = "عضویت در پروژه"
        verbose_name_plural = "عضویت‌ها در پروژه‌ها"
        # unique_together = ('project', 'user') # هر کاربر در هر پروژه فقط یک نقش می‌تواند داشته باشد
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.user.username} as {self.get_role_display()} in {self.project.name}"


class ProjectCaller(models.Model):
    """مدل برای تخصیص تماس‌گیرندگان به پروژه‌ها"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_callers', verbose_name="پروژه")
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_assignments',
                               verbose_name="تماس‌گیرنده")
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تخصیص")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    def clean(self):
        if not self.caller.profile.role == 'caller':
            raise ValidationError("کاربر باید تماس‌گیرنده باشد.")
        super().clean()

    class Meta:
        verbose_name = "تخصیص تماس‌گیرنده"
        verbose_name_plural = "تخصیص تماس‌گیرندگان"
        unique_together = ['project', 'caller']
        ordering = ['assigned_at']

    def __str__(self):
        return f"{self.caller.get_full_name()} - {self.project.name}"
