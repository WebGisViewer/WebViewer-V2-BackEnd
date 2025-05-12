# clients/admin.py
from django.contrib import admin
from .models import Client, ClientProject


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Admin configuration for Client model."""

    list_display = ('name', 'contact_email', 'contact_phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_email')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('name', 'is_active')}),
        ('Contact Information', {'fields': ('contact_email', 'contact_phone')}),
        ('Important dates', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(ClientProject)
class ClientProjectAdmin(admin.ModelAdmin):
    """Admin configuration for ClientProject model."""

    list_display = ('client', 'project', 'is_active', 'created_at', 'expires_at', 'last_accessed')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('client__name', 'project__name', 'unique_link')
    ordering = ('client__name', 'project__name')
    readonly_fields = ('created_at', 'last_accessed')

    fieldsets = (
        (None, {'fields': ('client', 'project', 'is_active')}),
        ('Access', {'fields': ('unique_link', 'expires_at')}),
        ('Important dates', {'fields': ('created_at', 'last_accessed')}),
    )