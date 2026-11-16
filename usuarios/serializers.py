from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Cliente


class RegistroClienteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Cliente
        fields = ['id', 'nome', 'email', 'telefone', 'password']

    def validate_email(self, value):
        if Cliente.objects.filter(email=value).exists() or User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este e-mail já está sendo utilizado.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=password,
        )
        return Cliente.objects.create(user=user, **validated_data)


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nome', 'email', 'telefone']