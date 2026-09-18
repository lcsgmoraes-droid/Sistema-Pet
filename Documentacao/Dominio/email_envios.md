---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — email_envios

Ver [[acertos_parceiro]], [[emails_templates]], [[Cliente]].

## Definição
Fila de envio de e-mail (com retry), tipicamente ligada a um acerto de parceiro.

## Confirmado no código
- Modelo: `models.py:460-505` (`EmailEnvio`).
- ⚠️ Mesmo override perigoso de `id`/timestamps documentado em [[audit_logs]].
- `parceiro_id → clientes.id` (destinatário, mesmo padrão de [[acertos_parceiro]]).
- Colunas de fila/retry: `status` (pendente/enviado/erro/cancelado), `tentativas`/`max_tentativas`, `proxima_tentativa`, `ultimo_erro`/`historico_erros` (JSON em texto).

## Relacionamentos
- FKs de saída: `parceiro_id → clientes.id`, `acerto_id → acertos_parceiro.id` (nullable), `template_id → emails_templates.id` (nullable), `user_id → users.id`.

## Utilizado por
- `services/acerto_service.py` (criação do registro de envio), `routes/acertos_routes.py` (`POST /emails/{id}/reenviar`, `POST /emails/processar-fila`).

## Não identificado
- Ver achado de override de `id` em [[audit_logs]].
