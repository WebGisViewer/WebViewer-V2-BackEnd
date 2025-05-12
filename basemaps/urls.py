# basemaps/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'basemaps', views.BasemapViewSet)
router.register(r'project-basemaps', views.ProjectBasemapViewSet)

urlpatterns = [
    path('', include(router.urls)),
]