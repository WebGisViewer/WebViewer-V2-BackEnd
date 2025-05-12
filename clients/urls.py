# clients/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ClientViewSet, ClientProjectViewSet

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'client-projects', ClientProjectViewSet)

# URLs for the clients app
urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),
]