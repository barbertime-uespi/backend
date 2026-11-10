from django.db import models

from servicos.models import Servico
from usuarios.models import Barbeiro, Cliente


class Agendamento(models.Model):
    """Reserva de um atendimento. Regras de conflito (RN01-RN05) virão em etapa futura."""

    class Status(models.TextChoices):
        AGENDADO = 'agendado', 'Agendado'
        CONCLUIDO = 'concluido', 'Concluído'
        CANCELADO = 'cancelado', 'Cancelado'

    data = models.DateField()
    horario_inicio = models.TimeField()
    horario_fim = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AGENDADO,
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='agendamentos',
    )
    barbeiro = models.ForeignKey(
        Barbeiro,
        on_delete=models.CASCADE,
        related_name='agendamentos',
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        related_name='agendamentos',
    )

    def __str__(self):
        return f'{self.cliente} - {self.data} {self.horario_inicio}'
