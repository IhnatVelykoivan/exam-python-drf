from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DealershipViewSet

router = DefaultRouter(trailing_slash=False)
router.register('', DealershipViewSet, basename='dealership')

urlpatterns = [
    path('', include(router.urls)),
]
