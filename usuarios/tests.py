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
