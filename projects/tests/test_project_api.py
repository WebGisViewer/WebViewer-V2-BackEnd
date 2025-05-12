# projects/tests/test_project_api.py
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from projects.models import Project
from clients.models import Client, ClientProject

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='admin123',
        is_admin=True
    )


@pytest.fixture
def test_client():
    return Client.objects.create(
        name='Test Client Inc.',
        contact_email='contact@testclient.com'
    )


@pytest.fixture
def client_user(test_client):
    return User.objects.create_user(
        username='clientuser',
        email='user@testclient.com',
        password='clientuser123',
        client=test_client
    )


@pytest.fixture
def test_project(admin_user):
    return Project.objects.create(
        name='Test Project',
        description='Project for testing',
        is_public=False,
        is_active=True,
        default_center_lat=34.0522,
        default_center_lng=-118.2437,
        default_zoom_level=10,
        created_by_user=admin_user
    )


@pytest.fixture
def public_project(admin_user):
    return Project.objects.create(
        name='Public Test Project',
        description='Public project for testing',
        is_public=True,
        is_active=True,
        default_center_lat=34.0522,
        default_center_lng=-118.2437,
        default_zoom_level=10,
        created_by_user=admin_user
    )


@pytest.mark.django_db
class TestProjectAPI:
    """Test project API endpoints."""

    def test_create_project_as_admin(self, api_client, admin_user):
        """Test admin can create a project."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('project-list')
        data = {
            'name': 'New Test Project',
            'description': 'New project for testing',
            'is_public': False,
            'is_active': True,
            'default_center_lat': 34.0522,
            'default_center_lng': -118.2437,
            'default_zoom_level': 10
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Project.objects.filter(name='New Test Project').exists()

    def test_regular_user_cant_create_project(self, api_client, client_user):
        """Test regular client users cannot create projects."""
        api_client.force_authenticate(user=client_user)
        url = reverse('project-list')
        data = {
            'name': 'Unauthorized Project',
            'description': 'This should fail',
            'is_public': False,
            'is_active': True,
            'default_center_lat': 34.0522,
            'default_center_lng': -118.2437,
            'default_zoom_level': 10
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Project.objects.filter(name='Unauthorized Project').exists()

    def test_admin_can_list_all_projects(self, api_client, admin_user, test_project, public_project):
        """Test admin can list all projects."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('project-list')

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Should contain both projects in the paginated results
        assert 'results' in response.data
        project_names = [project['name'] for project in response.data['results']]
        assert test_project.name in project_names
        assert public_project.name in project_names

    def test_client_user_can_see_public_projects(self, api_client, client_user, public_project):
        """Test client user can see public projects."""
        api_client.force_authenticate(user=client_user)
        url = reverse('project-list')

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Should contain only the public project in the paginated results
        assert 'results' in response.data
        project_names = [project['name'] for project in response.data['results']]
        assert public_project.name in project_names

    def test_client_user_can_see_shared_projects(self, api_client, client_user, test_client, test_project):
        """Test client user can see projects shared with their client."""
        # Create client project relationship
        ClientProject.objects.create(
            client=test_client,
            project=test_project,
            unique_link='test-link-access',
            is_active=True
        )

        api_client.force_authenticate(user=client_user)
        url = reverse('project-list')

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Should contain the shared project in the paginated results
        assert 'results' in response.data
        project_names = [project['name'] for project in response.data['results']]
        assert test_project.name in project_names

    def test_client_user_cant_see_unshared_projects(self, api_client, client_user, test_project):
        """Test client user cannot see projects not shared with their client."""
        api_client.force_authenticate(user=client_user)
        url = reverse('project-list')

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Should not contain the unshared private project in the paginated results
        assert 'results' in response.data
        project_names = [project['name'] for project in response.data['results']]
        assert test_project.name not in project_names

    def test_update_project(self, api_client, admin_user, test_project):
        """Test updating a project."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('project-detail', args=[test_project.id])
        data = {
            'name': 'Updated Project Name',
            'description': 'Updated description'
        }

        response = api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK

        # Verify project updated
        test_project.refresh_from_db()
        assert test_project.name == 'Updated Project Name'
        assert test_project.description == 'Updated description'

    def test_delete_project(self, api_client, admin_user, test_project):
        """Test deleting a project."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('project-detail', args=[test_project.id])

        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify project deleted
        assert not Project.objects.filter(id=test_project.id).exists()

    def test_view_project_clients(self, api_client, admin_user, test_project, test_client):
        """Test viewing clients with access to a project."""
        # Create client project relationship
        ClientProject.objects.create(
            client=test_client,
            project=test_project,
            unique_link='view-clients-test',
            is_active=True
        )

        api_client.force_authenticate(user=admin_user)
        url = reverse('project-clients', args=[test_project.id])

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Should contain the client
        client_names = [client['name'] for client in response.data]
        assert test_client.name in client_names