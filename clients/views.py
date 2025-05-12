# clients/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from users.models import AuditLog
from .models import Client, ClientProject
from .serializers import (
    ClientSerializer,
    ClientDetailSerializer,
    ClientUserSerializer,
    ClientProjectSerializer
)
from users.views import create_audit_log


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit, but allow all authenticated users to read.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions are only allowed to admin users
        return request.user and request.user.is_admin


class ClientViewSet(viewsets.ModelViewSet):
    """ViewSet for client management."""

    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'retrieve' or self.action == 'list':
            return ClientDetailSerializer
        return ClientSerializer

    def perform_create(self, serializer):
        """Create a new client with audit logging."""
        with transaction.atomic():
            client = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Client created',
                details={'client_id': client.id, 'client_name': client.name},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a client with audit logging."""
        with transaction.atomic():
            client = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Client updated',
                details={'client_id': client.id, 'client_name': client.name},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a client with audit logging."""
        client_id = instance.id
        client_name = instance.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Client deleted',
                details={'client_id': client_id, 'client_name': client_name},
                request=self.request
            )

    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Return the users associated with this client."""
        client = self.get_object()
        users = client.users.all()
        serializer = ClientUserSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def projects(self, request, pk=None):
        """Return the projects associated with this client."""
        client = self.get_object()
        projects = client.client_projects.all()
        serializer = ClientProjectSerializer(projects, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get client usage analytics."""
        client = self.get_object()

        # Get basic stats
        projects = client.client_projects.all()
        users = client.users.all()

        # Get recent activity
        user_ids = users.values_list('id', flat=True)
        recent_activity = AuditLog.objects.filter(
            user_id__in=user_ids
        ).order_by('-occurred_at')[:50]

        analytics = {
            'project_count': projects.count(),
            'active_projects': projects.filter(is_active=True).count(),
            'user_count': users.count(),
            'active_users': users.filter(is_active=True).count(),
            'most_accessed_projects': [
                {
                    'id': cp.project.id,
                    'name': cp.project.name,
                    'last_accessed': cp.last_accessed
                }
                for cp in projects.order_by('-last_accessed')[:5]
            ],
            'recent_activity': AuditLogSerializer(recent_activity, many=True).data
        }

        return Response(analytics)

class ClientProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for client project management."""

    queryset = ClientProject.objects.all()
    serializer_class = ClientProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        """Filter projects based on query parameters."""
        queryset = ClientProject.objects.all()

        # Filter by client
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(client_id=client_id)

        # Filter by project
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a new client project with audit logging."""
        with transaction.atomic():
            client_project = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Client project created',
                details={
                    'client_project_id': client_project.id,
                    'client_id': client_project.client.id,
                    'client_name': client_project.client.name,
                    'project_id': client_project.project.id,
                    'project_name': client_project.project.name
                },
                request=self.request
            )

    @action(detail=True, methods=['post'])
    def record_access(self, request, pk=None):
        """Record that a client accessed this project."""
        client_project = self.get_object()
        client_project.last_accessed = timezone.now()
        client_project.save(update_fields=['last_accessed'])

        create_audit_log(
            user=request.user,
            action='Client accessed project',
            details={
                'client_project_id': client_project.id,
                'client_id': client_project.client.id,
                'client_name': client_project.client.name,
                'project_id': client_project.project.id
            },
            request=request
        )

        return Response({'status': 'access recorded'})

    @action(detail=False, methods=['post'])
    def batch_assign(self, request):
        """Batch assign projects to clients."""
        assignments = request.data.get('assignments', [])
        client_id = request.data.get('client_id')

        if not client_id or not assignments:
            return Response({'error': 'Client ID and assignments are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        results = []
        with transaction.atomic():
            for project_id in assignments:
                # Check if assignment already exists
                existing = ClientProject.objects.filter(
                    client_id=client_id, project_id=project_id
                ).first()

                if not existing:
                    # Create unique link
                    import uuid
                    unique_link = f"client-{client_id}-project-{project_id}-{uuid.uuid4().hex[:8]}"

                    # Create assignment
                    assignment = ClientProject.objects.create(
                        client_id=client_id,
                        project_id=project_id,
                        unique_link=unique_link,
                        is_active=True
                    )

                    results.append({
                        'project_id': project_id,
                        'status': 'created',
                        'unique_link': unique_link
                    })
                else:
                    results.append({
                        'project_id': project_id,
                        'status': 'already_exists'
                    })

        create_audit_log(
            user=request.user,
            action='Batch project assignment',
            details={'client_id': client_id, 'count': len(results)},
            request=request
        )

        return Response({'results': results})