# BarberTime

Sistema web de agendamentos para barbearias. Backend em **Django + Django REST
Framework**, autenticação **JWT** e banco **SQLite**.

> Especificação completa em `docs/BarberTimer(Sistema Web de Agendamentos para Barbearias).pdf`.
> Design desta etapa em `docs/superpowers/specs/2026-11-10-barbertime-estrutura-geral-design.md`.

## Status

**Etapa 1 — Estrutura geral (scaffold).** Projeto, apps, models e autenticação JWT
configurados. Serializers, views, permissões e regras de negócio virão nas próximas etapas.

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

## Próximas etapas

- Serializers e ViewSets por entidade
- Permissões por papel (matriz da especificação)
- Validação de conflito de horário (RN01–RN05)
- Consulta de horários disponíveis (RF06)
- Testes automatizados
