from rest_framework import serializers

from .models import Dealership


class DealershipSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = Dealership
        fields = ['id', 'name', 'description', 'logo', 'address', 'owner', 'owner_email', 'is_active', 'created_at']
        read_only_fields = ['id', 'owner', 'owner_email', 'created_at']
