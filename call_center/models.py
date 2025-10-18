
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

import json



# 1. مدل کاربر سفارشی با فیلد شماره موبایل و اجازه ساخت پروژه
class CustomUser(AbstractUser):
    """
    مدل کاربر سفارشی که شماره موبایل و اجازه ساخت پروژه را نیز شامل می‌شود.
    """
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="شماره موبایل",)
    can_create_projects = models.BooleanField(default=False, verbose_name="می‌تواند پروژه بسازد")
    def __str__(self):
        return self.username

class Project(models.Model):
    """مدل برای مدیریت پروژه‌های تماس مختلف"""
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('completed', 'تکمیل شده'),
    ]
    show  = models.BooleanField(default=False)
    name = models.CharField(max_length=100, verbose_name="نام پروژه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="وضعیت")
    # ForeignKey به مدل کاربر سفارشی تغییر یافت
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_projects',
                                   verbose_name="ایجاد شده توسط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")
    # ارتباط با کاربران از طریق مدل واسط ProjectMembership
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ProjectMembership', related_name='projects', verbose_name="اعضای پروژه")
    #TODO it must get  queries optimised
    def get_statistics(self):
        """دریافت آمار کلی پروژه"""
        total_contacts = self.contacts.count()
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


    class Meta:
        verbose_name = "پروژه"
        verbose_name_plural = "پروژه‌ها"
        ordering = ['-created_at']
        permissions = [
            ('manage_project', 'Can manage project'),
        ]

    def __str__(self):
        return self.name


class ProjectMembership(models.Model):
    """
    مدل واسط برای تعیین نقش کاربران در هر پروژه.
    """
    ROLE_CHOICES = [
        ('admin', 'ادمین'),
        ('caller', 'تماس‌گیرنده'),
        ('regular', 'عادی'),
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

class Contact(models.Model):
    CALL_STATUS_CHOICES = [
        ('wrong_number', 'شماره اشتباه'),
        ('answered', 'پاسخ داد'),
        ('no_answer', 'پاسخ نداد'),
        ('pending', 'در حال انتظار')
    ]
    is_special = models.BooleanField(default=False)
    GENDER_CHOICES = [
        ('male','مرد'),
        ("female","زن"),
        ("none","ترجیح میدهم که نگویم")
                        ]
    birth_date  = models.DateField(null=True,blank=True,verbose_name="تاریخ تولد")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_contact", verbose_name="کاربر مخاطب", blank=True, null=True)
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
    custom_fields = models.TextField(blank=True, verbose_name="فیلدهای سفارشی",null=True)
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,related_name="created_contacts", null=True,blank=True,on_delete=models.CASCADE,verbose_name="ایجاد شده توسط")
    gender = models.CharField(max_length=20,choices=GENDER_CHOICES,default="none")
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

    def get_last_call(self):
        last_call = self.calls.order_by("-call_date").first()
        return last_call
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
        ('pending',"در انتظار")
    ]
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='calls', verbose_name="مخاطب")
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calls',
                               verbose_name="تماس‌گیرنده")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='calls', verbose_name="پروژه")
    call_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تماس")
    call_result = models.CharField(max_length=50, choices=CALL_RESULT_CHOICES, verbose_name="نتیجه تماس",blank=True,null=True)
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

class Question(models.Model):
    """مدل برای سوالات مرتبط با پروژه"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='questions', verbose_name="پروژه")
    text = models.CharField(max_length=200, verbose_name="متن سوال")

    class Meta:
        verbose_name = "سوال"
        verbose_name_plural = "سوالات"

    def __str__(self):
        return self.text
class AnswerChoice(models.Model):
    """مدل برای گزینه‌های پاسخ هر سوال"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices', verbose_name="سوال")
    text = models.CharField(max_length=100, verbose_name="متن گزینه")

    class Meta:
        verbose_name = "گزینه پاسخ"
        verbose_name_plural = "گزینه‌های پاسخ"
    def __str__(self):
        return self.text

class CallAnswer(models.Model):
    """مدل واسط برای پاسخ‌های تماس به سوالات"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='answers', verbose_name="تماس")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="سوال")
    selected_choice = models.ForeignKey(AnswerChoice, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="گزینه انتخاب‌شده")

    class Meta:
        unique_together = ('call', 'question')  # Prevent duplicate answers per call-question pair
        verbose_name = "پاسخ تماس"
        verbose_name_plural = "پاسخ‌های تماس"

    def __str__(self):
        return f"{self.call} - {self.question.text}"

class Ticket(models.Model):
    user =  models.ForeignKey(CustomUser,related_name="tickets",on_delete=models.CASCADE,verbose_name='سازنده')
    title = models.CharField(max_length=32,verbose_name="عنوان")
    description = models.TextField(verbose_name="متن")
    done = models.BooleanField(default=False,verbose_name="انجام شده ")
    created_at = models.DateField(auto_now=True,verbose_name="ساخته شده")
    class Meta:
        verbose_name = 'تیکت'
        verbose_name_plural = "تیکت ها "
        ordering = ['-created_at']
    def __str__(self):
        return self.title
