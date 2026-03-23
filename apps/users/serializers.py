from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.roles.serializers import RoleSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone',
            'role', 'account_type', 'avatar', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'email', 'role', 'account_type', 'is_active', 'created_at', 'updated_at']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'avatar']


class CreateManagerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'phone']

    def create(self, validated_data):
        from apps.roles.models import Role

        role = Role.objects.get(name='manager', scope='platform')
        user = User.objects.create_user(role=role, **validated_data)
        return user


class UserListSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role_name', 'account_type', 'is_active', 'created_at']
