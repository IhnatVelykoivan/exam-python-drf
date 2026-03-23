from rest_framework import serializers

from .models import Listing


class ListingListSerializer(serializers.ModelSerializer):
    car_brand_name = serializers.CharField(source='car_brand.name', read_only=True)
    car_model_name = serializers.CharField(source='car_model.name', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'car_brand_name', 'car_model_name', 'year',
            'original_price', 'original_currency',
            'price_usd', 'price_eur', 'price_uah',
            'region_name', 'city', 'mileage', 'engine_type',
            'status', 'created_at',
        ]


class ListingDetailSerializer(serializers.ModelSerializer):
    car_brand_name = serializers.CharField(source='car_brand.name', read_only=True)
    car_model_name = serializers.CharField(source='car_model.name', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)
    seller_name = serializers.SerializerMethodField()
    seller_phone = serializers.CharField(source='seller.phone', read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'seller', 'seller_name', 'seller_phone',
            'car_brand', 'car_brand_name', 'car_model', 'car_model_name',
            'year', 'description',
            'original_price', 'original_currency',
            'price_usd', 'price_eur', 'price_uah',
            'rate_usd_uah', 'rate_eur_uah', 'rate_date',
            'region', 'region_name', 'city',
            'mileage', 'engine_type',
            'status', 'edit_attempts',
            'created_at', 'updated_at',
        ]

    def get_seller_name(self, obj):
        return f'{obj.seller.first_name} {obj.seller.last_name}'.strip()


class ListingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            'car_brand', 'car_model', 'year', 'description',
            'original_price', 'original_currency',
            'region', 'city', 'mileage', 'engine_type',
        ]

    def validate(self, attrs):
        car_brand = attrs.get('car_brand')
        car_model = attrs.get('car_model')
        if car_brand and car_model and car_model.brand_id != car_brand.id:
            raise serializers.ValidationError({
                'car_model': f'Model "{car_model.name}" does not belong to brand "{car_brand.name}".',
            })
        return attrs


class ListingEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = ['description']
