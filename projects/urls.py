# projects/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ProjectViewSet, ProjectConstructorView
from .views import ProjectViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('constructor/<int:project_id>/', ProjectConstructorView.as_view(), name='project-constructor'),
    path('standalone/<str:hash_code>/', ProjectConstructorView.as_view(), name='project-standalone'),
]