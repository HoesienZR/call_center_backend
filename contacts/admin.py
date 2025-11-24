from django.contrib import admin
from .models import Contact, ContactLog


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the Contact model.
    """

    list_display = (
        'full_name', 'phone', 'project', 'call_status', 'assigned_caller',
        'assigned_caller_phone', 'last_call_date', 'birth_date', 'gender'
    )
    list_filter = ('project', 'call_status', 'is_active')
    search_fields = ('full_name', 'phone', 'email', 'project__name')

    @admin.display(description="Assigned Caller Phone Number")
    def assigned_caller_phone(self, obj):
        """
        Display the phone number of the assigned caller.
        """
        if obj.assigned_caller and hasattr(obj.assigned_caller, "phone_number"):
            return obj.assigned_caller.phone_number
        return "-"

    list_display_links = ('full_name',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset


@admin.register(ContactLog)
class ContactLogAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the ContactLog model.
    """
    list_display = ('contact', 'action', 'performed_by', 'timestamp')
    readonly_fields = [field.name for field in ContactLog._meta.fields]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset
