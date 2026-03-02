from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role_name = serializers.ChoiceField(choices=['buyer', 'seller'], write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'phone', 'role_name']

    def create(self, validated_data):
        from apps.roles.models import Role

        role_name = validated_data.pop('role_name')
        role = Role.objects.get(name=role_name, scope='platform')
        user = User.objects.create_user(
            role=role,
            **validated_data,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
