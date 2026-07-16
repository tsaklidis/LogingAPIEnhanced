import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories import HomeFactory, UserFactory


@pytest.mark.django_db
class TestHomes:
    def test_list_homes(self, authenticated_client, home):
        response = authenticated_client.get(reverse('homes:home-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_create_home(self, authenticated_client):
        response = authenticated_client.post(
            reverse('homes:home-list'),
            {'name': 'My Home', 'location': '123 Main St'},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'My Home'

    def test_cannot_access_others_home(self, api_client):
        other_home = HomeFactory()
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.get(
            reverse('homes:home-detail', kwargs={'pk': other_home.pk}),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSpaces:
    def test_list_spaces(self, authenticated_client, home, space):
        response = authenticated_client.get(
            reverse('homes:space-list', kwargs={'home_pk': home.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_create_space(self, authenticated_client, home):
        response = authenticated_client.post(
            reverse('homes:space-list', kwargs={'home_pk': home.pk}),
            {'name': 'Kitchen', 'is_public': False},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Kitchen'

