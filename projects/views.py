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