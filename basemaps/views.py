# basemaps/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
import base64

from .models import Basemap, ProjectBasemap
from .serializers import (
    BasemapSerializer,
    BasemapDetailSerializer,
    ProjectBasemapSerializer
)
from users.views import create_audit_log


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit, but allow authenticated users to read.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions are only allowed to admin users
        return request.user and (request.user.is_admin or request.user.is_staff)


class BasemapViewSet(viewsets.ModelViewSet):
    """ViewSet for managing basemaps."""

    queryset = Basemap.objects.all()
    serializer_class = BasemapSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'provider']
    ordering_fields = ['name', 'provider', 'created_at']

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'retrieve':
            return BasemapDetailSerializer
        return BasemapSerializer

    def get_queryset(self):
        """Filter basemaps based on query parameters."""
        queryset = Basemap.objects.all()

        # Filter by provider
        provider = self.request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider=provider)

        # Filter by system/custom
        is_system = self.request.query_params.get('is_system')
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a basemap with audit logging."""
        with transaction.atomic():
            basemap = serializer.save()
            create_audit_log(
                user= self.request.user,
                action= 'Basemap created',
                details={'basemap_id': basemap.id, 'name': basemap.name},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a basemap with audit logging."""
        with transaction.atomic():
            basemap = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Basemap updated',
                details={'basemap_id': basemap.id, 'name': basemap.name},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a basemap with audit logging."""
        basemap_id = instance.id
        basemap_name = instance.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Basemap deleted',
                details={'basemap_id': basemap_id, 'name': basemap_name},
                request=self.request
            )

    @action(detail=True, methods=['post'])
    def upload_preview(self, request, pk=None):
        """Upload a preview image for a basemap."""
        try:
            basemap = self.get_object()

            # Extract data from request
            preview_data = request.data.get('preview_image', '')

            if not preview_data:
                return Response(
                    {'error': 'Preview image data is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Convert base64 to binary
            if 'base64,' in preview_data:
                # Extract the actual base64 data
                preview_data = preview_data.split('base64,')[1]

            preview_binary = base64.b64decode(preview_data)

            # Update basemap
            basemap.preview_image = preview_binary
            basemap.save()

            # Create audit log
            create_audit_log(
                user=request.user,
                action='Basemap preview uploaded',
                details={'basemap_id': basemap.id, 'name': basemap.name},
                request=request
            )

            return Response(
                BasemapSerializer(basemap).data,
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Generate preview HTML for the basemap."""
        basemap = self.get_object()

        # Generate preview HTML with Leaflet
        preview_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Basemap Preview</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <style>
                html, body {{ height: 100%; margin: 0; padding: 0; }}
                #map {{ height: 100%; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <script>
                var map = L.map('map').setView([0, 0], 2);

                L.tileLayer('{basemap.url_template or "https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png"}', {{
                    attribution: '{basemap.attribution or "© OpenStreetMap contributors"}'
                }}).addTo(map);
            </script>
        </body>
        </html>
        """

        return Response({
            'preview_html': preview_html,
            'name': basemap.name,
            'provider': basemap.provider
        })

    @action(detail=True, methods=['get'])
    def test_connection(self, request, pk=None):
        """Test if the basemap is accessible."""
        basemap = self.get_object()

        # For demo, return simulated success
        return Response({
            'message': 'Basemap connection test successful',
            'simulated': True,
            'basemap_id': basemap.id,
            'url_tested': basemap.url_template or "https://tile.openstreetmap.org/0/0/0.png"
        })

class ProjectBasemapViewSet(viewsets.ModelViewSet):
    """ViewSet for managing project basemap associations."""

    queryset = ProjectBasemap.objects.all()
    serializer_class = ProjectBasemapSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        """Filter project basemaps based on query parameters."""
        queryset = ProjectBasemap.objects.all()

        # Filter by project
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Filter by basemap
        basemap_id = self.request.query_params.get('basemap_id')
        if basemap_id:
            queryset = queryset.filter(basemap_id=basemap_id)

        return queryset

    def perform_create(self, serializer):
        """Create a project basemap with audit logging."""
        with transaction.atomic():
            project_basemap = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Project basemap created',
                details={
                    'project_basemap_id': project_basemap.id,
                    'project_id': project_basemap.project.id,
                    'project_name': project_basemap.project.name,
                    'basemap_id': project_basemap.basemap.id,
                    'basemap_name': project_basemap.basemap.name
                },
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a project basemap with audit logging."""
        with transaction.atomic():
            project_basemap = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Project basemap updated',
                details={
                    'project_basemap_id': project_basemap.id,
                    'project_id': project_basemap.project.id,
                    'project_name': project_basemap.project.name,
                    'basemap_id': project_basemap.basemap.id,
                    'basemap_name': project_basemap.basemap.name
                },
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a project basemap with audit logging."""
        project_basemap_id = instance.id
        project_id = instance.project.id
        project_name = instance.project.name
        basemap_id = instance.basemap.id
        basemap_name = instance.basemap.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Project basemap deleted',
                details={
                    'project_basemap_id': project_basemap_id,
                    'project_id': project_id,
                    'project_name': project_name,
                    'basemap_id': basemap_id,
                    'basemap_name': basemap_name
                },
                request=self.request
            )

    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """Batch update multiple project basemaps."""
        project_id = request.data.get('project_id')
        basemaps = request.data.get('basemaps', [])

        if not project_id or not basemaps:
            return Response(
                {'error': 'Project ID and basemaps are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Get existing project basemaps
                existing = ProjectBasemap.objects.filter(project_id=project_id)
                existing_ids = set(pb.basemap_id for pb in existing)

                # Track processed basemaps
                processed_ids = set()

                # Process each basemap
                for item in basemaps:
                    basemap_id = item.get('basemap_id')
                    is_default = item.get('is_default', False)
                    display_order = item.get('display_order', 0)
                    custom_options = item.get('custom_options', {})

                    if not basemap_id:
                        continue

                    processed_ids.add(basemap_id)

                    # Update or create
                    if basemap_id in existing_ids:
                        pb = existing.get(basemap_id=basemap_id)
                        pb.is_default = is_default
                        pb.display_order = display_order
                        pb.custom_options = custom_options
                        pb.save()
                    else:
                        ProjectBasemap.objects.create(
                            project_id=project_id,
                            basemap_id=basemap_id,
                            is_default=is_default,
                            display_order=display_order,
                            custom_options=custom_options
                        )

                # Delete any basemaps not in the update
                to_delete = existing_ids - processed_ids
                if to_delete:
                    existing.filter(basemap_id__in=to_delete).delete()

                # Create audit log
                create_audit_log(
                    user=request.user,
                    action='Project basemaps batch updated',
                    details={
                        'project_id': project_id,
                        'updated_count': len(processed_ids),
                        'removed_count': len(to_delete)
                    },
                    request=request
                )

                # Return updated list
                updated = ProjectBasemap.objects.filter(project_id=project_id)
                serializer = self.get_serializer(updated, many=True)
                return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )