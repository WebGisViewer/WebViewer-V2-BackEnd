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

    # @action(detail=True, methods=['get'])
    # def export_geojson(self, request, pk=None):
    #     """Export layer data as GeoJSON."""
    #     layer = self.get_object()

    #     # Get layer features
    #     features_data = []
    #     for feature in layer.features.all():
    #         geojson_feature = {
    #             'type': 'Feature',
    #             'geometry': json.loads(feature.geometry.json),
    #             'properties': feature.properties
    #         }
    #         if feature.feature_id:
    #             geojson_feature['id'] = feature.feature_id
    #         features_data.append(geojson_feature)

    #     # Create GeoJSON
    #     geojson = {
    #         'type': 'FeatureCollection',
    #         'features': features_data
    #     }

    #     # Create audit log
    #     create_audit_log(
    #         user=request.user,
    #         action='GeoJSON export',
    #         details={'layer_id': layer.id},
    #         request=request
    #     )

    #     return Response(geojson)

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




## file upload complete upload functions below

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
                upload_status='importing',
                popup_template_id = request.data.get('popup_template_id', None),
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