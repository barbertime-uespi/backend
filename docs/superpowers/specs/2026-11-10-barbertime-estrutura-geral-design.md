# BarberTime — Design da Estrutura Geral (Etapa 1)

**Data:** 2026-11-10
**Fonte:** `docs/BarberTimer(Sistema Web de Agendamentos para Barbearias).pdf`
**Stack:** Django + Django REST Framework + SimpleJWT + SQLite

## Objetivo desta etapa

Subir **apenas a estrutura geral** (scaffold) do backend do BarberTime. Serializers,
views, permissões, validação de conflito e testes ficam para etapas seguintes.

## Decisões arquiteturais

### 1. Autenticação com entidades separadas

O PDF modela `Cliente` e `Barbeiro` como entidades separadas, cada uma com login
próprio, e exige JWT (escolha do usuário) e hash de senha (RNF02).

Reconciliação adotada:

- O `User` nativo do Django é usado **apenas como mecanismo de autenticação**
  (login, hash de senha, emissão de JWT via SimpleJWT).
- `Cliente` e `Barbeiro` permanecem como **modelos/tabelas separados**, cada um com
  `OneToOneField(User)`. O diagrama conceitual do PDF (tabelas Cliente, Barbeiro,
  Servico, Agendamento, Barbeiro_Servico) é preservado.
- O `Administrador` é um `User` com `is_staff=True`, sem perfil Cliente/Barbeiro.
- O papel do usuário é determinado pelo perfil vinculado ao `User`.

### 2. Autenticação JWT

`djangorestframework-simplejwt`:
- `POST /api/token/` — obter par access/refresh
- `POST /api/token/refresh/` — renovar access
- Header: `Authorization: Bearer <jwt>`

### 3. Organização em apps

```
barbertime/              # projeto (settings, urls raiz, wsgi)
├── usuarios/            # User, Cliente, Barbeiro, auth/JWT, registro (Épico E1)
├── servicos/            # Servico + Barbeiro_Servico M2M (Épico E2)
├── agendamentos/        # Agendamento + regras de conflito RN01–RN05 (Épicos E3/E4)
└── manage.py
```

## Modelo de dados (esqueleto desta etapa)

Baseado na seção 8 do PDF:

- **Cliente**: `user (1:1)`, `nome`, `email`, `telefone`
- **Barbeiro**: `user (1:1)`, `nome`, `email`, `telefone`, `ativo`
- **Servico**: `nome`, `descricao`, `preco`, `duracao`, `ativo`
- **Agendamento**: `data`, `horario_inicio`, `horario_fim`, `status`,
  `cliente (FK)`, `barbeiro (FK)`, `servico (FK)`
- **Barbeiro ↔ Servico**: M2M (tabela Barbeiro_Servico)

Relacionamentos: Cliente–Agendamento (1:N), Barbeiro–Agendamento (1:N),
Servico–Agendamento (1:N), Barbeiro–Servico (N:N).

## Escopo

**Nesta etapa (scaffold):**
- Projeto Django + 3 apps registrados
- `settings.py` com DRF, SimpleJWT e SQLite
- Models das 4 entidades + M2M (campos do PDF)
- URLs raiz + rotas de token JWT
- `requirements.txt`, `.gitignore`, migrations iniciais
- README com instruções de execução

**Próximas etapas:**
- Serializers e ViewSets por entidade
- Permissões por papel (matriz da seção 8.3)
- Validação de conflito de horário (RN01–RN05)
- Endpoint de consulta de horários disponíveis (RF06)
- Testes automatizados dos critérios de aceite

## Rastreabilidade

| App | Épico | Requisitos |
|-----|-------|------------|
| usuarios | E1 | RF01, RF02, RNF01, RNF02 |
| servicos | E2 | RF03, RF04, RF05 |
| agendamentos | E3, E4 | RF06–RF10, RN01–RN05 |
