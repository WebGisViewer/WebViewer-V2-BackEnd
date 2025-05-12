from django.contrib.auth.models import AnonymousUser
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from django.db import transaction

from .models import AuditLog
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    AuditLogSerializer
)

User = get_user_model()


def create_audit_log(user, action, details=None, request=None):
    """Helper function to create audit logs."""
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

    AuditLog.objects.create(
        user=user,
        action=action,
        action_details=details,
        ip_address=ip
    )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view with audit logging."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # If login was successful, update last_login and create audit log
            username = request.data.get('username')
            user = User.objects.get(username=username)
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            create_audit_log(
                user=user,
                action='User logged in',
                request=request
            )

        return response


class LogoutView(APIView):
    """View for user logout."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()

            create_audit_log(
                user=request.user,
                action='User logged out',
                request=request
            )

            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management."""

    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        """Set custom permissions for different actions."""
        if self.action == 'create':
            # Only admins can create users
            permission_classes = [permissions.IsAdminUser]
        else:
            # Admin users can access all users, others can only access themselves
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Restrict regular users to see only themselves."""
        user = self.request.user
        print('User:', user)
        if user == AnonymousUser:
            return User.objects.none()
        if user.is_staff or user.is_admin:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    def perform_create(self, serializer):
        """Create a new user with audit logging."""
        with transaction.atomic():
            user = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='User created',
                details={'created_user_id': user.id, 'username': user.username},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a user with audit logging."""
        with transaction.atomic():
            user = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='User updated',
                details={'updated_user_id': user.id, 'username': user.username},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a user with audit logging."""
        username = instance.username
        user_id = instance.id

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='User deleted',
                details={'deleted_user_id': user_id, 'username': username},
                request=self.request
            )

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password."""
        user = self.get_object()

        # If not user or admin trying to change password
        if not (request.user.id == user.id or request.user.is_admin):
            return Response(
                {"detail": "You do not have permission to change this user's password."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            # Check old password (if admin, don't verify old password)
            if not request.user.is_admin and not check_password(serializer.data.get("old_password"), user.password):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            user.set_password(serializer.data.get("new_password"))
            user.save()

            create_audit_log(
                user=request.user,
                action='Password changed',
                details={'target_user_id': user.id},
                request=request
            )

            return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return the authenticated user's details."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def activity(self, request, pk=None):
        """Get user activity history."""
        user = self.get_object()

        # Get user's audit logs
        logs = AuditLog.objects.filter(user=user).order_by('-occurred_at')[:100]
        serializer = AuditLogSerializer(logs, many=True)

        return Response(serializer.data)

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for audit logs."""

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Filter audit logs based on query parameters."""
        queryset = AuditLog.objects.all()

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action__icontains=action)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(occurred_at__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(occurred_at__lte=end_date)

        return queryset.order_by('-occurred_at')


class HealthCheckView(APIView):
    """Health check endpoint."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "healthy"}, status=status.HTTP_200_OK)