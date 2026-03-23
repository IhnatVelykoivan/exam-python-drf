from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated

from core.permissions import HasPermission
from .models import Permission, Role
from .serializers import PermissionSerializer, RoleSerializer


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related('permissions').all()
    serializer_class = RoleSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission('can_manage_roles')()]


class PermissionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission('can_manage_roles')()]
