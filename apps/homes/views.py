from rest_framework import generics, permissions

from .models import Home, Space
from .permissions import IsHomeOwner
from .serializers import HomeListSerializer, HomeSerializer, SpaceSerializer


class HomeListCreateView(generics.ListCreateAPIView):
    """List all homes for the authenticated user or create a new one."""
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'management'

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return HomeListSerializer
        return HomeSerializer

    def get_queryset(self):
        return Home.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class HomeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a home."""
    serializer_class = HomeSerializer
    permission_classes = [permissions.IsAuthenticated, IsHomeOwner]
    throttle_scope = 'management'
    lookup_field = 'pk'

    def get_queryset(self):
        return Home.objects.filter(owner=self.request.user).prefetch_related('spaces')


class SpaceListCreateView(generics.ListCreateAPIView):
    """List spaces for a home or create a new one."""
    serializer_class = SpaceSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'management'

    def get_queryset(self):
        return Space.objects.filter(
            home__owner=self.request.user,
            home_id=self.kwargs['home_pk'],
        )

    def perform_create(self, serializer):
        home = Home.objects.get(pk=self.kwargs['home_pk'], owner=self.request.user)
        serializer.save(home=home)


class SpaceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a space."""
    serializer_class = SpaceSerializer
    permission_classes = [permissions.IsAuthenticated, IsHomeOwner]
    throttle_scope = 'management'
    lookup_field = 'pk'

    def get_queryset(self):
        return Space.objects.filter(home__owner=self.request.user).select_related('home')

