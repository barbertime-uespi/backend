from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
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
            email="barbeiro@teste.com",
            telefone="86988888888",
        )

        self.servico = Servico.objects.create(
            nome="Corte",
            duracao=timedelta(minutes=45),
            preco="30.00",
            ativo=True,
        )
        self.barbeiro.servicos.add(self.servico)

        self.data_alvo = timezone.localdate() + timedelta(days=2)
        self.client.force_authenticate(user=self.user_cliente)

    def criar_agendamento(self, **kwargs):
        dados = {
            "cliente": self.cliente,
            "barbeiro": self.barbeiro,
            "servico": self.servico,
            "data": self.data_alvo,
            "horario_inicio": time(9, 0),
            "horario_fim": time(9, 45),
            "status": Agendamento.Status.AGENDADO,
        }
        dados.update(kwargs)
        return Agendamento.objects.create(**dados)

    def payload(self, **kwargs):
        dados = {
            "cliente": self.cliente.id,
            "barbeiro": self.barbeiro.id,
            "servico": self.servico.id,
            "data": self.data_alvo.isoformat(),
            "horario_inicio": "10:00:00",
        }
        dados.update(kwargs)
        return dados

    def test_consulta_horarios_disponiveis_remove_ocupado(self):
        self.criar_agendamento(horario_inicio=time(9, 0), horario_fim=time(9, 45))
        response = self.client.get(
            reverse("agendamentos:disponiveis"),
            {"barbeiro_id": self.barbeiro.id, "data": self.data_alvo.isoformat()},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("09:00", response.data["horarios_disponiveis"])
        self.assertIn("08:00", response.data["horarios_disponiveis"])

    def test_disponiveis_rejeita_barbeiro_id_nao_numerico(self):
        response = self.client.get(
            reverse("agendamentos:disponiveis"),
            {"barbeiro_id": "abc", "data": self.data_alvo.isoformat()},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disponiveis_rejeita_barbeiro_inexistente(self):
        response = self.client.get(
            reverse("agendamentos:disponiveis"),
            {"barbeiro_id": 999999, "data": self.data_alvo.isoformat()},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cliente_lista_apenas_seus_agendamentos_com_nomes(self):
        proprio = self.criar_agendamento()
        outro_user = User.objects.create_user(
            username="outro@teste.com", password="senha123"
        )
        outro_cliente = Cliente.objects.create(
            user=outro_user,
            nome="Outro Cliente",
            email="outro@teste.com",
            telefone="86977777777",
        )
        self.criar_agendamento(
            cliente=outro_cliente,
            horario_inicio=time(11, 0),
            horario_fim=time(11, 45),
        )

        response = self.client.get("/api/agendamentos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], proprio.id)
        self.assertEqual(response.data[0]["cliente_nome"], "Cliente Teste")
        self.assertEqual(response.data[0]["barbeiro_nome"], "Barbeiro Teste")
        self.assertEqual(response.data[0]["servico_nome"], "Corte")

    def test_barbeiro_lista_apenas_sua_agenda(self):
        proprio = self.criar_agendamento()
        outro_barbeiro_user = User.objects.create_user(
            username="barbeiro2@teste.com", password="senha123"
        )
        outro_barbeiro = Barbeiro.objects.create(
            user=outro_barbeiro_user,
            nome="Outro Barbeiro",
            email="barbeiro2@teste.com",
            telefone="86966666666",
        )
        outro_barbeiro.servicos.add(self.servico)
        outro = self.criar_agendamento(
            barbeiro=outro_barbeiro,
            horario_inicio=time(11, 0),
            horario_fim=time(11, 45),
        )

        self.client.force_authenticate(user=self.user_barbeiro)
        response = self.client.get("/api/agendamentos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [proprio.id])
        self.assertNotIn(outro.id, [item["id"] for item in response.data])

    def test_calcula_horario_fim_pela_duracao_real_do_servico(self):
        response = self.client.post(
            "/api/agendamentos/",
            self.payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["horario_fim"], "10:45:00")

    def test_cliente_nao_consegue_agendar_em_nome_de_outro(self):
        outro_user = User.objects.create_user(
            username="terceiro@teste.com", password="senha123"
        )
        outro_cliente = Cliente.objects.create(
            user=outro_user,
            nome="Terceiro",
            email="terceiro@teste.com",
            telefone="86955555555",
        )
        response = self.client.post(
            "/api/agendamentos/",
            self.payload(cliente=outro_cliente.id),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["cliente"], self.cliente.id)

    def test_bloqueia_conflito_horario_barbeiro(self):
        self.criar_agendamento(horario_inicio=time(10, 0), horario_fim=time(10, 45))
        response = self.client.post(
            "/api/agendamentos/", self.payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bloqueia_conflito_de_horario_do_cliente_com_outro_barbeiro(self):
        outro_user = User.objects.create_user(
            username="barbeiro3@teste.com", password="senha123"
        )
        outro_barbeiro = Barbeiro.objects.create(
            user=outro_user,
            nome="Terceiro Barbeiro",
            email="barbeiro3@teste.com",
            telefone="86944444444",
        )
        outro_barbeiro.servicos.add(self.servico)
        self.criar_agendamento(
            barbeiro=outro_barbeiro,
            horario_inicio=time(10, 0),
            horario_fim=time(10, 45),
        )

        response = self.client.post(
            "/api/agendamentos/", self.payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bloqueia_servico_nao_oferecido_pelo_barbeiro(self):
        outro_servico = Servico.objects.create(
            nome="Barba",
            duracao=timedelta(minutes=30),
            preco="20.00",
            ativo=True,
        )
        response = self.client.post(
            "/api/agendamentos/",
            self.payload(servico=outro_servico.id),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bloqueia_data_passada(self):
        data_passada = timezone.localdate() - timedelta(days=1)
        response = self.client.post(
            "/api/agendamentos/",
            self.payload(data=data_passada.isoformat()),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelar_agendamento_concluido_e_bloqueado(self):
        agendamento = self.criar_agendamento(status=Agendamento.Status.CONCLUIDO)
        response = self.client.patch(
            reverse("agendamentos:cancelar-agendamento", kwargs={"pk": agendamento.pk}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concluir_bloqueia_agendamento_cancelado(self):
        agendamento = self.criar_agendamento(status=Agendamento.Status.CANCELADO)
        self.client.force_authenticate(user=self.user_barbeiro)
        response = self.client.patch(
            reverse("agendamentos:concluir-agendamento", kwargs={"pk": agendamento.pk}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
