# layers/serializers.py
from rest_framework import serializers
from django.contrib.gis.geos import GEOSGeometry
from .models import LayerType, ProjectLayerGroup, ProjectLayer, ProjectLayerData, LayerPermission, CBRSLicense


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

class CBRSLicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CBRSLicense
        fields = '__all__'

class CountyCBRSSerializer(serializers.Serializer):
    """Serializer for county CBRS data in constructor"""
    county_fips = serializers.CharField()
    state_fips = serializers.CharField()
    county_name = serializers.CharField()
    state_name = serializers.CharField()
    licenses = CBRSLicenseSerializer(many=True)
    license_count = serializers.IntegerField()