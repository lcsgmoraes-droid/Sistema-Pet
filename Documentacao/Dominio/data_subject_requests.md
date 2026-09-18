---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — data_subject_requests

Ver [[data_privacy_consents]], [[data_deletion_requests]].

## Definição
Solicitação formal LGPD "operacional" e genérica do sistema (acesso/exportação/correção/exclusão/revogação/info) — **distinta** das tabelas LGPD específicas do WhatsApp ([[data_privacy_consents]]/[[data_access_logs]]/[[data_deletion_requests]] de `whatsapp/security.py`). As duas coexistem sem FK entre si, cobrindo domínios diferentes (solicitações formais de titular vs. logs/consentimentos por canal).

## Confirmado no código
- Modelo: `lgpd_models.py:14-62` (`DataSubjectRequest`).
- Colunas: `subject_type` (customer/user/contact), `request_type` (access/export/correction/deletion/revoke/info), `status` (default "pending"), `requester_name/email/phone`, `channel`, `request_payload`/`response_payload` (⚠️ `Text` livre, não `JSON` tipado — diferente do padrão de `ops_models.py`), `due_at`, `processed_at`.
- ⚠️ `created_by_user_id`/`processed_by_user_id` são Integer sem `ForeignKey()`.

## Relacionamentos
- Sem FK de saída real.

## Utilizado por
- `services/lgpd_requests.py` (CRUD completo), rotas `POST/GET/PATCH /solicitacoes`, `POST /solicitacoes/{id}/anonimizar` em `lgpd_routes.py`, registrado em `main.py:628`.

## Não identificado
- `created_by_user_id`/`processed_by_user_id` deveriam ser FK real.
