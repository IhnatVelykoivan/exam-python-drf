from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ListingViewSet

router = DefaultRouter(trailing_slash=False)
router.register('', ListingViewSet, basename='listing')

urlpatterns = [
    path('', include(router.urls)),
]
