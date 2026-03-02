from rest_framework import serializers


class ListingStatisticsSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()
    views = serializers.DictField()
    avg_price_region = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    avg_price_ukraine = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)


class ListingViewsSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()
    total = serializers.IntegerField()
    today = serializers.IntegerField()
    week = serializers.IntegerField()
    month = serializers.IntegerField()


class AvgPriceSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()
    avg_price_region = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    avg_price_ukraine = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    region_name = serializers.CharField()
