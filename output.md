├── basemaps/
│   ├── views.py
│   └── serializers.py
├── clients/
│   ├── views.py
│   └── serializers.py
├── functions/
│   ├── views.py
│   └── serializers.py
├── layers/
│   ├── views.py
│   └── serializers.py
├── projects/
│   ├── views.py
│   └── serializers.py
├── styling/
│   ├── views.py
│   └── serializers.py
└── users/
    ├── views.py
    └── serializers.py

# File: basemaps\views.py
```python
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
                user=self.request.user,
                action='Basemap created',
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
```
# End of file: basemaps\views.py

# File: clients\views.py
```python
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
```
# End of file: clients\views.py

# File: functions\views.py
```python
# functions/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from layers.models import ProjectLayer
from .models import LayerFunction, ProjectLayerFunction, MapTool, ProjectTool
from .serializers import (
    LayerFunctionSerializer,
    LayerFunctionDetailSerializer,
    ProjectLayerFunctionSerializer,
    MapToolSerializer,
    MapToolDetailSerializer,
    ProjectToolSerializer
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


class LayerFunctionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing layer functions."""

    queryset = LayerFunction.objects.all()
    serializer_class = LayerFunctionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'function_type']
    ordering_fields = ['name', 'function_type', 'created_at']

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'retrieve' or self.action == 'code':
            return LayerFunctionDetailSerializer
        return LayerFunctionSerializer

    def get_queryset(self):
        """Filter functions based on query parameters."""
        queryset = LayerFunction.objects.all()

        # Filter by function type
        function_type = self.request.query_params.get('function_type')
        if function_type:
            queryset = queryset.filter(function_type=function_type)

        # Filter by system/custom
        is_system = self.request.query_params.get('is_system')
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a function with audit logging."""
        with transaction.atomic():
            function = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Layer function created',
                details={'function_id': function.id, 'name': function.name},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a function with audit logging."""
        with transaction.atomic():
            function = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Layer function updated',
                details={'function_id': function.id, 'name': function.name},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a function with audit logging."""
        function_id = instance.id
        function_name = instance.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Layer function deleted',
                details={'function_id': function_id, 'name': function_name},
                request=self.request
            )

    @action(detail=True, methods=['get'])
    def code(self, request, pk=None):
        """Return the function code."""
        function = self.get_object()
        serializer = self.get_serializer(function)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute the function on a layer."""
        function = self.get_object()

        layer_id = request.data.get('layer_id')
        if not layer_id:
            return Response({'error': 'Layer ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            layer = ProjectLayer.objects.get(id=layer_id)

            # Execute based on function type
            if function.function_type == 'clustering':
                result = self._execute_clustering(function, layer, request.data)
            elif function.function_type == 'styling':
                result = self._execute_styling(function, layer, request.data)
            elif function.function_type == 'analysis':
                result = self._execute_analysis(function, layer, request.data)
            else:
                return Response({'error': f'Unsupported function type: {function.function_type}'},
                                status=status.HTTP_400_BAD_REQUEST)

            # Create audit log
            create_audit_log(
                user=request.user,
                action=f'Function executed: {function.name}',
                details={'function_id': function.id, 'layer_id': layer.id},
                request=request
            )

            return Response(result)

        except ProjectLayer.DoesNotExist:
            return Response({'error': 'Layer not found'}, status=status.HTTP_404_NOT_FOUND)

    def _execute_clustering(self, function, layer, data):
        """Execute clustering function."""
        # Get parameters
        radius = data.get('radius', 80)

        # Update layer clustering options
        layer.enable_clustering = True
        layer.clustering_options = {
            'radius': radius,
            'maxZoom': 18,
            'minPoints': 2
        }
        layer.save()

        return {
            'message': 'Clustering enabled',
            'settings': layer.clustering_options
        }

    def _execute_styling(self, function, layer, data):
        """Execute styling function."""
        # For demo, just return success
        return {
            'message': 'Styling function executed',
            'simulated': True
        }

    def _execute_analysis(self, function, layer, data):
        """Execute analysis function."""
        # Count features for demo
        feature_count = layer.features.count()

        return {
            'message': 'Analysis function executed',
            'feature_count': feature_count
        }

class ProjectLayerFunctionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing project layer functions."""

    queryset = ProjectLayerFunction.objects.all()
    serializer_class = ProjectLayerFunctionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        """Filter project layer functions based on query parameters."""
        queryset = ProjectLayerFunction.objects.all()

        # Filter by project layer
        layer_id = self.request.query_params.get('layer_id')
        if layer_id:
            queryset = queryset.filter(project_layer_id=layer_id)

        # Filter by function
        function_id = self.request.query_params.get('function_id')
        if function_id:
            queryset = queryset.filter(layer_function_id=function_id)

        # Filter by enabled status
        enabled = self.request.query_params.get('enabled')
        if enabled is not None:
            queryset = queryset.filter(enabled=enabled.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a project layer function with audit logging."""
        with transaction.atomic():
            plf = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Project layer function created',
                details={
                    'project_layer_function_id': plf.id,
                    'project_layer_id': plf.project_layer.id,
                    'layer_name': plf.project_layer.name,
                    'function_id': plf.layer_function.id,
                    'function_name': plf.layer_function.name
                },
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a project layer function with audit logging."""
        with transaction.atomic():
            plf = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Project layer function updated',
                details={
                    'project_layer_function_id': plf.id,
                    'project_layer_id': plf.project_layer.id,
                    'layer_name': plf.project_layer.name,
                    'function_id': plf.layer_function.id,
                    'function_name': plf.layer_function.name
                },
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a project layer function with audit logging."""
        plf_id = instance.id
        layer_id = instance.project_layer.id
        layer_name = instance.project_layer.name
        function_id = instance.layer_function.id
        function_name = instance.layer_function.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Project layer function deleted',
                details={
                    'project_layer_function_id': plf_id,
                    'project_layer_id': layer_id,
                    'layer_name': layer_name,
                    'function_id': function_id,
                    'function_name': function_name
                },
                request=self.request
            )


class MapToolViewSet(viewsets.ModelViewSet):
    """ViewSet for managing map tools."""

    queryset = MapTool.objects.all()
    serializer_class = MapToolSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'tool_type']
    ordering_fields = ['name', 'tool_type', 'created_at']

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'retrieve' or self.action == 'code':
            return MapToolDetailSerializer
        return MapToolSerializer

    def get_queryset(self):
        """Filter tools based on query parameters."""
        queryset = MapTool.objects.all()

        # Filter by tool type
        tool_type = self.request.query_params.get('tool_type')
        if tool_type:
            queryset = queryset.filter(tool_type=tool_type)

        # Filter by UI position
        ui_position = self.request.query_params.get('ui_position')
        if ui_position:
            queryset = queryset.filter(ui_position=ui_position)

        # Filter by system/custom
        is_system = self.request.query_params.get('is_system')
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a tool with audit logging."""
        with transaction.atomic():
            tool = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Map tool created',
                details={'tool_id': tool.id, 'name': tool.name},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a tool with audit logging."""
        with transaction.atomic():
            tool = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Map tool updated',
                details={'tool_id': tool.id, 'name': tool.name},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a tool with audit logging."""
        tool_id = instance.id
        tool_name = instance.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Map tool deleted',
                details={'tool_id': tool_id, 'name': tool_name},
                request=self.request
            )

    @action(detail=True, methods=['get'])
    def code(self, request, pk=None):
        """Return the tool code."""
        tool = self.get_object()
        serializer = self.get_serializer(tool)
        return Response(serializer.data)


class ProjectToolViewSet(viewsets.ModelViewSet):
    """ViewSet for managing project tools."""

    queryset = ProjectTool.objects.all()
    serializer_class = ProjectToolSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        """Filter project tools based on query parameters."""
        queryset = ProjectTool.objects.all()

        # Filter by project
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Filter by tool
        tool_id = self.request.query_params.get('tool_id')
        if tool_id:
            queryset = queryset.filter(tool_id=tool_id)

        # Filter by enabled status
        is_enabled = self.request.query_params.get('is_enabled')
        if is_enabled is not None:
            queryset = queryset.filter(is_enabled=is_enabled.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a project tool with audit logging."""
        with transaction.atomic():
            pt = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Project tool created',
                details={
                    'project_tool_id': pt.id,
                    'project_id': pt.project.id,
                    'project_name': pt.project.name,
                    'tool_id': pt.tool.id,
                    'tool_name': pt.tool.name
                },
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a project tool with audit logging."""
        with transaction.atomic():
            pt = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Project tool updated',
                details={
                    'project_tool_id': pt.id,
                    'project_id': pt.project.id,
                    'project_name': pt.project.name,
                    'tool_id': pt.tool.id,
                    'tool_name': pt.tool.name
                },
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a project tool with audit logging."""
        pt_id = instance.id
        project_id = instance.project.id
        project_name = instance.project.name
        tool_id = instance.tool.id
        tool_name = instance.tool.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Project tool deleted',
                details={
                    'project_tool_id': pt_id,
                    'project_id': project_id,
                    'project_name': project_name,
                    'tool_id': tool_id,
                    'tool_name': tool_name
                },
                request=self.request
            )

    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """Batch update multiple project tools."""
        project_id = request.data.get('project_id')
        tools = request.data.get('tools', [])

        if not project_id or not tools:
            return Response(
                {'error': 'Project ID and tools are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Get existing project tools
                existing = ProjectTool.objects.filter(project_id=project_id)
                existing_ids = set(pt.tool_id for pt in existing)

                # Track processed tools
                processed_ids = set()

                # Process each tool
                for item in tools:
                    tool_id = item.get('tool_id')
                    is_enabled = item.get('is_enabled', True)
                    display_order = item.get('display_order', 0)
                    tool_options = item.get('tool_options', {})
                    custom_position = item.get('custom_position')

                    if not tool_id:
                        continue

                    processed_ids.add(tool_id)

                    # Update or create
                    if tool_id in existing_ids:
                        pt = existing.get(tool_id=tool_id)
                        pt.is_enabled = is_enabled
                        pt.display_order = display_order
                        pt.tool_options = tool_options
                        pt.custom_position = custom_position
                        pt.save()
                    else:
                        ProjectTool.objects.create(
                            project_id=project_id,
                            tool_id=tool_id,
                            is_enabled=is_enabled,
                            display_order=display_order,
                            tool_options=tool_options,
                            custom_position=custom_position
                        )

                # Delete any tools not in the update
                to_delete = existing_ids - processed_ids
                if to_delete:
                    existing.filter(tool_id__in=to_delete).delete()

                # Create audit log
                create_audit_log(
                    user=request.user,
                    action='Project tools batch updated',
                    details={
                        'project_id': project_id,
                        'updated_count': len(processed_ids),
                        'removed_count': len(to_delete)
                    },
                    request=request
                )

                # Return updated list
                updated = ProjectTool.objects.filter(project_id=project_id)
                serializer = self.get_serializer(updated, many=True)
                return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
```
# End of file: functions\views.py

# File: layers\views.py
```python
# layers/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry
from django.utils import timezone
from django.core.files.storage import default_storage
import json
import os
from users.views import create_audit_log
from .models import LayerType, ProjectLayerGroup, ProjectLayer, ProjectLayerData, LayerPermission
from .serializers import (
    LayerTypeSerializer, ProjectLayerGroupSerializer, ProjectLayerSerializer,
    SimpleFeatureSerializer, FeatureSerializer, GeoJSONFeatureCollectionSerializer,
    LayerPermissionSerializer
)
from .file_utils import (
    get_crs_from_file, get_supported_crs_list, store_uploaded_file,
    detect_file_type, import_file_to_layer
)


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read access to authenticated users, but only allow write access to admin users.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and (request.user.is_admin or request.user.is_staff)

class LayerTypeViewSet(viewsets.ModelViewSet):
    """Viewset for layer types."""
    queryset = LayerType.objects.all()
    serializer_class = LayerTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['type_name', 'description']
    ordering_fields = ['type_name', 'created_at']

    def perform_create(self, serializer):
        """Create with audit logging."""
        with transaction.atomic():
            layer_type = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='LayerType created',
                details={'layer_type_id': layer_type.id, 'name': layer_type.type_name},
                request=self.request
            )

class ProjectLayerGroupViewSet(viewsets.ModelViewSet):
    """Viewset for layer groups."""
    queryset = ProjectLayerGroup.objects.all()
    serializer_class = ProjectLayerGroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'project__name']
    ordering_fields = ['name', 'display_order', 'project__name']

    def get_queryset(self):
        """Filter by project if specified."""
        queryset = ProjectLayerGroup.objects.all()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    def perform_create(self, serializer):
        """Create with audit logging."""
        with transaction.atomic():
            group = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='LayerGroup created',
                details={
                    'group_id': group.id,
                    'name': group.name,
                    'project_id': group.project_id
                },
                request=self.request
            )

class ProjectLayerViewSet(viewsets.ModelViewSet):
    """Viewset for project layers."""
    queryset = ProjectLayer.objects.all()
    serializer_class = ProjectLayerSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'project_layer_group__name', 'project_layer_group__project__name']
    ordering_fields = ['name', 'z_index', 'feature_count', 'created_at']

    def get_queryset(self):
        """Filter by project group or project."""
        queryset = ProjectLayer.objects.all()
        group_id = self.request.query_params.get('group_id')
        project_id = self.request.query_params.get('project_id')

        if group_id:
            queryset = queryset.filter(project_layer_group_id=group_id)
        elif project_id:
            queryset = queryset.filter(project_layer_group__project_id=project_id)

        return queryset

    def perform_create(self, serializer):
        """Create with audit logging."""
        with transaction.atomic():
            layer = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Layer created',
                details={
                    'layer_id': layer.id,
                    'name': layer.name,
                    'group_id': layer.project_layer_group_id,
                    'project_id': layer.project_layer_group.project_id
                },
                request=self.request
            )

    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        """Get layer data in GeoJSON format."""
        layer = self.get_object()

        # Support pagination parameters
        page = request.query_params.get('page')
        size = request.query_params.get('size', 1000)

        if page:
            # Paginated response as normal features
            start = (int(page) - 1) * int(size)
            end = start + int(size)
            features = layer.features.all()[start:end]
            serializer = SimpleFeatureSerializer(features, many=True)

            # Get total count for pagination
            total = layer.features.count()

            return Response({
                'count': total,
                'page': int(page),
                'size': int(size),
                'pages': (total + int(size) - 1) // int(size),
                'features': serializer.data
            })
        else:
            # Full GeoJSON response
            serializer = GeoJSONFeatureCollectionSerializer(layer)
            return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def import_geojson(self, request, pk=None):
        """Import features from GeoJSON."""
        layer = self.get_object()

        try:
            # Parse GeoJSON
            geojson_data = request.data

            # Validate it's a FeatureCollection
            if isinstance(geojson_data, str):
                geojson_data = json.loads(geojson_data)

            if geojson_data.get('type') != 'FeatureCollection':
                return Response(
                    {'error': 'Invalid GeoJSON: Not a FeatureCollection'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            features = geojson_data.get('features', [])

            # Process each feature
            created_count = 0
            with transaction.atomic():
                for feature in features:
                    try:
                        geometry = GEOSGeometry(json.dumps(feature.get('geometry')))
                        properties = feature.get('properties', {})
                        feature_id = feature.get('id') or properties.get('id')

                        # Create the feature
                        ProjectLayerData.objects.create(
                            project_layer=layer,
                            geometry=geometry,
                            properties=properties,
                            feature_id=feature_id
                        )
                        created_count += 1
                    except Exception as e:
                        return Response(
                            {'error': f'Error importing feature: {str(e)}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            # Update layer metadata
            layer.last_data_update = timezone.now()
            layer.update_feature_count()

            # Create audit log
            create_audit_log(
                user=request.user,
                action='GeoJSON imported',
                details={
                    'layer_id': layer.id,
                    'layer_name': layer.name,
                    'feature_count': created_count
                },
                request=request
            )

            return Response({
                'success': True,
                'features_imported': created_count,
                'total_features': layer.feature_count
            })

        except Exception as e:
            return Response(
                {'error': f'Error importing GeoJSON: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def clear_data(self, request, pk=None):
        """Remove all features from a layer."""
        layer = self.get_object()

        with transaction.atomic():
            count = layer.features.count()
            layer.features.all().delete()
            layer.last_data_update = timezone.now()
            layer.feature_count = 0
            layer.save()

            create_audit_log(
                user=request.user,
                action='Layer data cleared',
                details={
                    'layer_id': layer.id,
                    'layer_name': layer.name,
                    'features_removed': count
                },
                request=request
            )

        return Response({
            'success': True,
            'features_removed': count
        })

    @action(detail=True, methods=['post'])
    def upload_shapefile(self, request, pk=None):
        """Import features from a shapefile."""
        layer = self.get_object()

        if 'file' not in request.FILES:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        shapefile = request.FILES['file']

        # For demo purposes, we'll simulate success
        # In production, implement actual shapefile processing

        # Create audit log
        create_audit_log(
            user=request.user,
            action='Shapefile uploaded',
            details={'layer_id': layer.id, 'filename': shapefile.name},
            request=request
        )

        return Response({
            'message': 'Shapefile uploaded successfully',
            'simulated': True,
            'feature_count': 10  # Simulated count
        })

    @action(detail=True, methods=['post'])
    def buffer(self, request, pk=None):
        """Create buffer around features."""
        layer = self.get_object()

        distance = request.data.get('distance')
        if not distance:
            return Response({'error': 'Distance is required'}, status=status.HTTP_400_BAD_REQUEST)

        # For demo purposes, we'll simulate success
        # In production, implement actual buffer operation

        # Create audit log
        create_audit_log(
            user=request.user,
            action='Buffer operation',
            details={'layer_id': layer.id, 'distance': distance},
            request=request
        )

        return Response({
            'message': 'Buffer operation completed successfully',
            'simulated': True,
            'feature_count': 5  # Simulated count
        })

    @action(detail=True, methods=['get'])
    def export_geojson(self, request, pk=None):
        """Export layer data as GeoJSON."""
        layer = self.get_object()

        # Get layer features
        features_data = []
        for feature in layer.features.all():
            geojson_feature = {
                'type': 'Feature',
                'geometry': json.loads(feature.geometry.json),
                'properties': feature.properties
            }
            if feature.feature_id:
                geojson_feature['id'] = feature.feature_id
            features_data.append(geojson_feature)

        # Create GeoJSON
        geojson = {
            'type': 'FeatureCollection',
            'features': features_data
        }

        # Create audit log
        create_audit_log(
            user=request.user,
            action='GeoJSON export',
            details={'layer_id': layer.id},
            request=request
        )

        return Response(geojson)

class ProjectLayerDataViewSet(viewsets.ModelViewSet):
    """Viewset for individual layer features."""
    queryset = ProjectLayerData.objects.all()
    serializer_class = FeatureSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        """Filter by layer."""
        queryset = ProjectLayerData.objects.all()
        layer_id = self.request.query_params.get('layer_id')
        if layer_id:
            queryset = queryset.filter(project_layer_id=layer_id)
        return queryset

    def get_serializer_class(self):
        """Use the right serializer based on detail level."""
        if self.action == 'list':
            return SimpleFeatureSerializer
        return FeatureSerializer

    def perform_create(self, serializer):
        """Create with audit logging."""
        with transaction.atomic():
            feature = serializer.save()

            # Update layer metadata
            layer = feature.project_layer
            layer.last_data_update = timezone.now()
            layer.update_feature_count()

            create_audit_log(
                user=self.request.user,
                action='Feature created',
                details={
                    'feature_id': feature.feature_id,
                    'layer_id': feature.project_layer_id
                },
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete with audit logging."""
        layer = instance.project_layer
        feature_id = instance.feature_id

        with transaction.atomic():
            instance.delete()

            # Update layer metadata
            layer.last_data_update = timezone.now()
            layer.update_feature_count()

            create_audit_log(
                user=self.request.user,
                action='Feature deleted',
                details={
                    'feature_id': feature_id,
                    'layer_id': layer.id
                },
                request=self.request
            )

class LayerPermissionViewSet(viewsets.ModelViewSet):
    """Viewset for layer permissions."""
    queryset = LayerPermission.objects.all()
    serializer_class = LayerPermissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        """Filter by layer or client project."""
        queryset = LayerPermission.objects.all()
        layer_id = self.request.query_params.get('layer_id')
        client_project_id = self.request.query_params.get('client_project_id')

        if layer_id:
            queryset = queryset.filter(project_layer_id=layer_id)
        if client_project_id:
            queryset = queryset.filter(client_project_id=client_project_id)

        return queryset

class LayerDataView(APIView):
    """
    Provides layer data in chunks for frontend consumption.
    """
    permission_classes = [permissions.AllowAny]  # Allow unauthenticated access

    def get(self, request, layer_id):
        """
        Get layer data in chunks.
        """
        try:
            layer = ProjectLayer.objects.get(id=layer_id)

            # Check permissions for non-authenticated users
            if not request.user.is_authenticated and not layer.is_public:
                return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

            # Get chunk parameters
            chunk_id = request.query_params.get('chunk_id', 1)
            try:
                chunk_id = int(chunk_id)
            except ValueError:
                return Response({'error': 'Invalid chunk_id'}, status=status.HTTP_400_BAD_REQUEST)

            # Determine chunk size based on layer type
            chunk_size = self._get_chunk_size_for_layer(layer)

            # Calculate offsets
            start_idx = (chunk_id - 1) * chunk_size
            end_idx = start_idx + chunk_size

            # Get features for this chunk
            features = layer.features.all()[start_idx:end_idx]
            feature_count = features.count()

            # Build GeoJSON response
            feature_collection = {
                "type": "FeatureCollection",
                "features": [],
                "chunk_info": {
                    "chunk_id": chunk_id,
                    "features_count": feature_count,
                    "total_count": layer.features.count()
                }
            }

            # Add next chunk info if available
            total_chunks = (layer.features.count() + chunk_size - 1) // chunk_size
            if chunk_id < total_chunks:
                feature_collection["chunk_info"]["next_chunk"] = chunk_id + 1

            # Convert features to GeoJSON
            for feature in features:
                geojson_feature = {
                    "type": "Feature",
                    "geometry": json.loads(feature.geometry.json),
                    "properties": feature.properties,
                }

                if feature.feature_id:
                    geojson_feature["id"] = feature.feature_id

                feature_collection["features"].append(geojson_feature)

            # Log data access for larger chunks
            if feature_count > 100:
                log_user = request.user if request.user.is_authenticated else None
                create_audit_log(
                    user=log_user,
                    action='Layer data accessed',
                    details={
                        'layer_id': layer.id,
                        'layer_name': layer.name,
                        'chunk_id': chunk_id,
                        'feature_count': feature_count
                    },
                    request=request
                )

            return Response(feature_collection)

        except ProjectLayer.DoesNotExist:
            return Response({'error': 'Layer not found'}, status=status.HTTP_404_NOT_FOUND)

    def _get_chunk_size_for_layer(self, layer):
        """
        Determine appropriate chunk size based on layer type.
        """
        if not layer.layer_type:
            return 10000  # Default

        layer_type = layer.layer_type.type_name.lower()

        if layer_type in ['polygon', 'multipolygon']:
            return 500  # Smaller chunks for polygons
        elif layer_type in ['line', 'linestring', 'multilinestring']:
            return 2000  # Medium chunks for lines
        else:  # point, multipoint, or other
            return 10000  # Large chunks for points


class FileUploadView(APIView):
    """
    First step of file upload process: Upload and CRS check.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post']
    def post(self, request):
        """Upload a geospatial file and check its CRS."""
        # Check if file is present
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the file
        upload_file = request.FILES['file']

        # Detect file type from extension
        file_type = detect_file_type(upload_file)
        if not file_type:
            return Response(
                {'error': 'Unsupported file type. Supported types: .shp, .kml, .sqlite'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Store file in temporary location
            file_path, file_id = store_uploaded_file(upload_file, file_type)

            # Check if file has CRS
            has_crs, crs_code, crs_name = get_crs_from_file(file_path, file_type)

            # Get a list of common CRS options
            crs_options = get_supported_crs_list()

            # Create response
            response = {
                'file_id': file_id,
                'file_name': upload_file.name,
                'file_type': file_type,
                'file_size': upload_file.size,
                'has_crs': has_crs,
                'crs_detected': crs_code,
                'crs_name': crs_name,
                'crs_options': crs_options,
                'next_steps': 'complete_upload'
            }

            # Create audit log
            create_audit_log(
                user=request.user,
                action='File uploaded',
                details={
                    'file_name': upload_file.name,
                    'file_type': file_type,
                    'file_size': upload_file.size,
                    'has_crs': has_crs,
                    'crs_detected': crs_code
                },
                request=request
            )

            return Response(response)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompleteUploadView(APIView):
    """
    Second step of file upload process: Complete upload with metadata.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Complete the file upload and import to a layer."""
        # Check required fields
        required_fields = ['file_id', 'file_type', 'group_id', 'layer_name']
        missing_fields = [field for field in required_fields if field not in request.data]

        if missing_fields:
            return Response(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_id = request.data.get('file_id')
        file_type = request.data.get('file_type')
        group_id = request.data.get('group_id')
        layer_name = request.data.get('layer_name')
        layer_type_id = request.data.get('layer_type_id')
        source_crs = request.data.get('source_crs')
        target_crs = request.data.get('target_crs', 'EPSG:4326')
        description = request.data.get('description', '')
        is_visible = request.data.get('is_visible', True)
        is_public = request.data.get('is_public', False)

        # Get upload directory and construct file path
        upload_dir = getattr(settings, 'TEMP_UPLOAD_DIR', 'temp_uploads')
        file_path = os.path.join(upload_dir, f"{file_id}.{file_type}")

        # Verify file exists
        if not default_storage.exists(file_path):
            return Response(
                {'error': 'File not found. It may have expired.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # Get full path
            file_path = default_storage.path(file_path)

            # Get project layer group
            try:
                group = ProjectLayerGroup.objects.get(id=group_id)
            except ProjectLayerGroup.DoesNotExist:
                return Response(
                    {'error': 'Layer group not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get layer type
            layer_type = None
            if layer_type_id:
                try:
                    layer_type = LayerType.objects.get(id=layer_type_id)
                except LayerType.DoesNotExist:
                    return Response(
                        {'error': 'Layer type not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Create layer
            layer = ProjectLayer.objects.create(
                project_layer_group=group,
                layer_type=layer_type,
                name=layer_name,
                description=description,
                is_visible_by_default=is_visible,
                is_public=is_public,
                upload_file_type=file_type,
                upload_file_name=request.data.get('file_name', ''),
                original_crs=source_crs,
                target_crs=target_crs,
                upload_status='importing'
            )

            # Import the file
            success, feature_count, error = import_file_to_layer(
                layer, file_path, file_type, source_crs, target_crs
            )

            if not success:
                return Response(
                    {'error': error},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Create audit log
            create_audit_log(
                user=request.user,
                action='Layer created from file',
                details={
                    'layer_id': layer.id,
                    'layer_name': layer.name,
                    'file_type': file_type,
                    'feature_count': feature_count,
                    'group_id': group_id,
                    'project_id': group.project.id
                },
                request=request
            )

            # Clean up the temporary file
            default_storage.delete(file_path)

            return Response({
                'success': True,
                'layer_id': layer.id,
                'layer_name': layer.name,
                'feature_count': feature_count,
                'message': f'Successfully imported {feature_count} features'
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```
# End of file: layers\views.py

# File: projects\views.py
```python
# projects/views.py
# In projects/views.py
from rest_framework.views import APIView
from django.utils import timezone
from clients.models import ClientProject
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q

from layers.models import ProjectLayer, ProjectLayerGroup
from .models import Project
from .serializers import ProjectSerializer, ProjectCreateUpdateSerializer
from users.views import create_audit_log


class IsAdminOrReadOnly(permissions.BasePermission):
    """Permission to only allow admins to create/edit projects or project owners."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions only for admin users
        return request.user and (request.user.is_admin or request.user.is_staff)

    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions for admin or project creator
        return (
                request.user.is_admin or
                request.user.is_staff or
                (obj.created_by_user and obj.created_by_user.id == request.user.id)
        )


class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for project management."""

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action in ['create', 'update', 'partial_update']:
            return ProjectCreateUpdateSerializer
        return ProjectSerializer

    def get_queryset(self):
        """Filter projects based on user role."""
        user = self.request.user

        # Admin users can see all projects
        if user.is_admin or user.is_staff:
            queryset = Project.objects.all()
        else:
            # Regular users can see:
            # 1. Projects they created
            # 2. Public projects
            # 3. Projects shared with their client
            queryset = Project.objects.filter(
                Q(created_by_user=user) |
                Q(is_public=True) |
                Q(client_projects__client=user.client, client_projects__is_active=True)
            ).distinct()

        # Additional filtering
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        is_public = self.request.query_params.get('is_public')
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a new project with audit logging."""
        with transaction.atomic():
            # Set the creator to the current user
            project = serializer.save(created_by_user=self.request.user)

            create_audit_log(
                user=self.request.user,
                action='Project created',
                details={
                    'project_id': project.id,
                    'project_name': project.name
                },
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a project with audit logging."""
        with transaction.atomic():
            project = serializer.save()

            create_audit_log(
                user=self.request.user,
                action='Project updated',
                details={
                    'project_id': project.id,
                    'project_name': project.name
                },
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a project with audit logging."""
        project_id = instance.id
        project_name = instance.name

        with transaction.atomic():
            instance.delete()

            create_audit_log(
                user=self.request.user,
                action='Project deleted',
                details={
                    'project_id': project_id,
                    'project_name': project_name
                },
                request=self.request
            )

    @action(detail=True, methods=['get'])
    def clients(self, request, pk=None):
        """Return the clients associated with this project."""
        project = self.get_object()
        client_projects = project.client_projects.select_related('client')

        clients_data = [{
            'id': cp.client.id,
            'name': cp.client.name,
            'is_active': cp.is_active,
            'unique_link': cp.unique_link,
            'expires_at': cp.expires_at,
            'last_accessed': cp.last_accessed
        } for cp in client_projects]

        return Response(clients_data)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a project."""
        source_project = self.get_object()

        # Get clone parameters
        name = request.data.get('name', f"Copy of {source_project.name}")

        with transaction.atomic():
            # Create new project
            new_project = Project.objects.create(
                name=name,
                description=source_project.description,
                is_public=source_project.is_public,
                is_active=True,
                default_center_lat=source_project.default_center_lat,
                default_center_lng=source_project.default_center_lng,
                default_zoom_level=source_project.default_zoom_level,
                map_controls=source_project.map_controls,
                map_options=source_project.map_options,
                created_by_user=request.user
            )

            # Clone layer groups
            for group in source_project.layer_groups.all():
                new_group = ProjectLayerGroup.objects.create(
                    project=new_project,
                    name=group.name,
                    display_order=group.display_order,
                    is_visible_by_default=group.is_visible_by_default,
                    is_expanded_by_default=group.is_expanded_by_default
                )

                # Clone layers
                for layer in group.layers.all():
                    new_layer = ProjectLayer.objects.create(
                        project_layer_group=new_group,
                        layer_type=layer.layer_type,
                        name=layer.name,
                        description=layer.description,
                        style=layer.style,
                        z_index=layer.z_index,
                        is_visible_by_default=layer.is_visible_by_default,
                        min_zoom_visibility=layer.min_zoom_visibility,
                        max_zoom_visibility=layer.max_zoom_visibility,
                        marker_type=layer.marker_type,
                        marker_image_url=layer.marker_image_url,
                        marker_options=layer.marker_options,
                        enable_clustering=layer.enable_clustering,
                        clustering_options=layer.clustering_options,
                        enable_labels=layer.enable_labels,
                        label_options=layer.label_options
                    )

            create_audit_log(
                user=request.user,
                action='Project cloned',
                details={
                    'source_project_id': source_project.id,
                    'new_project_id': new_project.id
                },
                request=request
            )

        return Response({
            'id': new_project.id,
            'name': new_project.name,
            'message': 'Project cloned successfully'
        })

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get project statistics."""
        project = self.get_object()

        # Collect statistics
        layer_groups = project.layer_groups.all()
        all_layers = ProjectLayer.objects.filter(project_layer_group__in=layer_groups)

        # Get feature counts
        total_features = 0
        layer_stats = []

        for layer in all_layers:
            feature_count = layer.features.count()
            total_features += feature_count

            layer_stats.append({
                'id': layer.id,
                'name': layer.name,
                'feature_count': feature_count,
                'last_updated': layer.last_data_update
            })

        return Response({
            'total_layer_groups': layer_groups.count(),
            'total_layers': all_layers.count(),
            'total_features': total_features,
            'layer_stats': layer_stats,
            'client_shares': project.client_projects.count(),
            'created_at': project.created_at,
            'created_by': project.created_by_user.username if project.created_by_user else None
        })


class ProjectConstructorView(APIView):
    """
    Provides a complete project structure for frontend rendering.
    """
    permission_classes = [permissions.AllowAny]  # Allow unauthenticated access

    def get(self, request, project_id=None, hash_code=None):
        """
        Get complete project structure.
        Access via authenticated project_id or unauthenticated hash_code.
        """
        # Case 1: Access by hash code (standalone viewer)
        if hash_code and not project_id:
            try:
                # Find project by hash code
                client_project = ClientProject.objects.get(unique_link=hash_code, is_active=True)
                project = client_project.project
                is_authenticated = False  # Flag for filtering public layers

                # Log access for analytics
                client_project.last_accessed = timezone.now()
                client_project.save(update_fields=['last_accessed'])

                # Create audit log
                create_audit_log(
                    user=None,
                    action='Project accessed via shared link',
                    details={
                        'project_id': project.id,
                        'project_name': project.name,
                        'client_id': client_project.client_id,
                        'hash_code': hash_code
                    },
                    request=request
                )

            except ClientProject.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired link'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Case 2: Access by project ID (authenticated user)
        elif project_id and not hash_code:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                project = Project.objects.get(id=project_id)
                is_authenticated = True  # Flag for including all layers

                # Check if user has access
                if not (request.user.is_admin or request.user.is_staff):
                    # Check if project is public or shared with user's client
                    user_client = request.user.client
                    if not (project.is_public or
                            (user_client and ClientProject.objects.filter(
                                client=user_client, project=project, is_active=True).exists())):
                        return Response(
                            {'error': 'Access denied'},
                            status=status.HTTP_403_FORBIDDEN
                        )

                # Create audit log
                create_audit_log(
                    user=request.user,
                    action='Project accessed',
                    details={
                        'project_id': project.id,
                        'project_name': project.name
                    },
                    request=request
                )

            except Project.DoesNotExist:
                return Response(
                    {'error': 'Project not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        else:
            return Response(
                {'error': 'Either project_id or hash_code must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build project constructor response
        result = self._build_project_constructor(project, is_authenticated)

        return Response(result)

    def _build_project_constructor(self, project, is_authenticated):
        """
        Build complete project structure.
        """
        # Project base info
        result = {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "default_center": {
                    "lat": project.default_center_lat,
                    "lng": project.default_center_lng
                },
                "default_zoom": project.default_zoom_level,
                "min_zoom": project.min_zoom,
                "max_zoom": project.max_zoom,
                "map_controls": project.map_controls,
                "map_options": project.map_options
            },
            "basemaps": [],
            "layer_groups": [],
            "tools": []
        }

        # Add basemaps
        for pb in project.project_basemaps.all():
            basemap = pb.basemap
            result["basemaps"].append({
                "id": basemap.id,
                "name": basemap.name,
                "is_default": pb.is_default,
                "provider": basemap.provider,
                "url_template": basemap.url_template,
                "attribution": basemap.attribution,
                "options": {**basemap.options, **pb.custom_options}
            })

        # Add layer groups and layers
        for group in project.layer_groups.all().order_by('display_order'):
            group_data = {
                "id": group.id,
                "name": group.name,
                "display_order": group.display_order,
                "is_visible": group.is_visible_by_default,
                "is_expanded": group.is_expanded_by_default,
                "layers": []
            }

            # Get layers, filtering for public if unauthenticated
            layers_query = group.layers.all()
            if not is_authenticated:
                layers_query = layers_query.filter(is_public=True)

            for layer in layers_query.order_by('z_index'):
                # Get feature count
                feature_count = layer.features.count()

                # Calculate number of chunks needed based on layer type
                chunk_size = self._get_chunk_size_for_layer(layer)
                total_chunks = (feature_count + chunk_size - 1) // chunk_size  # Ceiling division
                chunk_ids = list(range(1, total_chunks + 1)) if total_chunks > 0 else [1]

                layer_data = {
                    "id": layer.id,
                    "name": layer.name,
                    "type": layer.layer_type.type_name if layer.layer_type else "unknown",
                    "is_visible": layer.is_visible_by_default,
                    "z_index": layer.z_index,
                    "min_zoom": layer.min_zoom_visibility,
                    "max_zoom": layer.max_zoom_visibility,
                    "style": layer.style,
                    "data_source": {
                        "type": "chunked",
                        "total_features": feature_count,
                        "chunk_size": chunk_size,
                        "chunk_ids": chunk_ids,
                        "attribution": layer.attribution
                    }
                }

                # Add clustering if enabled
                if layer.enable_clustering:
                    layer_data["clustering"] = {
                        "enabled": True,
                        "options": layer.clustering_options
                    }

                # Add labels if enabled
                if layer.enable_labels:
                    layer_data["labels"] = {
                        "enabled": True,
                        "options": layer.label_options
                    }

                # Add popup template if available
                if layer.popup_template:
                    layer_data["popup"] = {
                        "template_id": layer.popup_template.id,
                        "template_name": layer.popup_template.name,
                        "html_template": layer.popup_template.html_template,
                        "field_mappings": layer.popup_template.field_mappings,
                        "max_width": layer.popup_template.max_width,
                        "include_zoom": layer.popup_template.include_zoom_to_feature
                    }

                # Add marker library if available
                if layer.marker_library:
                    layer_data["marker"] = {
                        "library_id": layer.marker_library.id,
                        "library_name": layer.marker_library.name,
                        "icon_type": layer.marker_library.icon_type,
                        "icon_url": layer.marker_library.icon_url,
                        "default_size": layer.marker_library.default_size,
                        "default_color": layer.marker_library.default_color
                    }

                # Add functions if any
                functions = []
                for plf in layer.functions.filter(enabled=True):
                    functions.append({
                        "id": plf.id,
                        "type": plf.layer_function.function_type,
                        "name": plf.layer_function.name,
                        "arguments": plf.function_arguments,
                        "priority": plf.priority
                    })

                if functions:
                    layer_data["functions"] = functions

                group_data["layers"].append(layer_data)

            # Only add group if it has layers
            if group_data["layers"]:
                result["layer_groups"].append(group_data)

        # Add tools
        for pt in project.tools.filter(is_enabled=True).order_by('display_order'):
            tool = pt.tool
            result["tools"].append({
                "id": tool.id,
                "name": tool.name,
                "type": tool.tool_type,
                "position": pt.custom_position or tool.ui_position,
                "options": {**tool.default_options, **pt.tool_options}
            })

        return result

    def _get_chunk_size_for_layer(self, layer):
        """
        Determine appropriate chunk size based on layer type.
        """
        if not layer.layer_type:
            return 10000  # Default

        layer_type = layer.layer_type.type_name.lower()

        if layer_type in ['polygon', 'multipolygon']:
            return 500  # Smaller chunks for polygons
        elif layer_type in ['line', 'linestring', 'multilinestring']:
            return 2000  # Medium chunks for lines
        else:  # point, multipoint, or other
            return 10000  # Large chunks for points
```
# End of file: projects\views.py

# File: styling\views.py
```python
# styling/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
import base64

from layers.models import ProjectLayer
from .models import MarkerLibrary, PopupTemplate, StyleLibrary, ColorPalette
from .serializers import (
    MarkerLibrarySerializer,
    PopupTemplateSerializer,
    StyleLibrarySerializer,
    ColorPaletteSerializer
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


class MarkerLibraryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing map markers."""

    queryset = MarkerLibrary.objects.all()
    serializer_class = MarkerLibrarySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'tags', 'category']
    ordering_fields = ['name', 'created_at', 'updated_at', 'category']

    def get_queryset(self):
        """Filter markers based on query parameters."""
        queryset = MarkerLibrary.objects.all()

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # Filter by tag (exact match)
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__icontains=tag)

        # Filter by icon type
        icon_type = self.request.query_params.get('icon_type')
        if icon_type:
            queryset = queryset.filter(icon_type=icon_type)

        # Filter by system/custom
        is_system = self.request.query_params.get('is_system')
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a marker with audit logging."""
        with transaction.atomic():
            marker = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Marker created',
                details={'marker_id': marker.id, 'name': marker.name},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a marker with audit logging."""
        with transaction.atomic():
            marker = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Marker updated',
                details={'marker_id': marker.id, 'name': marker.name},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a marker with audit logging."""
        marker_id = instance.id
        marker_name = instance.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Marker deleted',
                details={'marker_id': marker_id, 'name': marker_name},
                request=self.request
            )

    @action(detail=False, methods=['post'])
    def upload_svg(self, request):
        """Upload an SVG file to create a new marker."""
        try:
            # Extract data from request
            name = request.data.get('name')
            description = request.data.get('description', '')
            svg_data = request.data.get('svg_data', '')

            if not name or not svg_data:
                return Response(
                    {'error': 'Name and SVG data are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Convert base64 to binary
            if 'base64,' in svg_data:
                # Extract the actual base64 data
                svg_data = svg_data.split('base64,')[1]

            svg_binary = base64.b64decode(svg_data)

            # Create marker
            marker = MarkerLibrary.objects.create(
                name=name,
                description=description,
                icon_type='svg',
                icon_data=svg_binary,
                created_by_user=request.user
            )

            # Create audit log
            create_audit_log(
                user=request.user,
                action='SVG marker uploaded',
                details={'marker_id': marker.id, 'name': marker.name},
                request=request
            )

            return Response(
                MarkerLibrarySerializer(marker).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PopupTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing popup templates."""

    queryset = PopupTemplate.objects.all()
    serializer_class = PopupTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        """Filter templates based on query parameters."""
        queryset = PopupTemplate.objects.all()

        # Filter by system/custom
        is_system = self.request.query_params.get('is_system')
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a template with audit logging."""
        with transaction.atomic():
            template = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Popup template created',
                details={'template_id': template.id, 'name': template.name},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a template with audit logging."""
        with transaction.atomic():
            template = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Popup template updated',
                details={'template_id': template.id, 'name': template.name},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a template with audit logging."""
        template_id = instance.id
        template_name = instance.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Popup template deleted',
                details={'template_id': template_id, 'name': template_name},
                request=self.request
            )

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Generate a preview of the template with sample data."""
        template = self.get_object()

        # Create sample data for preview
        sample_data = {
            "name": "Sample Feature",
            "description": "This is a sample description",
            "value": 1234.56,
            "category": "Sample Category",
            "date": "2023-05-15"
        }

        # Create simple HTML preview with template and sample data
        html = """
        <html>
        <head>
            <title>Template Preview</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 10px; }
                h3 { margin-top: 0; }
                .preview-container { max-width: 500px; border: 1px solid #ccc; padding: 15px; }
                .template-container { border: 1px dashed #aaa; padding: 10px; margin-top: 10px; }
            </style>
            <style>
                {}
            </style>
        </head>
        <body>
            <div class="preview-container">
                <h3>Template Preview: {}</h3>
                <div>Field mappings: {}</div>
                <div class="template-container">
                    {}
                </div>
            </div>
        </body>
        </html>
        """.format(
            template.css_styles or '',
            template.name,
            template.field_mappings,
            template.html_template
        )

        return Response({
            'html': html,
            'sample_data': sample_data
        })


class StyleLibraryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing style libraries."""

    queryset = StyleLibrary.objects.all()
    serializer_class = StyleLibrarySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        """Filter styles based on query parameters."""
        queryset = StyleLibrary.objects.all()

        # Filter by style type
        style_type = self.request.query_params.get('style_type')
        if style_type:
            queryset = queryset.filter(style_type=style_type)

        # Filter by system/custom
        is_system = self.request.query_params.get('is_system')
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a style with audit logging."""
        with transaction.atomic():
            style = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Style created',
                details={'style_id': style.id, 'name': style.name},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a style with audit logging."""
        with transaction.atomic():
            style = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Style updated',
                details={'style_id': style.id, 'name': style.name},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a style with audit logging."""
        style_id = instance.id
        style_name = instance.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Style deleted',
                details={'style_id': style_id, 'name': style_name},
                request=self.request
            )

    @action(detail=True, methods=['post'])
    def apply_to_layer(self, request, pk=None):
        """Apply this style to a layer."""
        style = self.get_object()

        layer_id = request.data.get('layer_id')
        if not layer_id:
            return Response({'error': 'Layer ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            layer = ProjectLayer.objects.get(id=layer_id)

            # Update layer style
            layer.style = style.style_definition.copy()
            layer.save()

            # Create audit log
            create_audit_log(
                user=request.user,
                action='Style applied to layer',
                details={'style_id': style.id, 'layer_id': layer.id},
                request=request
            )

            return Response({
                'message': 'Style applied successfully',
                'layer_id': layer.id,
                'layer_name': layer.name
            })

        except ProjectLayer.DoesNotExist:
            return Response({'error': 'Layer not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def generate_categorized(self, request, pk=None):
        """Generate a categorized style based on property values."""
        style = self.get_object()

        property_name = request.data.get('property')
        if not property_name:
            return Response({'error': 'Property name is required'}, status=status.HTTP_400_BAD_REQUEST)

        layer_id = request.data.get('layer_id')
        if not layer_id:
            return Response({'error': 'Layer ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get layer and unique values
            layer = ProjectLayer.objects.get(id=layer_id)

            # For demo, we'll simulate success
            # In production, get actual unique values and generate styles

            # Create new style definition
            style_definition = style.style_definition.copy()
            style_definition['categorized'] = {
                'property': property_name,
                'categories': [
                    {'value': 'Category 1', 'color': '#ff0000'},
                    {'value': 'Category 2', 'color': '#00ff00'},
                    {'value': 'Category 3', 'color': '#0000ff'}
                ]
            }

            return Response({
                'message': 'Categorized style generated',
                'style_definition': style_definition
            })

        except ProjectLayer.DoesNotExist:
            return Response({'error': 'Layer not found'}, status=status.HTTP_404_NOT_FOUND)


class ColorPaletteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing color palettes."""

    queryset = ColorPalette.objects.all()
    serializer_class = ColorPaletteSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        """Filter palettes based on query parameters."""
        queryset = ColorPalette.objects.all()

        # Filter by palette type
        palette_type = self.request.query_params.get('palette_type')
        if palette_type:
            queryset = queryset.filter(palette_type=palette_type)

        # Filter by system/custom
        is_system = self.request.query_params.get('is_system')
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        """Create a palette with audit logging."""
        with transaction.atomic():
            palette = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Color palette created',
                details={'palette_id': palette.id, 'name': palette.name},
                request=self.request
            )

    def perform_update(self, serializer):
        """Update a palette with audit logging."""
        with transaction.atomic():
            palette = serializer.save()
            create_audit_log(
                user=self.request.user,
                action='Color palette updated',
                details={'palette_id': palette.id, 'name': palette.name},
                request=self.request
            )

    def perform_destroy(self, instance):
        """Delete a palette with audit logging."""
        palette_id = instance.id
        palette_name = instance.name

        with transaction.atomic():
            instance.delete()
            create_audit_log(
                user=self.request.user,
                action='Color palette deleted',
                details={'palette_id': palette_id, 'name': palette_name},
                request=self.request
            )
```
# End of file: styling\views.py

# File: users\views.py
```python
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
```
# End of file: users\views.py

# File: basemaps\serializers.py
```python
# basemaps/serializers.py
from rest_framework import serializers
from .models import Basemap, ProjectBasemap
import base64


class BasemapSerializer(serializers.ModelSerializer):
    """Serializer for basemap objects."""

    preview_image_base64 = serializers.SerializerMethodField(read_only=True)
    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')
    provider_display = serializers.ReadOnlyField(source='get_provider_display')

    class Meta:
        model = Basemap
        fields = (
            'id', 'name', 'description', 'provider', 'provider_display',
            'url_template', 'options', 'attribution', 'min_zoom', 'max_zoom',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at', 'preview_image_base64'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')
        extra_kwargs = {
            'api_key': {'write_only': True}  # Never expose API keys in responses
        }

    def get_preview_image_base64(self, obj):
        """Convert binary preview image to base64 for frontend display."""
        if obj.preview_image:
            return base64.b64encode(obj.preview_image).decode('utf-8')
        return None

    def create(self, validated_data):
        """Create a basemap with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class ProjectBasemapSerializer(serializers.ModelSerializer):
    """Serializer for project basemap associations."""

    basemap_name = serializers.ReadOnlyField(source='basemap.name')
    basemap_provider = serializers.ReadOnlyField(source='basemap.provider')
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = ProjectBasemap
        fields = (
            'id', 'project', 'project_name', 'basemap', 'basemap_name',
            'basemap_provider', 'is_default', 'display_order',
            'custom_options', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'project_name', 'basemap_name')


class BasemapDetailSerializer(BasemapSerializer):
    """Extended serializer for basemap details including projects."""

    projects = serializers.SerializerMethodField()

    class Meta(BasemapSerializer.Meta):
        fields = BasemapSerializer.Meta.fields + ('projects',)

    def get_projects(self, obj):
        """List projects using this basemap."""
        project_basemaps = obj.project_instances.all()
        return [
            {
                'id': pb.project.id,
                'name': pb.project.name,
                'is_default': pb.is_default,
                'display_order': pb.display_order
            }
            for pb in project_basemaps
        ]
```
# End of file: basemaps\serializers.py

# File: clients\serializers.py
```python
# clients/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, ClientProject

User = get_user_model()


class ClientSerializer(serializers.ModelSerializer):
    """Serializer for client objects."""

    class Meta:
        model = Client
        fields = ('id', 'name', 'contact_email', 'contact_phone', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class ClientDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for client objects with user count."""

    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ('id', 'name', 'contact_email', 'contact_phone',
                  'is_active', 'created_at', 'updated_at', 'user_count')
        read_only_fields = ('id', 'created_at', 'updated_at', 'user_count')

    def get_user_count(self, obj):
        return obj.users.count()


class ClientUserSerializer(serializers.ModelSerializer):
    """Serializer for users associated with a client."""

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'is_active', 'last_login')
        read_only_fields = fields


class ClientProjectSerializer(serializers.ModelSerializer):
    """Serializer for client projects."""

    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = ClientProject
        fields = ('id', 'client', 'project', 'project_name', 'unique_link',
                  'is_active', 'created_at', 'expires_at', 'last_accessed')
        read_only_fields = ('id', 'created_at', 'last_accessed')
```
# End of file: clients\serializers.py

# File: functions\serializers.py
```python
# functions/serializers.py
from rest_framework import serializers
from .models import LayerFunction, ProjectLayerFunction, MapTool, ProjectTool


class LayerFunctionSerializer(serializers.ModelSerializer):
    """Serializer for layer function objects."""

    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')
    function_type_display = serializers.ReadOnlyField(source='get_function_type_display')

    class Meta:
        model = LayerFunction
        fields = (
            'id', 'name', 'description', 'function_type', 'function_type_display',
            'function_config', 'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')
        extra_kwargs = {
            'function_code': {'write_only': True}  # Don't expose code in regular responses
        }

    def create(self, validated_data):
        """Create a function with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class LayerFunctionDetailSerializer(LayerFunctionSerializer):
    """Extended serializer for layer function details including code."""

    class Meta(LayerFunctionSerializer.Meta):
        fields = LayerFunctionSerializer.Meta.fields + ('function_code',)


class ProjectLayerFunctionSerializer(serializers.ModelSerializer):
    """Serializer for project layer function associations."""

    function_name = serializers.ReadOnlyField(source='layer_function.name')
    function_type = serializers.ReadOnlyField(source='layer_function.function_type')
    layer_name = serializers.ReadOnlyField(source='project_layer.name')

    class Meta:
        model = ProjectLayerFunction
        fields = (
            'id', 'project_layer', 'layer_name', 'layer_function', 'function_name',
            'function_type', 'function_arguments', 'enabled', 'priority',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'function_name', 'layer_name')


class MapToolSerializer(serializers.ModelSerializer):
    """Serializer for map tool objects."""

    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')
    tool_type_display = serializers.ReadOnlyField(source='get_tool_type_display')
    ui_position_display = serializers.ReadOnlyField(source='get_ui_position_display')

    class Meta:
        model = MapTool
        fields = (
            'id', 'name', 'description', 'tool_type', 'tool_type_display',
            'icon', 'default_options', 'ui_position', 'ui_position_display',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')
        extra_kwargs = {
            'tool_code': {'write_only': True}  # Don't expose code in regular responses
        }

    def create(self, validated_data):
        """Create a tool with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class MapToolDetailSerializer(MapToolSerializer):
    """Extended serializer for map tool details including code."""

    class Meta(MapToolSerializer.Meta):
        fields = MapToolSerializer.Meta.fields + ('tool_code',)


class ProjectToolSerializer(serializers.ModelSerializer):
    """Serializer for project tool associations."""

    tool_name = serializers.ReadOnlyField(source='tool.name')
    tool_type = serializers.ReadOnlyField(source='tool.tool_type')
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = ProjectTool
        fields = (
            'id', 'project', 'project_name', 'tool', 'tool_name',
            'tool_type', 'is_enabled', 'display_order', 'tool_options',
            'custom_position', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'tool_name', 'project_name')
```
# End of file: functions\serializers.py

# File: layers\serializers.py
```python
# layers/serializers.py
from rest_framework import serializers
from django.contrib.gis.geos import GEOSGeometry
from .models import LayerType, ProjectLayerGroup, ProjectLayer, ProjectLayerData, LayerPermission


class LayerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayerType
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ProjectLayerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectLayerGroup
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ProjectLayerSerializer(serializers.ModelSerializer):
    project_name = serializers.SerializerMethodField()
    layer_type_name = serializers.ReadOnlyField(source='layer_type.type_name')
    feature_count = serializers.ReadOnlyField()

    class Meta:
        model = ProjectLayer
        fields = (
            'id', 'project_layer_group', 'project_name', 'layer_type', 'layer_type_name',
            'name', 'description', 'style', 'z_index', 'is_visible_by_default',
            'min_zoom_visibility', 'max_zoom_visibility', 'marker_type',
            'marker_image_url', 'marker_options', 'enable_clustering',
            'clustering_options', 'enable_labels', 'label_options',
            'feature_count', 'data_source', 'attribution',
            'created_at', 'updated_at', 'last_data_update'
        )
        read_only_fields = ('created_at', 'updated_at', 'feature_count', 'last_data_update')

    def get_project_name(self, obj):
        return obj.project_layer_group.project.name


class SimpleFeatureSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing features without full geometry."""
    geometry_type = serializers.SerializerMethodField()

    class Meta:
        model = ProjectLayerData
        fields = ('id', 'feature_id', 'geometry_type', 'properties', 'created_at')
        read_only_fields = ('created_at',)

    def get_geometry_type(self, obj):
        return obj.geometry.geom_type if obj.geometry else None


class FeatureSerializer(serializers.ModelSerializer):
    """Full serializer for individual features with complete geometry."""
    geometry = serializers.JSONField()  # We'll convert to/from GeoJSON in to_representation/to_internal_value

    class Meta:
        model = ProjectLayerData
        fields = ('id', 'project_layer', 'feature_id', 'geometry', 'properties', 'created_at')
        read_only_fields = ('created_at',)

    def to_representation(self, instance):
        """Convert GEOS geometry to GeoJSON."""
        ret = super().to_representation(instance)
        # Convert geometry to GeoJSON
        if instance.geometry:
            ret['geometry'] = instance.geometry.json
        return ret

    def to_internal_value(self, data):
        """Convert GeoJSON to GEOS geometry."""
        internal_value = super().to_internal_value(data)

        # Convert GeoJSON to GEOS geometry
        if 'geometry' in internal_value and isinstance(internal_value['geometry'], dict):
            geometry_json = internal_value['geometry']
            internal_value['geometry'] = GEOSGeometry(str(geometry_json))

        return internal_value


class GeoJSONFeatureCollectionSerializer(serializers.Serializer):
    """Serializer for GeoJSON FeatureCollection format."""
    type = serializers.ReadOnlyField(default='FeatureCollection')
    features = serializers.SerializerMethodField()

    def get_features(self, layer):
        """Convert all features to GeoJSON Feature objects."""
        features = []
        for feature in layer.features.all():
            geo_feature = {
                'type': 'Feature',
                'id': feature.feature_id,
                'geometry': feature.geometry.json,
                'properties': feature.properties
            }
            features.append(geo_feature)
        return features


class LayerPermissionSerializer(serializers.ModelSerializer):
    client_name = serializers.ReadOnlyField(source='client_project.client.name')
    project_name = serializers.ReadOnlyField(source='client_project.project.name')
    layer_name = serializers.ReadOnlyField(source='project_layer.name')

    class Meta:
        model = LayerPermission
        fields = (
            'id', 'project_layer', 'client_project', 'client_name',
            'project_name', 'layer_name', 'can_view', 'can_edit',
            'can_export', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')
```
# End of file: layers\serializers.py

# File: projects\serializers.py
```python
# projects/serializers.py
from rest_framework import serializers
from .models import Project
from django.contrib.auth import get_user_model

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for project objects."""

    creator_username = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'is_public', 'is_active',
            'default_center_lat', 'default_center_lng', 'default_zoom_level',
            'map_controls', 'map_options', 'max_zoom', 'min_zoom',
            'created_at', 'updated_at', 'created_by_user', 'creator_username'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_creator_username(self, obj):
        if obj.created_by_user:
            return obj.created_by_user.username
        return None


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating project objects."""

    class Meta:
        model = Project
        fields = (
            'id',  # Add the id field to the serializer
            'name', 'description', 'is_public', 'is_active',
            'default_center_lat', 'default_center_lng', 'default_zoom_level',
            'map_controls', 'map_options', 'max_zoom', 'min_zoom',
        )
        read_only_fields = ('id',)  # Mark it as read-only
```
# End of file: projects\serializers.py

# File: styling\serializers.py
```python
# styling/serializers.py
from rest_framework import serializers
from .models import MarkerLibrary, PopupTemplate, StyleLibrary, ColorPalette
from django.core.files.base import ContentFile
import base64
import uuid


class MarkerLibrarySerializer(serializers.ModelSerializer):
    """Serializer for marker library objects."""

    icon_data_base64 = serializers.SerializerMethodField(read_only=True)
    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')

    class Meta:
        model = MarkerLibrary
        fields = (
            'id', 'name', 'description', 'icon_url', 'icon_type',
            'default_options', 'default_size', 'default_anchor', 'default_color',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at', 'tags', 'category', 'icon_data_base64'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')

    def get_icon_data_base64(self, obj):
        """Convert binary icon data to base64 for frontend display."""
        if obj.icon_data:
            return base64.b64encode(obj.icon_data).decode('utf-8')
        return None

    def create(self, validated_data):
        """Create a marker with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class PopupTemplateSerializer(serializers.ModelSerializer):
    """Serializer for popup template objects."""

    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')

    class Meta:
        model = PopupTemplate
        fields = (
            'id', 'name', 'description', 'html_template', 'field_mappings',
            'css_styles', 'max_width', 'max_height', 'include_zoom_to_feature',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')

    def create(self, validated_data):
        """Create a template with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class StyleLibrarySerializer(serializers.ModelSerializer):
    """Serializer for style library objects."""

    preview_image_base64 = serializers.SerializerMethodField(read_only=True)
    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')

    class Meta:
        model = StyleLibrary
        fields = (
            'id', 'name', 'description', 'style_definition', 'style_type',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at', 'preview_image_base64'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')

    def get_preview_image_base64(self, obj):
        """Convert binary preview image to base64 for frontend display."""
        if obj.preview_image:
            return base64.b64encode(obj.preview_image).decode('utf-8')
        return None

    def create(self, validated_data):
        """Create a style with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class ColorPaletteSerializer(serializers.ModelSerializer):
    """Serializer for color palette objects."""

    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')

    class Meta:
        model = ColorPalette
        fields = (
            'id', 'name', 'description', 'colors', 'palette_type',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')

    def create(self, validated_data):
        """Create a palette with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)
```
# End of file: styling\serializers.py

# File: users\serializers.py
```python
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import AuditLog

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user objects."""

    client_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'is_admin',
                  'client', 'client_name', 'created_at', 'updated_at', 'last_login')
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_login')

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.name
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user objects."""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'password',
                  'password_confirm', 'is_admin', 'client')
        read_only_fields = ('id',)

    def validate(self, attrs):
        """Validate that the passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        """Create and return a new user."""
        # Remove password_confirm field as it's not needed for user creation
        validated_data.pop('password_confirm')

        # Create user with create_user method to properly hash password
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user objects."""

    class Meta:
        model = User
        fields = ('email', 'full_name', 'is_admin')


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        """Validate the passwords."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs."""

    username = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ('id', 'username', 'action', 'action_details', 'occurred_at', 'ip_address')
        read_only_fields = fields

    def get_username(self, obj):
        """Get the username or 'Unknown' if user is None."""
        return obj.user.username if obj.user else 'Unknown'
```
# End of file: users\serializers.py

