# layers/tests/test_layer_models.py
import pytest
from django.contrib.gis.geos import Point, Polygon
from layers.models import LayerType, ProjectLayerGroup, ProjectLayer, ProjectLayerData
from projects.models import Project
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='admin123',
        is_admin=True
    )


@pytest.fixture
def test_project(admin_user):
    return Project.objects.create(
        name='Test Project',
        is_active=True,
        default_center_lat=34.0522,
        default_center_lng=-118.2437,
        default_zoom_level=10,
        created_by_user=admin_user
    )


@pytest.fixture
def test_layer_type():
    return LayerType.objects.create(
        type_name='Point Layer',
        description='A layer for point features',
        default_style={'color': '#ff0000', 'radius': 5}
    )


@pytest.fixture
def test_layer_group(test_project):
    return ProjectLayerGroup.objects.create(
        project=test_project,
        name='Test Layer Group',
        display_order=0
    )


@pytest.fixture
def test_layer(test_layer_group, test_layer_type):
    return ProjectLayer.objects.create(
        project_layer_group=test_layer_group,
        layer_type=test_layer_type,
        name='Test Layer',
        style={'color': '#00ff00'}
    )


@pytest.mark.django_db
class TestLayerModels:
    """Test layer-related models."""

    def test_create_layer_type(self, test_layer_type):
        """Test creating a layer type."""
        assert test_layer_type.id is not None
        assert test_layer_type.type_name == 'Point Layer'
        assert test_layer_type.default_style['color'] == '#ff0000'

    def test_create_layer_group(self, test_layer_group, test_project):
        """Test creating a layer group."""
        assert test_layer_group.id is not None
        assert test_layer_group.project == test_project
        assert test_layer_group.name == 'Test Layer Group'

    def test_create_layer(self, test_layer, test_layer_group, test_layer_type):
        """Test creating a layer."""
        assert test_layer.id is not None
        assert test_layer.project_layer_group == test_layer_group
        assert test_layer.layer_type == test_layer_type
        assert test_layer.name == 'Test Layer'
        assert test_layer.style['color'] == '#00ff00'

    def test_create_feature(self, test_layer):
        """Test creating a feature."""
        # Create a point feature
        point = Point(-118.2437, 34.0522)  # Los Angeles
        feature = ProjectLayerData.objects.create(
            project_layer=test_layer,
            geometry=point,
            properties={'name': 'Los Angeles', 'population': 3971883}
        )

        assert feature.id is not None
        assert feature.project_layer == test_layer
        assert feature.geometry.equals(point)
        assert feature.properties['name'] == 'Los Angeles'

        # Verify feature count updated
        test_layer.refresh_from_db()
        assert test_layer.feature_count == 1
        assert test_layer.last_data_update is not None

    def test_create_polygon_feature(self, test_layer):
        """Test creating a polygon feature."""
        # Create a simple rectangle
        coords = ((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))
        polygon = Polygon(coords)

        feature = ProjectLayerData.objects.create(
            project_layer=test_layer,
            geometry=polygon,
            properties={'name': 'Rectangle', 'area': 1}
        )

        assert feature.id is not None
        assert feature.geometry.equals(polygon)
        assert feature.bbox is not None  # Should automatically create bounding box