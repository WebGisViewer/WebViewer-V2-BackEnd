# basemaps/tests/test_basemap_models.py
import pytest
from django.contrib.auth import get_user_model
from basemaps.models import Basemap, ProjectBasemap
from projects.models import Project

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


@pytest.mark.django_db
class TestBasemapModels:
    """Test basemaps-related models."""

    def test_create_basemap(self, admin_user):
        """Test creating a basemap."""
        basemap = Basemap.objects.create(
            name='Test Basemap',
            description='A test basemap',
            provider='openstreetmap',
            url_template='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attribution='© OpenStreetMap contributors',
            created_by_user=admin_user
        )

        assert basemap.id is not None
        assert basemap.name == 'Test Basemap'
        assert basemap.provider == 'openstreetmap'
        assert basemap.url_template == 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        assert basemap.created_by_user == admin_user

    def test_create_project_basemap(self, admin_user, test_project):
        """Test creating a project basemap assignment."""
        # First create a basemap
        basemap = Basemap.objects.create(
            name='Test OSM',
            provider='openstreetmap',
            url_template='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            created_by_user=admin_user
        )

        # Now create a project basemap
        project_basemap = ProjectBasemap.objects.create(
            project=test_project,
            basemap=basemap,
            is_default=True,
            display_order=1,
            custom_options={'maxZoom': 18}
        )

        assert project_basemap.id is not None
        assert project_basemap.project == test_project
        assert project_basemap.basemap == basemap
        assert project_basemap.is_default is True
        assert project_basemap.display_order == 1
        assert project_basemap.custom_options['maxZoom'] == 18

    def test_default_basemap_uniqueness(self, admin_user, test_project):
        """Test that only one basemap can be default per project."""
        # Create two basemaps
        basemap1 = Basemap.objects.create(
            name='OSM',
            provider='openstreetmap',
            created_by_user=admin_user
        )

        basemap2 = Basemap.objects.create(
            name='Google',
            provider='google',
            created_by_user=admin_user
        )

        # Set the first as default
        pb1 = ProjectBasemap.objects.create(
            project=test_project,
            basemap=basemap1,
            is_default=True,
            display_order=1
        )

        # Set the second as default
        pb2 = ProjectBasemap.objects.create(
            project=test_project,
            basemap=basemap2,
            is_default=True,
            display_order=2
        )

        # Refresh the first one from database
        pb1.refresh_from_db()

        # Verify the first is no longer default
        assert pb1.is_default is False
        assert pb2.is_default is True