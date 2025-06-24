from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="WebGIS Viewer V2 API",
      default_version='v1',
      description="API for the WebGIS Viewer V2 platform",
      terms_of_service="https://www.example.com/terms/",
      contact=openapi.Contact(email="contact@example.com"),
      license=openapi.License(name="Proprietary"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/v1/', include('users.urls')),
    path('api/v1/', include('clients.urls')),
    path('api/v1/', include('projects.urls')),
    path('api/v1/', include('layers.urls')),
    path('api/v1/', include('styling.urls')),
    path('api/v1/', include('basemaps.urls')),
    path('api/v1/', include('functions.urls')),
    path('api/v1/', include('fcc_bdc.urls'))
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)