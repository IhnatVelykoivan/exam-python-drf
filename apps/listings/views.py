from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.roles.permissions import IsManagerOrAdmin
from core.permissions import HasPermission, IsOwnerOrReadOnly
from .filters import ListingFilter
from .models import Listing
from .serializers import (
    ListingCreateSerializer,
    ListingDetailSerializer,
    ListingEditSerializer,
    ListingListSerializer,
)
from .services import can_create_listing, process_listing_creation, process_listing_edit
from apps.notifications.services import notify_seller_listing_deactivated


class ListingViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_class = ListingFilter

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Record view for statistics
        from apps.statistics.services import record_view
        record_view(instance, request)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_queryset(self):
        user = self.request.user

        if self.action == 'my':
            return Listing.objects.filter(seller=user).select_related(
                'car_brand', 'car_model', 'region', 'seller',
            )
        if self.action == 'pending':
            return Listing.objects.filter(
                status__in=['needs_edit', 'inactive'],
            ).select_related('car_brand', 'car_model', 'region', 'seller')
        # Default: show active listings to everyone, plus needs_edit/inactive to author/manager/admin
        if user.is_authenticated and user.role and user.role.name in ('manager', 'admin'):
            return Listing.objects.all().select_related(
                'car_brand', 'car_model', 'region', 'seller',
            )
        if user.is_authenticated:
            return Listing.objects.filter(
                status='active',
            ).select_related(
                'car_brand', 'car_model', 'region', 'seller',
            ) | Listing.objects.filter(
                seller=user,
            ).select_related(
                'car_brand', 'car_model', 'region', 'seller',
            )
        return Listing.objects.filter(
            status='active',
        ).select_related(
            'car_brand', 'car_model', 'region', 'seller',
        )
    def get_serializer_class(self):
        if self.action == 'create':
            return ListingCreateSerializer
        if self.action == 'partial_update':
            return ListingEditSerializer
        if self.action in ('retrieve',):
            return ListingDetailSerializer
        return ListingListSerializer

    def create(self, request, *args, **kwargs):
        if not can_create_listing(request.user):
            return Response(
                {'detail': 'Basic account can have only 1 active listing. Upgrade to premium.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save(seller=request.user)
        listing = process_listing_creation(listing)
        return Response(
            ListingDetailSerializer(listing).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        listing = self.get_object()
        description = request.data.get('description')

        # Block edits on inactive listings (profanity attempts exhausted)
        if listing.status == 'inactive':
            return Response(
                {'detail': 'Listing is inactive. Only a manager or admin can reactivate it.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if listing.status == 'needs_edit' and listing.edit_attempts >= 3:
            return Response(
                {'detail': 'Edit attempts exhausted. Listing is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if description:
            listing = process_listing_edit(listing, description)
            if listing is None:
                return Response(
                    {'detail': 'Edit attempts exhausted.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(ListingDetailSerializer(listing).data)

        serializer = self.get_serializer(listing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ListingDetailSerializer(listing).data)

    @action(detail=False, methods=['get'], url_path='my')
    def my(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ListingListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ListingListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ListingListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ListingListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        listing = self.get_object()
        listing.status = 'inactive'
        listing.save(update_fields=['status'])
        notify_seller_listing_deactivated(listing, manager=request.user)
        return Response({'detail': 'Listing deactivated'})

    @action(detail=True, methods=['patch'], url_path='activate')
    def activate(self, request, pk=None):
        listing = self.get_object()
        listing.status = 'active'
        listing.save(update_fields=['status'])
        return Response({'detail': 'Listing activated'})

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated(), HasPermission('can_create_listing')()]
        if self.action == 'partial_update':
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        if self.action in ('my',):
            return [IsAuthenticated()]
        if self.action in ('pending', 'deactivate', 'activate'):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated()]
