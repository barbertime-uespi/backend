from datetime import datetime, timedelta
from rest_framework import serializers
from .models import Agendamento


class AgendamentoSerializer(serializers.ModelSerializer):
    """Calcula horario_fim pela duracao do servico e valida conflitos (RF07, RF08, RN01, RN02)."""

    class Meta:
        model = Agendamento
        fields = [
            'id',
            'cliente',
            'barbeiro',
            'servico',
            'data',
            'horario_inicio',
            'horario_fim',
            'status',
        ]
        read_only_fields = ['horario_fim', 'status']

    def _calcular_horario_fim(self, horario_inicio, servico):
        # Ajuste o nome do atributo de duracao (ex.: duracao_minutos) conforme servicos/models.py
        duracao_minutos = getattr(servico, 'duracao_minutos', 30)
        base_dt = datetime.combine(datetime.today().date(), horario_inicio)
        fim_dt = base_dt + timedelta(minutes=duracao_minutos)
        return fim_dt.time()

    def validate(self, attrs):
        cliente = attrs.get('cliente')
        barbeiro = attrs.get('barbeiro')
        servico = attrs.get('servico')
        data = attrs.get('data')
        horario_inicio = attrs.get('horario_inicio')

        if self.instance:
            cliente = cliente or self.instance.cliente
            barbeiro = barbeiro or self.instance.barbeiro
            servico = servico or self.instance.servico
            data = data or self.instance.data
            horario_inicio = horario_inicio or self.instance.horario_inicio

        if not all([barbeiro, servico, data, horario_inicio]):
            return attrs

        horario_fim = self._calcular_horario_fim(horario_inicio, servico)
        attrs['horario_fim'] = horario_fim

        # Ignora cancelados ao verificar sobreposicao de horario
        agendamentos_mesmo_dia = Agendamento.objects.filter(data=data).exclude(status='cancelado')
        if self.instance:
            agendamentos_mesmo_dia = agendamentos_mesmo_dia.exclude(pk=self.instance.pk)

        # RN01: Bloqueia conflito de horario com outro agendamento do mesmo barbeiro
        conflito_barbeiro = agendamentos_mesmo_dia.filter(
            barbeiro=barbeiro,
            horario_inicio__lt=horario_fim,
            horario_fim__gt=horario_inicio,
        ).exists()
        if conflito_barbeiro:
            raise serializers.ValidationError(
                "O barbeiro ja possui um agendamento nesse intervalo de horario."
            )

        # RN02: Bloqueia agendamento simultaneo para o mesmo cliente
        if cliente is not None:
            conflito_cliente = agendamentos_mesmo_dia.filter(
                cliente=cliente,
                horario_inicio__lt=horario_fim,
                horario_fim__gt=horario_inicio,
            ).exists()
            if conflito_cliente:
                raise serializers.ValidationError(
                    "O cliente ja possui outro agendamento nesse intervalo de horario."
                )

        return attrs