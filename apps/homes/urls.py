from django.urls import path

from . import views

app_name = 'homes'

urlpatterns = [
    path('homes/', views.HomeListCreateView.as_view(), name='home-list'),
    path('homes/<uuid:pk>/', views.HomeDetailView.as_view(), name='home-detail'),
    path('homes/<uuid:home_pk>/spaces/', views.SpaceListCreateView.as_view(), name='space-list'),
    path('spaces/<uuid:pk>/', views.SpaceDetailView.as_view(), name='space-detail'),
]

