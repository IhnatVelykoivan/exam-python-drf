from django.urls import path

from .views import CurrencyRateView

urlpatterns = [
    path('rates', CurrencyRateView.as_view(), name='currency-rates'),
]
