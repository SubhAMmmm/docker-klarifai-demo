from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatasetViewSet, QueryViewSet

router = DefaultRouter()
router.register(r'datasets', DatasetViewSet)
router.register(r'queries', QueryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]