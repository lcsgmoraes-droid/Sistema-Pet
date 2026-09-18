---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — data_deletion_requests

Ver [[data_privacy_consents]], [[data_access_logs]].

## Definição
Solicitação LGPD de exclusão de dados pessoais ("direito ao esquecimento").

## Confirmado no código
- Modelo: `whatsapp/security.py:192-224` (`DataDeletionRequest`). `tenant_id` sem FK real.
- Colunas: `subject_type`/`subject_id`, `request_date`, `reason`, `status` (pending/approved/rejected/completed, default "pending"), `processed_at`/`rejection_reason`, `contact_phone`/`contact_email`, `extra_metadata`.
- ⚠️ FK fantasma: `processed_by_user_id` tem comentário `# FK para users` mas sem `ForeignKey()` real.

## Relacionamentos
- Sem FK real.

## Utilizado por
- `LGPDService.request_data_deletion/process_deletion_request`, `whatsapp/security_router.py`.

## Não identificado
- `processed_by_user_id` deveria ser FK real e não é.
