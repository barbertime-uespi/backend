from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from agendamentos.models import Agendamento
from servicos.models import Servico
from usuarios.models import Barbeiro, Cliente


class AgendamentoSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    barbeiro_nome = serializers.CharField(source="barbeiro.nome", read_only=True)
    servico_nome = serializers.CharField(source="servico.nome", read_only=True)

    # Cliente pode ser informado pelo administrador. Para clientes comuns,
    # o perfil é sempre definido pelo usuário autenticado na validação.
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.select_related("user"),
        required=False,
    )

    class Meta:
        model = Agendamento
        fields = [
            "id",
            "cliente",
            "cliente_nome",
            "barbeiro",
            "barbeiro_nome",
            "servico",
            "servico_nome",
            "data",
            "horario_inicio",
            "horario_fim",
            "status",
        ]
        read_only_fields = ["horario_fim", "status"]

    @staticmethod
    def _eh_admin(user):
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))

    def _calcular_horario_fim(self, horario_inicio, servico):
        duracao = servico.duracao
        if not isinstance(duracao, timedelta) or duracao.total_seconds() <= 0:
            raise serializers.ValidationError(
                {"servico": "A duração do serviço deve ser maior que zero."}
            )

        inicio = datetime.combine(timezone.localdate(), horario_inicio)
        fim = inicio + duracao
        if fim.date() != inicio.date():
            raise serializers.ValidationError(
                {"horario_inicio": "O atendimento não pode ultrapassar a meia-noite."}
            )
        return fim.time()

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # Cliente autenticado nunca pode criar uma reserva em nome de outra pessoa.
        if user and user.is_authenticated and not self._eh_admin(user):
            try:
                attrs["cliente"] = user.cliente
            except Cliente.DoesNotExist:
                raise serializers.ValidationError(
                    {"cliente": "Somente clientes ou administradores podem criar agendamentos."}
                )
        elif self._eh_admin(user) and not attrs.get("cliente") and not self.instance:
            raise serializers.ValidationError(
                {"cliente": "O administrador deve informar o cliente do agendamento."}
            )

        cliente = attrs.get("cliente", getattr(self.instance, "cliente", None))
        barbeiro = attrs.get("barbeiro", getattr(self.instance, "barbeiro", None))
        servico = attrs.get("servico", getattr(self.instance, "servico", None))
        data = attrs.get("data", getattr(self.instance, "data", None))
        horario_inicio = attrs.get(
            "horario_inicio", getattr(self.instance, "horario_inicio", None)
        )

        if not all([cliente, barbeiro, servico, data, horario_inicio]):
            return attrs

        if not servico.ativo:
            raise serializers.ValidationError(
                {"servico": "Não é possível agendar um serviço inativo."}
            )

        if not barbeiro.ativo:
            raise serializers.ValidationError(
                {"barbeiro": "Não é possível agendar com um barbeiro inativo."}
            )

        if not barbeiro.servicos.filter(pk=servico.pk).exists():
            raise serializers.ValidationError(
                {"servico": "Este barbeiro não oferece o serviço selecionado."}
            )

        hoje = timezone.localdate()
        if data < hoje:
            raise serializers.ValidationError(
                {"data": "Não é possível criar agendamentos em datas passadas."}
            )
        if data == hoje:
            agora = timezone.localtime().replace(tzinfo=None).time()
            if horario_inicio <= agora:
                raise serializers.ValidationError(
                    {"horario_inicio": "Não é possível agendar em um horário que já passou."}
                )

        horario_fim = self._calcular_horario_fim(horario_inicio, servico)
        attrs["horario_fim"] = horario_fim

        agendamentos_mesmo_dia = Agendamento.objects.filter(data=data).exclude(
            status=Agendamento.Status.CANCELADO
        )
        if self.instance:
            agendamentos_mesmo_dia = agendamentos_mesmo_dia.exclude(pk=self.instance.pk)

        conflito_barbeiro = agendamentos_mesmo_dia.filter(
            barbeiro=barbeiro,
            horario_inicio__lt=horario_fim,
            horario_fim__gt=horario_inicio,
        ).exists()
        if conflito_barbeiro:
            raise serializers.ValidationError(
                "O barbeiro já possui um agendamento nesse intervalo de horário."
            )

        conflito_cliente = agendamentos_mesmo_dia.filter(
            cliente=cliente,
            horario_inicio__lt=horario_fim,
            horario_fim__gt=horario_inicio,
        ).exists()
        if conflito_cliente:
            raise serializers.ValidationError(
                "O cliente já possui outro agendamento nesse intervalo de horário."
            )

        return attrs
