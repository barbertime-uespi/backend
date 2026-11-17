# US02 (logout) + US03 (gerenciamento de barbeiros) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar a pendência de logout da US02 (RF02) e implementar o CRUD de barbeiros da US03 (RF03), restrito ao administrador, expondo rotas completas para o front.

**Architecture:** Logout via blacklist de refresh token do SimpleJWT (app `token_blacklist` + rotação). Gestão de barbeiros via `ModelViewSet` admin-only que cria `User`+`Barbeiro` no cadastro e faz soft delete (`ativo=False`) no destroy. Segue os padrões já existentes em `usuarios/` (serializer que cria User+perfil em transação atômica).

**Tech Stack:** Django, Django REST Framework, `djangorestframework-simplejwt`, SQLite, `APITestCase`.

## Global Constraints

- Permissão padrão global é `IsAuthenticated` (`REST_FRAMEWORK` em `barbertime/settings.py`).
- Autenticação por JWT (`rest_framework_simplejwt`).
- Senhas sempre via `User.objects.create_user` (hash — RNF02).
- Criação de User+perfil sempre em `@transaction.atomic`.
- Todos os comandos Python rodam com o venv do projeto: `./venv/bin/python manage.py ...`.
- Rodar a suíte com: `./venv/bin/python manage.py test usuarios -v 2`.

---

### Task 1: US02 — Logout via blacklist de refresh token

**Files:**
- Modify: `barbertime/settings.py` (INSTALLED_APPS + bloco SIMPLE_JWT)
- Modify: `usuarios/views.py` (nova `LogoutView`)
- Modify: `barbertime/urls.py` (rota de logout)
- Test: `usuarios/tests.py`

**Interfaces:**
- Produces: `LogoutView` (APIView) em `usuarios/views.py`; rota nomeada `token_logout` → `POST /api/token/logout/` body `{"refresh": "<token>"}`.

- [ ] **Step 1: Habilitar o app de blacklist e a rotação de tokens**

Em `barbertime/settings.py`, no `INSTALLED_APPS`, adicionar a linha logo após `'rest_framework_simplejwt',`:

```python
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
```

E substituir o bloco `SIMPLE_JWT` por:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

- [ ] **Step 2: Aplicar as migrations do token_blacklist**

Run: `./venv/bin/python manage.py migrate`
Expected: aplica migrations de `token_blacklist` (`Applying token_blacklist.0001_initial... OK` etc.), sem erros.

- [ ] **Step 3: Escrever os testes de logout (falhando)**

Em `usuarios/tests.py`, substituir todo o conteúdo por:

```python
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
```

- [ ] **Step 4: Rodar os testes para ver falhar**

Run: `./venv/bin/python manage.py test usuarios.tests.LogoutTests -v 2`
Expected: FAIL (404 nas rotas de logout — `LogoutView` e rota ainda não existem).

- [ ] **Step 5: Implementar a LogoutView**

Em `usuarios/views.py`, acrescentar os imports e a classe ao final do arquivo:

```python
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class LogoutView(APIView):
    """RF02: logout real invalidando o refresh token (blacklist)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response(
                {'detail': 'O campo "refresh" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except TokenError:
            return Response(
                {'detail': 'Token inválido ou expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)
```

(`status`, `IsAuthenticated`, `APIView` e `Response` já estão importados no topo do arquivo.)

- [ ] **Step 6: Registrar a rota de logout**

Em `barbertime/urls.py`, adicionar o import e a rota. Após os imports do simplejwt:

```python
from usuarios.views import LogoutView
```

E no `urlpatterns`, logo após a linha de `token/refresh/`:

```python
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/logout/', LogoutView.as_view(), name='token_logout'),
```

- [ ] **Step 7: Rodar os testes para ver passar**

Run: `./venv/bin/python manage.py test usuarios.tests.LogoutTests -v 2`
Expected: PASS (3 testes).

- [ ] **Step 8: Commit**

```bash
git add barbertime/settings.py barbertime/urls.py usuarios/views.py usuarios/tests.py
git commit -m "feat(usuarios): logout via blacklist de refresh token (US02/RF02)"
```

---

### Task 2: US03 — Serializer de cadastro de barbeiro

**Files:**
- Modify: `usuarios/serializers.py` (nova `RegistroBarbeiroSerializer`)
- Test: `usuarios/tests.py`

**Interfaces:**
- Consumes: `Barbeiro` model, `User = get_user_model()` (já no topo do arquivo).
- Produces: `RegistroBarbeiroSerializer` — campos `id, username(w/o), password(w/o), nome, email, telefone, ativo`; `.save()` cria `User`+`Barbeiro` e retorna a instância `Barbeiro`.

- [ ] **Step 1: Escrever o teste do serializer (falhando)**

Em `usuarios/tests.py`, adicionar ao final do arquivo:

```python
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
```

- [ ] **Step 2: Rodar o teste para ver falhar**

Run: `./venv/bin/python manage.py test usuarios.tests.RegistroBarbeiroSerializerTests -v 2`
Expected: FAIL com `ImportError: cannot import name 'RegistroBarbeiroSerializer'`.

- [ ] **Step 3: Implementar o serializer**

Em `usuarios/serializers.py`, adicionar ao final do arquivo (após `BarbeiroSerializer`):

```python
class RegistroBarbeiroSerializer(serializers.ModelSerializer):
    """US03/RF03: cria o User do Django e o perfil Barbeiro vinculado."""

    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Barbeiro
        fields = ['id', 'username', 'password', 'nome', 'email', 'telefone', 'ativo']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Este nome de usuário já está em uso.')
        return value

    def validate_email(self, value):
        if Barbeiro.objects.filter(email=value).exists() or User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        email = validated_data.get('email', '')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        return Barbeiro.objects.create(user=user, **validated_data)
```

(`transaction`, `serializers`, `Barbeiro` e `User` já estão importados no topo do arquivo.)

- [ ] **Step 4: Rodar o teste para ver passar**

Run: `./venv/bin/python manage.py test usuarios.tests.RegistroBarbeiroSerializerTests -v 2`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add usuarios/serializers.py usuarios/tests.py
git commit -m "feat(usuarios): RegistroBarbeiroSerializer cria User+Barbeiro (US03)"
```

---

### Task 3: US03 — ViewSet admin de barbeiros + rotas

**Files:**
- Modify: `usuarios/views.py` (nova `BarbeiroViewSet`)
- Modify: `usuarios/urls.py` (router `admin/barbeiros`)
- Test: `usuarios/tests.py`

**Interfaces:**
- Consumes: `RegistroBarbeiroSerializer`, `BarbeiroSerializer`, `Barbeiro`.
- Produces: rotas `GET·POST /api/admin/barbeiros/` e `GET·PUT·PATCH·DELETE /api/admin/barbeiros/{id}/` (admin only; DELETE = soft delete).

- [ ] **Step 1: Escrever os testes da API admin (falhando)**

Em `usuarios/tests.py`, adicionar ao final do arquivo:

```python
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
```

Garantir que o topo de `usuarios/tests.py` tem os imports usados por estes testes: `from rest_framework.test import APITestCase`, `from usuarios.models import Barbeiro`, `User = get_user_model()` (já presentes das tasks anteriores).

- [ ] **Step 2: Rodar os testes para ver falhar**

Run: `./venv/bin/python manage.py test usuarios.tests.BarbeiroAdminAPITests -v 2`
Expected: FAIL (404 — rota `admin/barbeiros` ainda não existe).

- [ ] **Step 3: Implementar a BarbeiroViewSet**

Em `usuarios/views.py`:

Trocar a linha de import do rest_framework no topo:

```python
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
```

Atualizar o import de serializers para incluir os dois novos:

```python
from .serializers import (
    BarbeiroSerializer,
    ClienteSerializer,
    RegistroBarbeiroSerializer,
    RegistroClienteSerializer,
)
```

Adicionar a classe ao final do arquivo:

```python
class BarbeiroViewSet(viewsets.ModelViewSet):
    """US03/RF03: CRUD de barbeiros restrito ao administrador."""

    queryset = Barbeiro.objects.all().order_by('nome')
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return RegistroBarbeiroSerializer
        return BarbeiroSerializer

    def perform_destroy(self, instance):
        # Soft delete: preserva histórico e FKs de agendamentos.
        instance.ativo = False
        instance.save(update_fields=['ativo'])
```

- [ ] **Step 4: Registrar as rotas do ViewSet**

Substituir todo o conteúdo de `usuarios/urls.py` por:

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BarbeiroListView,
    BarbeiroViewSet,
    PerfilUsuarioView,
    RegistroClienteView,
)

app_name = 'usuarios'

router = DefaultRouter()
router.register(r'admin/barbeiros', BarbeiroViewSet, basename='admin-barbeiro')

urlpatterns = [
    path('usuarios/cadastro/', RegistroClienteView.as_view(), name='cadastro-cliente'),
    path('usuarios/perfil/', PerfilUsuarioView.as_view(), name='perfil_usuario'),
    path('barbeiros/', BarbeiroListView.as_view(), name='lista_barbeiros'),
    path('', include(router.urls)),
]
```

- [ ] **Step 5: Rodar os testes para ver passar**

Run: `./venv/bin/python manage.py test usuarios.tests.BarbeiroAdminAPITests -v 2`
Expected: PASS (5 testes).

- [ ] **Step 6: Rodar a suíte completa do app + system check**

Run: `./venv/bin/python manage.py test usuarios -v 2 && ./venv/bin/python manage.py check`
Expected: todos os testes PASS e `System check identified no issues`.

- [ ] **Step 7: Commit**

```bash
git add usuarios/views.py usuarios/urls.py usuarios/tests.py
git commit -m "feat(usuarios): BarbeiroViewSet admin com soft delete + rotas (US03/RF03)"
```

---

## Mapa de rotas final (US1 / US2 / US3)

| História | Método + Rota | Permissão |
|----------|---------------|-----------|
| US01 cadastro | `POST /api/usuarios/cadastro/` | público |
| US01 perfil | `GET·PATCH /api/usuarios/perfil/` | autenticado |
| US02 login | `POST /api/token/` | público |
| US02 refresh | `POST /api/token/refresh/` | público |
| US02 logout | `POST /api/token/logout/` | autenticado |
| US03 lista/criar | `GET·POST /api/admin/barbeiros/` | admin |
| US03 detalhe | `GET·PUT·PATCH·DELETE /api/admin/barbeiros/{id}/` | admin |
| apoio | `GET /api/barbeiros/` (ativos) | público |

## Notas de implementação

- `BarbeiroSerializer` já expõe `telefone` e `ativo` como editáveis (apenas `username` é read-only) — não precisa de alteração para edição via `PATCH`/`PUT`.
- O logout depende das migrations do `token_blacklist`; sem o `migrate` do Task 1 Step 2, os testes de logout falham.
