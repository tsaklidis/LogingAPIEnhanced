import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories import UserFactory


@pytest.mark.django_db
class TestJWTAuth:
    def test_obtain_token(self, api_client):
        user = UserFactory()
        response = api_client.post(
            reverse("accounts:token_obtain_pair"),
            {"username": user.username, "password": "testpass123"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_refresh_token(self, api_client):
        user = UserFactory()
        response = api_client.post(
            reverse("accounts:token_obtain_pair"),
            {"username": user.username, "password": "testpass123"},
        )
        refresh_token = response.data["refresh"]

        response = api_client.post(
            reverse("accounts:token_refresh"),
            {"refresh": refresh_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_invalid_credentials(self, api_client):
        response = api_client.post(
            reverse("accounts:token_obtain_pair"),
            {"username": "nonexistent", "password": "wrongpass"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRegistration:
    def test_register_user(self, api_client):
        response = api_client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "strongpass123",
                "password_confirm": "strongpass123",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "newuser"

    def test_register_password_mismatch(self, api_client):
        response = api_client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "strongpass123",
                "password_confirm": "differentpass",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
