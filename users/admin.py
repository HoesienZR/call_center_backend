from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from .models import CustomUser


# ----------------------------
# Custom User Creation Form
# ----------------------------
class CustomUserCreationForm(forms.ModelForm):
    """
    Form shown when creating a new user in the admin panel.
    """

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ("phone_number", "can_create_projects")

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# ----------------------------
# Custom User Change Form
# ----------------------------
class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            "phone_number",
            "can_create_projects",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )


# ----------------------------
# Custom UserAdmin
# ----------------------------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin panel for phone-number-based user model without username.
    """

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = (
        "phone_number",
        "can_create_projects",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = ("phone_number",)
    ordering = ("phone_number",)

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Extra", {"fields": ("can_create_projects",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "password1",
                    "password2",
                    "can_create_projects",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
