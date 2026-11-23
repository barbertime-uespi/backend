# BarberTime

Sistema web de agendamentos para barbearias. Backend em **Django + Django REST
Framework**, autenticação **JWT** e banco **SQLite**.

> Especificação completa em `docs/BarberTimer(Sistema Web de Agendamentos para Barbearias).pdf`.
> Design desta etapa em `docs/superpowers/specs/2026-11-10-barbertime-estrutura-geral-design.md`.

## Status

**Backend — serviços e CORS.** CRUD de serviços com escrita restrita a administradores, consulta pública apenas de serviços ativos, desativação lógica, testes automatizados e CORS configurado para o frontend local.

## Arquitetura

```
barbertime/        # projeto (settings, urls, wsgi)
├── usuarios/      # Cliente, Barbeiro (vinculados ao User) — Épico E1
├── servicos/      # Servico + relação N:N com Barbeiro — Épico E2
└── agendamentos/  # Agendamento — Épicos E3/E4
```

Autenticação: o `User` do Django cuida de login/hash de senha/JWT; `Cliente` e
`Barbeiro` são modelos separados ligados 1:1 ao `User`. O `Administrador` é um
`User` com `is_staff=True`.

## Como executar

```bash
# 1. Criar e ativar o virtualenv
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 2.1 Executar os testes automatizados
python manage.py test

# 3. Aplicar migrations
python manage.py migrate

# 4. Criar um administrador
python manage.py createsuperuser

# 5. Rodar o servidor
python manage.py runserver
```

- Admin do Django: http://127.0.0.1:8000/admin/
- Obter token JWT: `POST /api/token/` com `username` e `password`
- Renovar token: `POST /api/token/refresh/`

## Serviços e permissões

- `GET /api/servicos/` e `GET /api/servicos/{id}/` são públicos e retornam somente serviços ativos.
- `POST`, `PUT`, `PATCH` e `DELETE` exigem usuário administrador (`is_staff=True`).
- `DELETE /api/servicos/{id}/` realiza desativação lógica, preservando o registro.
- Administradores podem consultar também os serviços inativos.

## CORS

As origens `http://localhost:5173` (Vite) e `http://localhost:3000` estão liberadas para desenvolvimento. Inclua a origem real do frontend em `CORS_ALLOWED_ORIGINS` ao mudar o endereço.

## Testes

Execute `python manage.py test` na raiz do projeto para rodar os testes dos aplicativos.
