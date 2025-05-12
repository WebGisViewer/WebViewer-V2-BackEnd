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