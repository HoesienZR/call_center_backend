from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

# Register your models here.


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Display the custom user model in the admin panel.
    Additional fields (phone_number, can_create_projects) have been added.
    """

    # Fields displayed in the user edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {'fields': ('phone_number', 'can_create_projects')}),
    )

    # Fields displayed when creating a new user
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Information', {'fields': ('phone_number', 'can_create_projects')}),
    )

    # Fields shown in the user list
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'phone_number', 'can_create_projects'
    )

    # Fields that can be used for searching
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
