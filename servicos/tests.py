from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from servicos.models import Servico
from usuarios.models import Barbeiro

User = get_user_model()


class ServicoAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_servicos', password='senha123', is_staff=True
        )
        self.cliente_user = User.objects.create_user(
            username='cliente_servicos', password='senha123'
        )
        self.barbeiro_user = User.objects.create_user(
            username='barbeiro_servicos', password='senha123'
        )
        self.barbeiro = Barbeiro.objects.create(
            user=self.barbeiro_user,
            nome='Carlos',
            email='carlos@barbertime.test',
            telefone='11999990000',
            ativo=True,
        )
        self.servico = Servico.objects.create(
            nome='Corte tradicional',
            descricao='Corte masculino',
            preco=Decimal('35.00'),
            duracao=timedelta(minutes=30),
            ativo=True,
        )
        self.inativo = Servico.objects.create(
            nome='Barba antiga',
            descricao='Serviço indisponível',
            preco=Decimal('20.00'),
            duracao=timedelta(minutes=20),
            ativo=False,
        )
        self.lista_url = '/api/servicos/'
        self.detalhe_url = f'/api/servicos/{self.servico.pk}/'

    def dados_servico(self, **alteracoes):
        dados = {
            'nome': 'Corte + barba',
            'descricao': 'Atendimento completo',
            'preco': '55.00',
            'duracao': '01:00:00',
            'ativo': True,
            'barbeiros': [self.barbeiro.pk],
        }
        dados.update(alteracoes)
        return dados

    # RF04 — cadastro, edição e desativação restritos ao administrador.
    def test_administrador_cadastra_servico(self):
        self.client.force_authenticate(user=self.admin)
        resposta = self.client.post(
            self.lista_url, self.dados_servico(), format='json'
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertTrue(Servico.objects.filter(nome='Corte + barba').exists())

    def test_administrador_edita_servico(self):
        self.client.force_authenticate(user=self.admin)
        resposta = self.client.patch(
            self.detalhe_url, {'preco': '40.00'}, format='json'
        )
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.servico.refresh_from_db()
        self.assertEqual(self.servico.preco, Decimal('40.00'))

    def test_administrador_desativa_servico_por_patch(self):
        self.client.force_authenticate(user=self.admin)
        resposta = self.client.patch(
            self.detalhe_url, {'ativo': False}, format='json'
        )
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.servico.refresh_from_db()
        self.assertFalse(self.servico.ativo)

    def test_delete_desativa_sem_apagar_registro(self):
        self.client.force_authenticate(user=self.admin)
        resposta = self.client.delete(self.detalhe_url)
        self.assertEqual(resposta.status_code, 204)
        self.assertTrue(Servico.objects.filter(pk=self.servico.pk).exists())
        self.servico.refresh_from_db()
        self.assertFalse(self.servico.ativo)

    def test_cliente_nao_pode_cadastrar_servico(self):
        self.client.force_authenticate(user=self.cliente_user)
        resposta = self.client.post(
            self.lista_url, self.dados_servico(), format='json'
        )
        self.assertEqual(resposta.status_code, 403)

    def test_barbeiro_nao_pode_cadastrar_servico(self):
        self.client.force_authenticate(user=self.barbeiro_user)
        resposta = self.client.post(
            self.lista_url, self.dados_servico(), format='json'
        )
        self.assertEqual(resposta.status_code, 403)

    def test_visitante_nao_pode_cadastrar_servico(self):
        resposta = self.client.post(
            self.lista_url, self.dados_servico(), format='json'
        )
        self.assertEqual(resposta.status_code, 401)

    # RF05 — consulta pública dos serviços disponíveis e seus dados.
    def test_visitante_consulta_apenas_servicos_ativos(self):
        resposta = self.client.get(self.lista_url)
        self.assertEqual(resposta.status_code, 200)
        nomes = [item['nome'] for item in resposta.data]
        self.assertIn('Corte tradicional', nomes)
        self.assertNotIn('Barba antiga', nomes)

    def test_cliente_consulta_servicos_ativos(self):
        self.client.force_authenticate(user=self.cliente_user)
        resposta = self.client.get(self.lista_url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([item['nome'] for item in resposta.data], ['Corte tradicional'])

    def test_resposta_contem_preco_e_duracao(self):
        resposta = self.client.get(self.detalhe_url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data['preco'], '35.00')
        self.assertEqual(resposta.data['duracao'], '00:30:00')

    def test_visitante_nao_acessa_detalhe_de_servico_inativo(self):
        resposta = self.client.get(f'/api/servicos/{self.inativo.pk}/')
        self.assertEqual(resposta.status_code, 404)

    def test_administrador_visualiza_servicos_inativos(self):
        self.client.force_authenticate(user=self.admin)
        resposta = self.client.get(self.lista_url)
        self.assertEqual(resposta.status_code, 200)
        nomes = [item['nome'] for item in resposta.data]
        self.assertIn('Barba antiga', nomes)


@override_settings(
    CORS_ALLOWED_ORIGINS=['http://localhost:5173'],
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'corsheaders.middleware.CorsMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ],
)
class CorsConfigurationTests(TestCase):
    def test_preflight_de_origem_permitida_recebe_cabecalho_cors(self):
        resposta = self.client.options(
            '/api/servicos/',
            HTTP_ORIGIN='http://localhost:5173',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
        )
        self.assertEqual(
            resposta.headers.get('Access-Control-Allow-Origin'),
            'http://localhost:5173',
        )
