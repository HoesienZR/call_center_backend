from django.contrib.auth.models import Group, Permission, User
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from .models import UserProfile

@receiver(post_migrate)
def create_groups(sender, **kwargs):
    # ایجاد گروه تماس‌گیرنده
    caller_group, created = Group.objects.get_or_create(name='Caller')
    if created or not caller_group.permissions.exists():
        permissions = []
        for codename in ['view_project', 'add_call', 'change_call', 'view_contact', 'manage_project']:
            try:
                permission = Permission.objects.get(
                    codename=codename,
                    content_type__app_label='call_center'
                )
                permissions.append(permission)
            except Permission.DoesNotExist:
                print(f"Warning: Permission with codename '{codename}' does not exist for app 'call_center'.")
        caller_group.permissions.set(permissions)

    # ایجاد گروه کاربر معمولی
    regular_user_group, created = Group.objects.get_or_create(name='Regular User')
    if created or not regular_user_group.permissions.exists():
        permissions = []
        for codename in ['view_project', 'view_contact']:
            try:
                permission = Permission.objects.get(
                    codename=codename,
                    content_type__app_label='call_center'
                )
                permissions.append(permission)
            except Permission.DoesNotExist:
                print(f"Warning: Permission with codename '{codename}' does not exist for app 'call_center'.")
        regular_user_group.permissions.set(permissions)

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        try:
            instance.profile.save()
        except ObjectDoesNotExist:
            UserProfile.objects.create(user=instance)