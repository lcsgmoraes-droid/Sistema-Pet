---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — acertos_parceiro

Ver [[Cliente]], [[email_envios]], [[comissoes_itens]].

## Definição
Acerto financeiro periódico com um parceiro/comissionado (modelado como [[Cliente]]).

## Confirmado no código
- Modelo: `models.py:356-413` (`AcertoParceiro`).
- ⚠️ Mesmo override perigoso de `id`/timestamps documentado em [[audit_logs]].
- `parceiro_id → clientes.id` — confirma o padrão "parceiro = Cliente" já visto em [[comissoes_itens]]`.funcionario_id`.
- `user_id → users.id` comentado como "Multi-tenant" — campo redundante, já que o tenant vem do `tenant_id` do mixin.
- Colunas: `tipo_acerto` (mensal/quinzenal/semanal/manual), `valor_bruto`/`valor_compensado`/`valor_liquido`, `status` (processado/erro/cancelado), rastreio de e-mail (`email_enviado`, `email_destinatarios`, `email_erro`).

## Relacionamentos
- FKs de saída: `parceiro_id → clientes.id`, `user_id → users.id`.
- Referenciada por: [[email_envios]]`.acerto_id` (nullable).

## Utilizado por
- `services/acerto_service.py` (geração do acerto), `routes/acertos_routes.py` (`POST /gerar`, `GET /{acerto_id}`).

## Não identificado
- Ver achado de override de `id` em [[audit_logs]].
