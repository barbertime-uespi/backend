from rest_framework import serializers

from usuarios.models import Barbeiro
from usuarios.serializers import BarbeiroSerializer
from .models import Servico


class ServicoSerializer(serializers.ModelSerializer):
    barbeiros_detalhes = BarbeiroSerializer(source='barbeiros', many=True, read_only=True)
    barbeiros = serializers.PrimaryKeyRelatedField(
        queryset=Barbeiro.objects.filter(ativo=True),
        many=True,
        required=False,
    )

    class Meta:
        model = Servico
        fields = [
            'id',
            'nome',
            'descricao',
            'preco',
            'duracao',
            'ativo',
            'barbeiros',
            'barbeiros_detalhes',
        ]