---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — data_access_logs

Ver [[data_privacy_consents]].

## Definição
Log de auditoria LGPD de acesso a dados pessoais (read/write/delete/export).

## Confirmado no código
- Modelo: `whatsapp/security.py:162-189` (`DataAccessLog`). Mesmo padrão de `tenant_id` sem FK real.
- Colunas: `subject_type`/`subject_id`, `access_type` (read/write/delete/export), `resource_type`/`resource_id`, `ip_address`/`user_agent`/`justification`.
- ⚠️ FK fantasma: `accessed_by_user_id` tem comentário `# FK para users` mas sem `ForeignKey()` real.

## Relacionamentos
- Sem FK real.

## Utilizado por
- `LGPDService.log_data_access()`, `services/lgpd_audit.py`/`lgpd_customer_data.py`.

## Não identificado
- `accessed_by_user_id` deveria ser FK real e não é.
