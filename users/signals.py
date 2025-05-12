from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()


# users/signals.py
@receiver(post_save, sender=User)
def create_user_audit_log(sender, instance, created, **kwargs):
    """Create an audit log when a user is created or updated (outside of view)."""
    # Skip if being created through view (the view handles its own audit logs)
    if hasattr(instance, '_from_view'):
        return

    # Skip updates to last_login since it's already logged in the login view
    update_fields = kwargs.get('update_fields')
    if not created and update_fields is not None and 'last_login' in update_fields:
        return

    action = 'User created' if created else 'User updated (system)'
    details = {'user_id': instance.id, 'username': instance.username}

    # Create audit log with system action
    AuditLog.objects.create(
        user=None,  # System action
        action=action,
        action_details=details
    )


@receiver(post_delete, sender=User)
def delete_user_audit_log(sender, instance, **kwargs):
    """Create an audit log when a user is deleted (outside of view)."""
    # Skip if being deleted through view (the view handles its own audit logs)
    if hasattr(instance, '_from_view'):
        return

    # Create audit log for system deletion
    AuditLog.objects.create(
        user=None,  # System action
        action='User deleted (system)',
        action_details={'user_id': instance.id, 'username': instance.username}
    )