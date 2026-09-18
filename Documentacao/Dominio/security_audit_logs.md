---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — security_audit_logs

Ver [[data_access_logs]].

## Definição
Log de auditoria de eventos de segurança (não só LGPD) — alerta automático em eventos críticos.

## Confirmado no código
- Modelo: `whatsapp/security.py:232-268` (`SecurityAuditLog`). `tenant_id` sem FK real — coluna do mixin é `nullable=False`, mas `SecurityAuditService.log_security_event` aceita `tenant_id: Optional[str] = None` (❓ potencial erro de integridade se algum caller de fato omitir tenant_id — não confirmado).
- Colunas: `event_type`, `severity` (info/warning/error/critical, default "info"), `resource_type`/`resource_id`/`action`, `description` (NOT NULL), `extra_data` (renomeado para evitar conflito com `metadata` reservado do SQLAlchemy).
- ⚠️ FK fantasma: `user_id` tem comentário `# FK para users` mas sem `ForeignKey()` real.
- Dispara alerta (log) quando `severity == "critical"`.

## Relacionamentos
- Sem FK real.

## Utilizado por
- `SecurityAuditService.log_security_event()`, `whatsapp/security_router.py:384-396` (import local dentro da função, não no topo do arquivo).

## Não identificado
- ❓ Possível erro de integridade se `log_security_event` for chamado sem `tenant_id` apesar da coluna ser NOT NULL — não confirmado se algum caller realmente omite.
