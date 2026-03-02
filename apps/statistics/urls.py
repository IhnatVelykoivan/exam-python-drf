from django.urls import path

from .views import AvgPriceView, ListingStatisticsView, ListingViewsView

urlpatterns = [
    path('listings/<int:listing_id>', ListingStatisticsView.as_view(), name='listing-statistics'),
    path('listings/<int:listing_id>/views', ListingViewsView.as_view(), name='listing-views'),
    path('listings/<int:listing_id>/avg-price', AvgPriceView.as_view(), name='listing-avg-price'),
]
