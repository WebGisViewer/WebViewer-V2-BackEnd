from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
# from .views import FCCQueryViewSet


router = DefaultRouter()
router.register(r'fcc-query', views.FCCQueryViewSet,basename = 'fcc-query')

urlpatterns = [
    path('', include(router.urls)),  #/fcc-query/bounding_box_query/

]




