from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.roles.permissions import IsAdmin, IsManagerOrAdmin
from core.permissions import HasPermission
from .models import BrandRequest, CarBrand, CarModel
from .serializers import (
    BrandRequestSerializer,
    BrandRequestUpdateSerializer,
    CarBrandSerializer,
    CarModelSerializer,
)

BRANDS_CACHE_KEY = 'car:brands:list'
MODELS_CACHE_PREFIX = 'car:models:list'


class CarBrandViewSet(viewsets.ModelViewSet):
    queryset = CarBrand.objects.all()
    serializer_class = CarBrandSerializer
    pagination_class = None  # small dataset — no pagination needed

    def list(self, request, *args, **kwargs):
        data = cache.get(BRANDS_CACHE_KEY)
        if data is None:
            response = super().list(request, *args, **kwargs)
            cache.set(BRANDS_CACHE_KEY, response.data, 60 * 60 * 24)
            return response
        return Response(data)

    def perform_create(self, serializer):
        serializer.save()
        _invalidate_car_caches()

    def perform_update(self, serializer):
        serializer.save()
        _invalidate_car_caches()

    def perform_destroy(self, instance):
        instance.delete()
        _invalidate_car_caches()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAuthenticated(), HasPermission('can_manage_brands')()]


class CarModelViewSet(viewsets.ModelViewSet):
    serializer_class = CarModelSerializer
    pagination_class = None  # small dataset — no pagination needed

    def get_queryset(self):
        return CarModel.objects.filter(brand_id=self.kwargs['brand_pk'])

    def list(self, request, *args, **kwargs):
        brand_pk = self.kwargs['brand_pk']
        cache_key = f'{MODELS_CACHE_PREFIX}:{brand_pk}'
        data = cache.get(cache_key)
        if data is None:
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, 60 * 60 * 24)
            return response
        return Response(data)

    def perform_create(self, serializer):
        serializer.save(brand_id=self.kwargs['brand_pk'])
        _invalidate_car_caches()

    def perform_update(self, serializer):
        serializer.save()
        _invalidate_car_caches()

    def perform_destroy(self, instance):
        instance.delete()
        _invalidate_car_caches()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAuthenticated(), HasPermission('can_manage_brands')()]


class BrandRequestViewSet(viewsets.ModelViewSet):
    queryset = BrandRequest.objects.select_related('user').all()

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return BrandRequestUpdateSerializer
        return BrandRequestSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        # When approved, create the brand and model in the catalog
        if instance.status == 'approved':
            brand, _ = CarBrand.objects.get_or_create(
                name=instance.brand_name,
                defaults={'is_active': True},
            )
            if instance.model_name:
                CarModel.objects.get_or_create(
                    brand=brand,
                    name=instance.model_name,
                    defaults={'is_active': True},
                )
            # Invalidate brand/model list caches
            _invalidate_car_caches()

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), HasPermission('can_request_brand')()]
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        if self.action == 'partial_update':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated(), IsAdmin()]


def _invalidate_car_caches():
    """Invalidate only car-related cache keys (brands list + all per-brand model lists)."""
    cache.delete(BRANDS_CACHE_KEY)
    brand_pks = list(CarBrand.objects.values_list('pk', flat=True))
    if brand_pks:
        cache.delete_many([f'{MODELS_CACHE_PREFIX}:{pk}' for pk in brand_pks])
