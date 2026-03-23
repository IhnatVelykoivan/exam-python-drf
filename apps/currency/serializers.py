from rest_framework import serializers

from .models import CurrencyRate


class CurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = ['id', 'ccy', 'base_ccy', 'buy', 'sale', 'fetched_at']
