# Design — US02 (logout) + US03 (gerenciamento de barbeiros)

Data: 2026-11-17
Épicos: E1 (Acesso e gerenciamento de usuários), E2 (Gerenciamento da barbearia)
Requisitos: RF02, RF03, RNF01, RNF02

## Objetivo

Fechar a pendência da US02 (logout) e implementar a US03 (gerenciamento de
barbeiros pela API, restrito ao administrador), garantindo que as rotas das
US01, US02 e US03 exponham um CRUD completo e consistente para o front-end.

## Contexto atual

- Autenticação via `rest_framework_simplejwt` já configurada
  (`api/token/`, `api/token/refresh/`), `IsAuthenticated` como permissão
  padrão global.
- `usuarios/models.py`: `Cliente` e `Barbeiro`, ambos com `OneToOneField`
  obrigatório para `settings.AUTH_USER_MODEL`. `Barbeiro` tem `ativo`.
- `usuarios/serializers.py`: `RegistroClienteSerializer` (cria User + Cliente),
  `ClienteSerializer`, `BarbeiroSerializer` (leitura).
- `usuarios/views.py`: `RegistroClienteView`, `PerfilUsuarioView`,
  `BarbeiroListView` (lista barbeiros ativos, pública).
- `token_blacklist` **não** está em `INSTALLED_APPS`.

## 1. US02 — Logout (RF02 / RNF02)

### Configuração
- Adicionar `'rest_framework_simplejwt.token_blacklist'` ao `INSTALLED_APPS`.
- Rodar `python manage.py migrate` (cria tabelas de blacklist).
- No bloco `SIMPLE_JWT` do `settings.py`:
  - `ROTATE_REFRESH_TOKENS = True`
  - `BLACKLIST_AFTER_ROTATION = True`

### Endpoint
- `LogoutView(APIView)`, `permission_classes = [IsAuthenticated]`.
- `POST /api/token/logout/` com corpo `{"refresh": "<refresh_token>"}`.
- Fluxo: instanciar `RefreshToken(refresh)`, chamar `.blacklist()`,
  retornar `205 Reset Content`.
- Erros: refresh ausente ou inválido → `400 Bad Request` com mensagem.
- Registrada em `barbertime/urls.py`, junto das demais rotas de auth.

## 2. US03 — Gerenciamento de barbeiros (RF03, E2)

Restrito ao administrador (`IsAdminUser` → `user.is_staff`), conforme a
matriz de permissões (seção 8.3 do documento de requisitos: "Cadastrar
barbeiros" = somente Administrador).

### Serializers (`usuarios/serializers.py`)
- `RegistroBarbeiroSerializer` (escrita/criação):
  - Campos: `id, username, password, nome, email, telefone, ativo`.
  - `username` e `password` são `write_only`.
  - Valida `username` e `email` duplicados (contra `User` e `Barbeiro`).
  - `create` em `@transaction.atomic`: cria `User` (via `create_user`,
    senha com hash) e o `Barbeiro` vinculado.
- `BarbeiroSerializer` (leitura/edição):
  - Campos: `id, username (read-only), nome, email, telefone, ativo`.
  - `telefone` passa a ser editável (hoje o serializer só expõe leitura).

### ViewSet (`usuarios/views.py`)
- `BarbeiroViewSet(ModelViewSet)`, `permission_classes = [IsAdminUser]`.
- `queryset = Barbeiro.objects.all().order_by('nome')` (admin vê inativos também).
- `get_serializer_class`: `create` → `RegistroBarbeiroSerializer`;
  demais ações → `BarbeiroSerializer`.
- `destroy` sobrescrito → **soft delete**: seta `ativo=False`, salva,
  retorna `204 No Content` (não remove o registro, preserva histórico de
  agendamentos e integridade de FKs).
- Reativar / editar = `PATCH`/`PUT`.

### Rotas
- `DefaultRouter` em `usuarios/urls.py` registrando o ViewSet em
  `admin/barbeiros` → `/api/admin/barbeiros/` e `/api/admin/barbeiros/{id}/`.
- A rota pública `GET /api/barbeiros/` (lista apenas ativos, via
  `BarbeiroListView`) é mantida, separada da rota de gestão, para o cliente
  escolher barbeiro no agendamento sem expor dados de gestão/inativos.

## 3. Mapa de rotas US1 / US2 / US3 (CRUD para o front)

| História | Método + Rota | Permissão |
|----------|---------------|-----------|
| US01 cadastro | `POST /api/usuarios/cadastro/` | público |
| US01 perfil | `GET·PATCH /api/usuarios/perfil/` | autenticado |
| US02 login | `POST /api/token/` | público |
| US02 refresh | `POST /api/token/refresh/` | público |
| US02 logout | `POST /api/token/logout/` 🆕 | autenticado |
| US03 lista/criar | `GET·POST /api/admin/barbeiros/` 🆕 | admin |
| US03 detalhe | `GET·PUT·PATCH·DELETE /api/admin/barbeiros/{id}/` 🆕 | admin |
| apoio | `GET /api/barbeiros/` (ativos) | público |

## Testes (DRF `APITestCase`)

- **Logout**: após logout, o refresh usado retorna `401` em `api/token/refresh/`.
- **Logout** sem/`refresh` inválido → `400`.
- **Barbeiro CRUD**:
  - admin cria barbeiro → `201`, e o `User` correspondente é criado e
    consegue autenticar.
  - admin edita (`PATCH`) e reativa/desativa via `ativo`.
  - `DELETE` como admin → `204` e `ativo=False` (registro preservado).
  - cliente autenticado em qualquer ação de gestão → `403`.
  - não autenticado → `401`.

## Fora de escopo

- US04..US08 (serviços já feito; agendamentos, consulta de horários,
  cancelamento, agenda do barbeiro) — serão tratados em specs próprios.
- Endpoint de troca de senha do barbeiro.
