# styling/tests/test_styling_models.py
import pytest
from django.contrib.auth import get_user_model
from styling.models import MarkerLibrary, PopupTemplate, StyleLibrary, ColorPalette

User = get_user_model()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='admin123',
        is_admin=True
    )


@pytest.mark.django_db
class TestStylingModels:
    """Test styling-related models."""

    def test_create_marker(self, admin_user):
        """Test creating a marker."""
        marker = MarkerLibrary.objects.create(
            name='Test Marker',
            description='A test marker',
            icon_type='svg',
            default_size=32,
            default_color='#FF0000',
            created_by_user=admin_user
        )

        assert marker.id is not None
        assert marker.name == 'Test Marker'
        assert marker.icon_type == 'svg'
        assert marker.default_size == 32
        assert marker.default_color == '#FF0000'
        assert marker.created_by_user == admin_user

    def test_create_popup_template(self, admin_user):
        """Test creating a popup template."""
        template = PopupTemplate.objects.create(
            name='Test Template',
            description='A test template',
            html_template='<div>{{name}}</div>',
            field_mappings={'name': 'feature.properties.name'},
            max_width=400,
            created_by_user=admin_user
        )

        assert template.id is not None
        assert template.name == 'Test Template'
        assert template.html_template == '<div>{{name}}</div>'
        assert template.max_width == 400
        assert template.created_by_user == admin_user

    def test_create_style(self, admin_user):
        """Test creating a style."""
        style = StyleLibrary.objects.create(
            name='Test Style',
            description='A test style',
            style_type='polygon',
            style_definition={
                'fillColor': '#0000FF',
                'weight': 2,
                'opacity': 0.8
            },
            created_by_user=admin_user
        )

        assert style.id is not None
        assert style.name == 'Test Style'
        assert style.style_type == 'polygon'
        assert style.style_definition['fillColor'] == '#0000FF'
        assert style.created_by_user == admin_user

    def test_create_color_palette(self, admin_user):
        """Test creating a color palette."""
        palette = ColorPalette.objects.create(
            name='Test Palette',
            description='A test palette',
            palette_type='sequential',
            colors=['#FFFFFF', '#AAAAAA', '#555555', '#000000'],
            created_by_user=admin_user
        )

        assert palette.id is not None
        assert palette.name == 'Test Palette'
        assert palette.palette_type == 'sequential'
        assert len(palette.colors) == 4
        assert palette.colors[0] == '#FFFFFF'
        assert palette.created_by_user == admin_user