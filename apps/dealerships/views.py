from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Dealership
from .serializers import DealershipSerializer


class DealershipViewSet(viewsets.ModelViewSet):
    queryset = Dealership.objects.select_related('owner').all()
    serializer_class = DealershipSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAuthenticated()]
