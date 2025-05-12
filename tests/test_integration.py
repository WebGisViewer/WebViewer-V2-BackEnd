# tests/test_integration.py
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


@pytest.mark.django_db
class TestCompleteFlow:
    """Test the complete flow from user creation to project access."""

    def test_complete_flow(self, api_client):
        """Test the entire flow of user creation, client creation, project sharing, and access."""
        # Step 1: Create admin user
        admin = User.objects.create_superuser(
            username='admin_flow',
            email='admin_flow@test.com',
            password='admin123',
            is_admin=True
        )

        # Step 2: Login as admin
        login_url = reverse('token_obtain_pair')
        login_data = {
            'username': 'admin_flow',
            'password': 'admin123'
        }
        login_response = api_client.post(login_url, login_data)
        assert login_response.status_code == status.HTTP_200_OK

        # Set authentication token
        admin_token = login_response.data['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')

        # Step 3: Create a client
        client_url = reverse('client-list')
        client_data = {
            'name': 'Flow Test Client',
            'contact_email': 'flow@testclient.com',
            'is_active': True
        }
        client_response = api_client.post(client_url, client_data)
        assert client_response.status_code == status.HTTP_201_CREATED
        client_id = client_response.data['id']

        # Step 4: Create a client user
        user_url = reverse('user-list')
        user_data = {
            'username': 'flowclientuser',
            'email': 'flow_user@testclient.com',
            'full_name': 'Flow Client User',
            'password': 'clientuser123',
            'password_confirm': 'clientuser123',
            'is_admin': False,
            'client': client_id
        }
        user_response = api_client.post(user_url, user_data)
        assert user_response.status_code == status.HTTP_201_CREATED

        # Step 5: Create a project
        project_url = reverse('project-list')
        project_data = {
            'name': 'Flow Test Project',
            'description': 'Project for flow testing',
            'is_public': False,
            'is_active': True,
            'default_center_lat': 34.0522,
            'default_center_lng': -118.2437,
            'default_zoom_level': 10
        }
        project_response = api_client.post(project_url, project_data)
        assert project_response.status_code == status.HTTP_201_CREATED

        project = Project.objects.get(name='Flow Test Project')
        project_id = project.id
        # Step 6: Assign project to client
        client_project_url = reverse('clientproject-list')
        client_project_data = {
            'client': client_id,
            'project': project_id,
            'unique_link': 'flow-test-link',
            'is_active': True
        }
        client_project_response = api_client.post(client_project_url, client_project_data)
        assert client_project_response.status_code == status.HTTP_201_CREATED

        # Step 7: Create a second project (not shared with client)
        private_project_data = {
            'name': 'Private Flow Test Project',
            'description': 'Private project for flow testing',
            'is_public': False,
            'is_active': True,
            'default_center_lat': 34.0522,
            'default_center_lng': -118.2437,
            'default_zoom_level': 10
        }
        private_project_response = api_client.post(project_url, private_project_data)
        assert private_project_response.status_code == status.HTTP_201_CREATED

        # Step 8: Create a public project
        public_project_data = {
            'name': 'Public Flow Test Project',
            'description': 'Public project for flow testing',
            'is_public': True,
            'is_active': True,
            'default_center_lat': 34.0522,
            'default_center_lng': -118.2437,
            'default_zoom_level': 10
        }
        public_project_response = api_client.post(project_url, public_project_data)
        assert public_project_response.status_code == status.HTTP_201_CREATED

        # Step 9: Log out admin and login as client user
        api_client.credentials()
        client_login_data = {
            'username': 'flowclientuser',
            'password': 'clientuser123'
        }
        client_login_response = api_client.post(login_url, client_login_data)
        assert client_login_response.status_code == status.HTTP_200_OK

        client_token = client_login_response.data['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {client_token}')

        # Step 10: Check user profile to confirm client association
        me_url = reverse('user-me')
        me_response = api_client.get(me_url)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.data['client'] == client_id

        # Step 11: List available projects
        projects_response = api_client.get(project_url)
        assert projects_response.status_code == status.HTTP_200_OK

        assert 'results' in projects_response.data
        project_names = [p['name'] for p in projects_response.data['results']]

        # Should see shared project and public project
        assert 'Flow Test Project' in project_names
        assert 'Public Flow Test Project' in project_names

        # Should NOT see private unshared project
        assert 'Private Flow Test Project' not in project_names

        # Step 12: Test permission boundaries
        # Try to create a client (should fail)
        unauthorized_client_data = {
            'name': 'Unauthorized Client',
            'contact_email': 'unauthorized@test.com'
        }
        unauthorized_client_response = api_client.post(client_url, unauthorized_client_data)
        assert unauthorized_client_response.status_code == status.HTTP_403_FORBIDDEN

        # Try to create a project (should fail)
        unauthorized_project_data = {
            'name': 'Unauthorized Project',
            'description': 'This should fail',
            'is_public': False
        }
        unauthorized_project_response = api_client.post(project_url, unauthorized_project_data)
        assert unauthorized_project_response.status_code == status.HTTP_403_FORBIDDEN