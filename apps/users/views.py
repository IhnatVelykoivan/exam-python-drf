from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.roles.permissions import IsAdmin, IsManagerOrAdmin
from core.permissions import HasPermission
from .serializers import (
    CreateManagerSerializer,
    ProfileUpdateSerializer,
    UserListSerializer,
    UserSerializer,
)

User = get_user_model()


class UserViewSet(GenericViewSet):
    queryset = User.objects.select_related('role').all()

    def get_serializer_class(self):
        if self.action == 'create_manager':
            return CreateManagerSerializer
        if self.action in ('list', 'retrieve'):
            return UserListSerializer
        if self.action == 'update_me':
            return ProfileUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @me.mapping.patch
    def update_me(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    def list(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = UserListSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        user = self.get_object()
        serializer = UserSerializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='create-manager')
    def create_manager(self, request):
        serializer = CreateManagerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='ban')
    def ban(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'detail': f'User {user.email} has been banned'})

    @action(detail=True, methods=['patch'], url_path='unban')
    def unban(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': f'User {user.email} has been unbanned'})

    @action(detail=False, methods=['post'], url_path='upgrade-premium')
    def upgrade_premium(self, request):
        user = request.user
        if not user.role or user.role.name != 'seller':
            return Response(
                {'detail': 'Only sellers can upgrade to premium'},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.account_type = 'premium'
        user.save(update_fields=['account_type'])
        return Response({'detail': 'Account upgraded to premium', 'account_type': 'premium'})

    def get_permissions(self):
        if self.action in ('me', 'update_me'):
            return [IsAuthenticated()]
        if self.action == 'upgrade_premium':
            return [IsAuthenticated()]
        if self.action == 'create_manager':
            return [IsAuthenticated(), IsAdmin()]
        if self.action in ('list', 'retrieve', 'ban', 'unban'):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated()]
