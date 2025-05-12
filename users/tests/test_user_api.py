# users/tests/test_user_api.py
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

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
def regular_user():
    return User.objects.create_user(
        username='user_test',
        email='user@test.com',
        password='user123'
    )


@pytest.mark.django_db
class TestUserAPI:
    """Test user API endpoints."""

    def test_login(self, api_client):
        """Test user login."""
        # Create a user
        User.objects.create_user(
            username='logintest',
            password='testpass123'
        )

        url = reverse('token_obtain_pair')
        data = {
            'username': 'logintest',
            'password': 'testpass123'
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials."""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'nonexistentuser',
            'password': 'wrongpass'
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_user_as_admin(self, api_client, admin_user):
        """Test admin can create a user."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('user-list')
        data = {
            'username': 'newuser',
            'email': 'new@user.com',
            'full_name': 'New User',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'is_admin': False
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        # Verify user created
        user = User.objects.get(username='newuser')
        assert user.email == 'new@user.com'
        assert user.is_admin == False

    def test_create_user_as_regular_user(self, api_client, regular_user):
        """Test regular user cannot create a user."""
        api_client.force_authenticate(user=regular_user)
        url = reverse('user-list')
        data = {
            'username': 'newuser',
            'email': 'new@user.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'is_admin': False
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(username='newuser').exists()

    def test_get_user_profile(self, api_client, regular_user):
        """Test retrieving user profile."""
        api_client.force_authenticate(user=regular_user)
        url = reverse('user-me')

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == regular_user.username

    def test_update_user_as_admin(self, api_client, admin_user, regular_user):
        """Test admin can update any user."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('user-detail', args=[regular_user.id])
        data = {
            'email': 'updated@user.com',
            'full_name': 'Updated User',
            'is_admin': False
        }

        response = api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK

        # Verify user updated
        regular_user.refresh_from_db()
        assert regular_user.email == 'updated@user.com'
        assert regular_user.full_name == 'Updated User'

    def test_password_change(self, api_client, regular_user):
        """Test user can change their password."""
        api_client.force_authenticate(user=regular_user)
        url = reverse('user-change-password', args=[regular_user.id])
        data = {
            'old_password': 'user123',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK

        # Verify password change by logging in
        api_client.logout()
        login_url = reverse('token_obtain_pair')
        login_data = {
            'username': regular_user.username,
            'password': 'newpassword123'
        }
        login_response = api_client.post(login_url, login_data)
        assert login_response.status_code == status.HTTP_200_OK