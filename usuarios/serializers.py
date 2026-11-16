from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Barbeiro, Cliente

User = get_user_model()


class RegistroClienteSerializer(serializers.ModelSerializer):
    """Cria o User do Django e o perfil Cliente vinculado."""

    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Cliente
        fields = ['id', 'username', 'password', 'nome', 'email', 'telefone']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Este nome de usuário já está em uso.')
        return value

    def validate_email(self, value):
        if Cliente.objects.filter(email=value).exists() or User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        email = validated_data.get('email', '')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        cliente = Cliente.objects.create(user=user, **validated_data)
        return cliente


class ClienteSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Cliente
        fields = ['id', 'username', 'nome', 'email', 'telefone']


class BarbeiroSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Barbeiro
        fields = ['id', 'username', 'nome', 'email', 'telefone', 'ativo']