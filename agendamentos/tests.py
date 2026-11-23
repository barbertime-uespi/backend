from datetime import date, time, timedelta
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from agendamentos.models import Agendamento
from servicos.models import Servico
from usuarios.models import Barbeiro, Cliente


class AgendamentoTests(APITestCase):
    def setUp(self):
        self.user_cliente = User.objects.create_user(
            username="cliente@teste.com",
            email="cliente@teste.com",
            password="senha123",
        )
        self.cliente = Cliente.objects.create(
            user=self.user_cliente,
            nome="Cliente Teste",
            email="cliente@teste.com",
            telefone="86999999999",
        )

        self.user_barbeiro = User.objects.create_user(
            username="barbeiro@teste.com",
            email="barbeiro@teste.com",
            password="senha123",
        )
        self.barbeiro = Barbeiro.objects.create(
            user=self.user_barbeiro,
            nome="Barbeiro Teste",
        )

        self.servico = Servico.objects.create(
            nome="Corte",
            duracao=timedelta(minutes=30),
            preco="30.00",
            ativo=True,
        )
        self.data_alvo = date(2026, 11, 25)
        self.client.force_authenticate(user=self.user_cliente)

    def test_consulta_horarios_disponiveis_remove_ocupado(self):
        Agendamento.objects.create(
            cliente=self.cliente,
            barbeiro=self.barbeiro,
            servico=self.servico,
            data=self.data_alvo,
            horario_inicio=time(9, 0),
            horario_fim=time(9, 30),
            status=Agendamento.Status.AGENDADO,
        )

        url = reverse("agendamentos:disponiveis")
        response = self.client.get(
            url,
            {"barbeiro_id": self.barbeiro.id, "data": self.data_alvo.isoformat()},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("09:00", response.data.get("horarios_disponiveis", []))
        self.assertIn("08:00", response.data.get("horarios_disponiveis", []))

    def test_bloqueia_conflito_horario_barbeiro(self):
        Agendamento.objects.create(
            cliente=self.cliente,
            barbeiro=self.barbeiro,
            servico=self.servico,
            data=self.data_alvo,
            horario_inicio=time(9, 0),
            horario_fim=time(9, 30),
            status=Agendamento.Status.AGENDADO,
        )

        url = "/api/agendamentos/"
        payload = {
            "cliente": self.cliente.id,
            "barbeiro": self.barbeiro.id,
            "servico": self.servico.id,
            "data": self.data_alvo.isoformat(),
            "horario_inicio": "09:00:00",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concluir_bloqueia_agendamento_cancelado(self):
        agendamento = Agendamento.objects.create(
            cliente=self.cliente,
            barbeiro=self.barbeiro,
            servico=self.servico,
            data=self.data_alvo,
            horario_inicio=time(10, 0),
            horario_fim=time(10, 30),
            status=Agendamento.Status.CANCELADO,
        )

        self.client.force_authenticate(user=self.user_barbeiro)
        url = reverse("agendamentos:concluir-agendamento", kwargs={"pk": agendamento.pk})
        response = self.client.patch(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)