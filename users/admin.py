from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""

    list_display = ('username', 'email', 'full_name', 'is_admin', 'is_active', 'created_at', 'last_login')
    list_filter = ('is_admin', 'is_active', 'created_at', 'last_login')
    search_fields = ('username', 'email', 'full_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_login')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email', 'full_name')}),
        (_('Permissions'),
         {'fields': ('is_active', 'is_admin', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('created_at', 'updated_at', 'last_login')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'password1', 'password2', 'is_admin', 'is_staff', 'is_active'),
        }),
    )

    # Custom save_model to ensure password is hashed properly
    def save_model(self, request, obj, form, change):
        if not change:
            # Only set password for new users to avoid re-hashing the password
            obj.set_password(form.cleaned_data.get('password'))
        super().save_model(request, obj, form, change)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for AuditLog model."""

    list_display = ('user', 'action', 'occurred_at', 'ip_address')
    list_filter = ('action', 'occurred_at')
    search_fields = ('user__username', 'action', 'ip_address')
    ordering = ('-occurred_at',)
    readonly_fields = ('user', 'action', 'action_details', 'occurred_at', 'ip_address')

    def has_add_permission(self, request):
        # Prevent manual creation of audit logs
        return False

    def has_change_permission(self, request, obj=None):
        # Prevent editing of audit logs
        return False