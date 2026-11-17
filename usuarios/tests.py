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
