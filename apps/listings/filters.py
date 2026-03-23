import django_filters

from .models import Listing


class ListingFilter(django_filters.FilterSet):
    car_brand = django_filters.NumberFilter(field_name='car_brand_id')
    car_model = django_filters.NumberFilter(field_name='car_model_id')
    region = django_filters.NumberFilter(field_name='region_id')
    price_min = django_filters.NumberFilter(field_name='price_usd', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price_usd', lookup_expr='lte')
    year_min = django_filters.NumberFilter(field_name='year', lookup_expr='gte')
    year_max = django_filters.NumberFilter(field_name='year', lookup_expr='lte')
    engine_type = django_filters.CharFilter(field_name='engine_type')

    class Meta:
        model = Listing
        fields = ['car_brand', 'car_model', 'region', 'engine_type']
