from rest_framework import serializers

from .models import BrandRequest, CarBrand, CarModel


class CarBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarBrand
        fields = ['id', 'name', 'is_active']


class CarModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarModel
        fields = ['id', 'brand', 'name', 'is_active']
        read_only_fields = ['brand']


class BrandRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = BrandRequest
        fields = ['id', 'user', 'user_email', 'brand_name', 'model_name', 'status', 'admin_comment', 'created_at']
        read_only_fields = ['id', 'user', 'user_email', 'status', 'created_at']


class BrandRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandRequest
        fields = ['status', 'admin_comment']
