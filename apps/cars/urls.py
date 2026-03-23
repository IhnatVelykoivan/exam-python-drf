from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BrandRequestViewSet, CarBrandViewSet, CarModelViewSet

router = DefaultRouter(trailing_slash=False)
router.register('brands', CarBrandViewSet, basename='car-brand')
router.register('brand-requests', BrandRequestViewSet, basename='brand-request')

urlpatterns = [
    path('brands/<int:brand_pk>/models', CarModelViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='car-model-list'),
    path('brands/<int:brand_pk>/models/<int:pk>', CarModelViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='car-model-detail'),
    path('', include(router.urls)),
]
