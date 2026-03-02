from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CurrencyRate
from .serializers import CurrencyRateSerializer


class CurrencyRateView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 60 * 24))
    def get(self, request):
        # Get latest rate for each currency
        usd = CurrencyRate.objects.filter(ccy='USD').first()
        eur = CurrencyRate.objects.filter(ccy='EUR').first()
        rates = [r for r in [usd, eur] if r is not None]
        serializer = CurrencyRateSerializer(rates, many=True)
        return Response(serializer.data)
