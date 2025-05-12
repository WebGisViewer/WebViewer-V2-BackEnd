from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserViewSet,
    AuditLogViewSet,
    CustomTokenObtainPairView,
    LogoutView,
    HealthCheckView
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'audit-logs', AuditLogViewSet)

# URLs for the users app
urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Authentication URLs
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # Health check URL
    path('health/', HealthCheckView.as_view(), name='health_check'),
]