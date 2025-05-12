# functions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'layer-functions', views.LayerFunctionViewSet)
router.register(r'project-layer-functions', views.ProjectLayerFunctionViewSet)
router.register(r'map-tools', views.MapToolViewSet)
router.register(r'project-tools', views.ProjectToolViewSet)

urlpatterns = [
    path('', include(router.urls)),
]