---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — emails_templates

Ver [[email_envios]].

## Definição
Template de e-mail transacional do sistema (ex.: `ACERTO_PARCEIRO`, `BOAS_VINDAS`).

## Confirmado no código
- Modelo: `models.py:416-457` (`EmailTemplate`).
- ⚠️ Mesmo override perigoso de `id`/timestamps documentado em [[audit_logs]].
- `UniqueConstraint(tenant_id, codigo)`. `user_id → users.id` comentado "Multi-tenant" (redundante, mesmo padrão de [[acertos_parceiro]]).
- Colunas: `codigo` (chave lógica), `corpo_html`/`corpo_texto`, `placeholders` (JSON), `categoria` (financeiro/marketing/operacional), `ativo`.

## Relacionamentos
- Referenciada por: [[email_envios]]`.template_id` (nullable).

## Utilizado por
- CRUD em `routes/acertos_routes.py`, `services/acerto_service.py`.

## Não identificado
- Ver achado de override de `id` em [[audit_logs]].
