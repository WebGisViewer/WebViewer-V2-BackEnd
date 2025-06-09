# layers/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    LayerDataView, ProjectLayerViewSet, FileUploadView, CompleteUploadView
)
router = DefaultRouter()
router.register(r'layer-types', views.LayerTypeViewSet)
router.register(r'layer-groups', views.ProjectLayerGroupViewSet)
router.register(r'layers', views.ProjectLayerViewSet)
router.register(r'features', views.ProjectLayerDataViewSet)
router.register(r'layer-permissions', views.LayerPermissionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('data/<int:layer_id>/', LayerDataView.as_view(), name='layer-data'),

    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('complete_upload/', CompleteUploadView.as_view(), name='complete-upload'),

]