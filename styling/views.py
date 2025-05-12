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