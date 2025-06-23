from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FCCQueryViewSet

router = DefaultRouter()
router.register(r'fcc-query', FCCQueryViewSet, basename='fcc-query')

urlpatterns = [
    path('', include(router.urls)),
]

