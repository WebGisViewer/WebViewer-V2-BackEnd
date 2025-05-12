# styling/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'markers', views.MarkerLibraryViewSet)
router.register(r'popup-templates', views.PopupTemplateViewSet)
router.register(r'styles', views.StyleLibraryViewSet)
router.register(r'color-palettes', views.ColorPaletteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]