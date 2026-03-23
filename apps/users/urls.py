from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserViewSet

router = DefaultRouter(trailing_slash=False)
router.register('', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
