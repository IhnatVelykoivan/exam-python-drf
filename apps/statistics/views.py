from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listings.models import Listing
from .services import get_average_price_by_region, get_average_price_ukraine, get_listing_view_counts


class BaseStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_listing_or_error(self, request, listing_id):
        try:
            listing = Listing.objects.select_related('car_brand', 'car_model', 'region').get(id=listing_id)
        except Listing.DoesNotExist:
            return None, Response(
                {'detail': 'Listing not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check premium
        if request.user.account_type != 'premium' and not (request.user.role and request.user.role.name == 'admin'):
            return None, Response(
                {'detail': 'Premium account required for statistics'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check ownership (unless admin)
        if request.user.role and request.user.role.name != 'admin':
            if listing.seller_id != request.user.id:
                return None, Response(
                    {'detail': 'You can only view statistics for your own listings'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return listing, None


class ListingStatisticsView(BaseStatisticsView):
    def get(self, request, listing_id):
        listing, error = self.get_listing_or_error(request, listing_id)
        if error:
            return error

        views = get_listing_view_counts(listing)
        avg_region = get_average_price_by_region(listing)
        avg_ukraine = get_average_price_ukraine(listing)

        return Response({
            'listing_id': listing.id,
            'views': views,
            'avg_price_region': avg_region,
            'avg_price_ukraine': avg_ukraine,
        })


class ListingViewsView(BaseStatisticsView):
    def get(self, request, listing_id):
        listing, error = self.get_listing_or_error(request, listing_id)
        if error:
            return error

        views = get_listing_view_counts(listing)
        return Response({
            'listing_id': listing.id,
            **views,
        })


class AvgPriceView(BaseStatisticsView):
    def get(self, request, listing_id):
        listing, error = self.get_listing_or_error(request, listing_id)
        if error:
            return error

        avg_region = get_average_price_by_region(listing)
        avg_ukraine = get_average_price_ukraine(listing)

        return Response({
            'listing_id': listing.id,
            'avg_price_region': avg_region,
            'avg_price_ukraine': avg_ukraine,
            'region_name': listing.region.name,
        })
