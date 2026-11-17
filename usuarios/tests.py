from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class LogoutTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='joao', password='senha123')

    def test_logout_invalida_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.force_authenticate(user=self.user)

        resp = self.client.post(
            '/api/token/logout/', {'refresh': str(refresh)}, format='json'
        )
        self.assertEqual(resp.status_code, 205)

        # O refresh usado não pode mais gerar novo access token.
        refresh_resp = self.client.post(
            '/api/token/refresh/', {'refresh': str(refresh)}, format='json'
        )
        self.assertEqual(refresh_resp.status_code, 401)

    def test_logout_sem_refresh_retorna_400(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/token/logout/', {}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_logout_exige_autenticacao(self):
        resp = self.client.post('/api/token/logout/', {}, format='json')
        self.assertEqual(resp.status_code, 401)


from django.test import TestCase

from usuarios.models import Barbeiro
from usuarios.serializers import RegistroBarbeiroSerializer


class RegistroBarbeiroSerializerTests(TestCase):
    def test_cria_user_e_barbeiro_com_senha_hash(self):
        data = {
            'username': 'roberto',
            'password': 'senha123',
            'nome': 'Roberto',
            'email': 'roberto@ex.com',
            'telefone': '11999998888',
            'ativo': True,
        }
        serializer = RegistroBarbeiroSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        barbeiro = serializer.save()

        self.assertIsInstance(barbeiro, Barbeiro)
        self.assertEqual(barbeiro.nome, 'Roberto')
        self.assertEqual(barbeiro.user.username, 'roberto')
        self.assertTrue(barbeiro.user.check_password('senha123'))

    def test_username_duplicado_invalido(self):
        User.objects.create_user(username='roberto', password='x')
        serializer = RegistroBarbeiroSerializer(data={
            'username': 'roberto', 'password': 'senha123', 'nome': 'R',
            'email': 'r@ex.com', 'telefone': '1', 'ativo': True,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)


class BarbeiroAdminAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='x', is_staff=True
        )
        self.cliente_user = User.objects.create_user(username='cli', password='x')

    def test_admin_cria_barbeiro(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'username': 'barb1', 'password': 'senha123', 'nome': 'Rob',
            'email': 'rob@ex.com', 'telefone': '11988887777', 'ativo': True,
        }
        resp = self.client.post('/api/admin/barbeiros/', data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(username='barb1').exists())
        self.assertTrue(Barbeiro.objects.filter(nome='Rob').exists())

    def test_cliente_nao_acessa_gestao(self):
        self.client.force_authenticate(user=self.cliente_user)
        resp = self.client.get('/api/admin/barbeiros/')
        self.assertEqual(resp.status_code, 403)

    def test_nao_autenticado_recebe_401(self):
        resp = self.client.get('/api/admin/barbeiros/')
        self.assertEqual(resp.status_code, 401)

    def test_delete_faz_soft_delete(self):
        self.client.force_authenticate(user=self.admin)
        user = User.objects.create_user(username='barb2', password='x')
        barbeiro = Barbeiro.objects.create(
            user=user, nome='Ana', email='ana@ex.com', telefone='1', ativo=True
        )
        resp = self.client.delete(f'/api/admin/barbeiros/{barbeiro.id}/')
        self.assertEqual(resp.status_code, 204)
        barbeiro.refresh_from_db()
        self.assertFalse(barbeiro.ativo)

    def test_admin_lista_inclui_inativos(self):
        self.client.force_authenticate(user=self.admin)
        user = User.objects.create_user(username='barb3', password='x')
        Barbeiro.objects.create(
            user=user, nome='Zé', email='ze@ex.com', telefone='1', ativo=False
        )
        resp = self.client.get('/api/admin/barbeiros/')
        self.assertEqual(resp.status_code, 200)
        nomes = [b['nome'] for b in resp.json()]
        self.assertIn('Zé', nomes)
