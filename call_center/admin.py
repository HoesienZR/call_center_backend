# call_center/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser,
    Project,
    ProjectMembership,
    Contact,
    Call,
    AnswerChoice,
    Question, CallAnswer,Ticket

)
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['title','created_at','user',]
    list_filter = ['done']
    search_fields = ['title','description']

# 1. سفارشی‌سازی پنل ادمین برای مدل CustomUser
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    نمایش مدل کاربر سفارشی در پنل ادمین.
    فیلدهای جدید (phone_number, can_create_projects) به آن اضافه شده است.
    """
    # فیلدهایی که در فرم ویرایش کاربر نمایش داده می‌شوند
    fieldsets = UserAdmin.fieldsets + (
        ('اطلاعات تکمیلی', {'fields': ('phone_number', 'can_create_projects')}),
    )
    # فیلدهایی که هنگام ساخت کاربر جدید نمایش داده می‌شوند
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('اطلاعات تکمیلی', {'fields': ('phone_number', 'can_create_projects')}),
    )
    # فیلدهایی که در لیست کاربران نمایش داده می‌شوند
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'phone_number', 'can_create_projects')
    # فیلدهایی که می‌توان بر اساس آن‌ها جستجو کرد
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')


# 2. نمایش اعضای پروژه به صورت درون‌خطی (Inline) در صفحه پروژه
class ProjectMembershipInline(admin.TabularInline):
    """
    امکان افزودن و ویرایش اعضای پروژه به صورت مستقیم در صفحه همان پروژه.
    """
    model = ProjectMembership
    extra = 1  # نمایش یک فرم خالی برای افزودن عضو جدید
    autocomplete_fields = ['user'] # برای جستجوی سریع کاربران


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل پروژه.
    """
    list_display = ('name',"id", 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description')
    autocomplete_fields = ['created_by']
    inlines = [ProjectMembershipInline] # اضافه کردن اعضا به صورت درون‌خطی

@admin.register(CallAnswer)
class CallAnswerAdmin(admin.ModelAdmin):
    list_display = ['call','question','selected_choice']

@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل عضویت در پروژه.
    """
    list_display = ('project', 'user', 'role', 'assigned_at')
    list_filter = ('role', 'project')
    search_fields = ('project__name', 'user__username')
    autocomplete_fields = ['project', 'user']

@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ['question',"text"]

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["text"]



@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل مخاطب.
    """
    list_display = ('full_name', 'phone', 'project', 'call_status', 'assigned_caller', 'assigned_caller_phone' ,'last_call_date',"birth_date","gender")
    list_filter = ('project', 'call_status', 'is_active')
    search_fields = ('full_name', 'phone', 'email', 'project__name')
    # برای بهبود عملکرد، فیلدهای سنگین را در لیست نمایش ندهید
    # raw_id_fields = ('membership',)

    @admin.display(description="شماره تماس‌گیرنده تخصیص داده‌شده")
    def assigned_caller_phone(self, obj):
        """نمایش شماره تلفن تماس‌گیرنده تخصیص داده‌شده"""
        if obj.assigned_caller and hasattr(obj.assigned_caller, "phone_number"):
            return obj.assigned_caller.phone_number
        return "-"

@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    """
    تنظیمات پنل ادمین برای مدل تماس.
    """
    list_display = ('contact', 'caller', 'project', 'call_date', 'call_result', 'status', 'duration','created_at')
    list_filter = ('project', 'call_result', 'status', 'call_date')
    search_fields = ('contact__full_name', 'caller__username', 'notes')
    autocomplete_fields = ['contact', 'caller', 'project']
    readonly_fields = ( 'edited_at', 'edited_by',)




