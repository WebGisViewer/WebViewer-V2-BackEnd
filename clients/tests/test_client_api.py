# clients/tests/test_client_api.py
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from clients.models import Client, ClientProject
from projects.models import Project

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
        contact_email='contact@testclient.com',
        contact_phone='123-456-7890'
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


@pytest.mark.django_db
class TestClientAPI:
    """Test client API endpoints."""

    def test_create_client_as_admin(self, api_client, admin_user):
        """Test admin can create a client."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('client-list')
        data = {
            'name': 'New Test Client',
            'contact_email': 'new@testclient.com',
            'contact_phone': '987-654-3210',
            'is_active': True
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Client.objects.filter(name='New Test Client').exists()

    def test_create_client_as_regular_user(self, api_client, client_user):
        """Test regular user cannot create a client."""
        api_client.force_authenticate(user=client_user)
        url = reverse('client-list')
        data = {
            'name': 'Unauthorized Client',
            'contact_email': 'unauthorized@client.com'
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Client.objects.filter(name='Unauthorized Client').exists()

    def test_list_clients_as_admin(self, api_client, admin_user, test_client):
        """Test admin can list all clients."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('client-list')

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Access the 'results' key from the paginated response
        assert 'results' in response.data
        assert len(response.data['results']) >= 1
        assert any(client['name'] == test_client.name for client in response.data['results'])

    def test_get_client_users(self, api_client, admin_user, test_client, client_user):
        """Test getting users of a client."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('client-users', args=[test_client.id])

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any(user['username'] == client_user.username for user in response.data)

    def test_assign_project_to_client(self, api_client, admin_user, test_client, test_project):
        """Test assigning a project to a client."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('clientproject-list')
        data = {
            'client': test_client.id,
            'project': test_project.id,
            'unique_link': 'test-link-123',
            'is_active': True
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        # Verify relationship created
        client_project = ClientProject.objects.filter(
            client=test_client,
            project=test_project
        ).first()
        assert client_project is not None
        assert client_project.unique_link == 'test-link-123'

    def test_client_user_can_see_own_client(self, api_client, client_user, test_client):
        """Test that a client user can see their own client."""
        api_client.force_authenticate(user=client_user)

        # Get the user profile which should include client info
        url = reverse('user-me')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['client'] == test_client.id

    def test_client_user_can_access_shared_projects(self, api_client, client_user, test_client, test_project):
        """Test that a client user can access projects shared with their client."""
        # Create client project relationship
        ClientProject.objects.create(
            client=test_client,
            project=test_project,
            unique_link='access-test-link',
            is_active=True
        )

        api_client.force_authenticate(user=client_user)
        url = reverse('project-list')

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Check if the test project is in the paginated results
        assert 'results' in response.data
        project_ids = [project['id'] for project in response.data['results']]
        assert test_project.id in project_ids