from django.db import models

from usuarios.models import Barbeiro


class Servico(models.Model):
    """Serviço oferecido pela barbearia (ex.: corte, barba)."""

    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    duracao = models.DurationField(help_text='Duração estimada do atendimento.')
    ativo = models.BooleanField(default=True)

    # Relação N:N (tabela Barbeiro_Servico do modelo conceitual).
    barbeiros = models.ManyToManyField(
        Barbeiro,
        related_name='servicos',
        blank=True,
    )

    def __str__(self):
        return self.nome
