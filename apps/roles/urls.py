from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PermissionViewSet, RoleViewSet

router = DefaultRouter(trailing_slash=False)
router.register('', RoleViewSet, basename='role')

urlpatterns = [
    path('permissions', PermissionViewSet.as_view({'get': 'list'}), name='permission-list'),
    path('', include(router.urls)),
]
