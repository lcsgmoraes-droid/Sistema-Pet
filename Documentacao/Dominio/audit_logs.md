---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — audit_logs

Ver [[Usuario]], [[security_audit_logs]].

## Definição
Log de auditoria genérico do sistema (rastreabilidade LGPD) — docstring explícita no código.

## Confirmado no código
- Modelo: `models.py:290-318` (`AuditLog`).
- 🔴 **Override perigoso confirmado**: a classe redeclara manualmente `id = Column(Integer, primary_key=True, index=True)`, sobrescrevendo o `id` com `Identity(always=True)` que o próprio `BaseTenantModel` foi desenhado para fornecer especificamente para evitar duplicate-key violations (documentado no docstring do mixin, `base_models.py:47-48`). Como atributo de subclasse tem precedência sobre `declared_attr` do mixin, esta tabela perde essa proteção silenciosamente. Mesmo padrão em [[acertos_parceiro]], `emails_templates`, `email_envios` — parece cópia de um template antigo pré-`BaseTenantModel`.
- Colunas: `user_id` (FK, nullable — permite log de ações "do sistema"), `action`, `entity_type`, `entity_id` (⚠️ Integer solto, sem FK), `old_value`/`new_value`/`details` (texto JSON manual, não coluna `JSON`), `timestamp` (índice próprio, além do `created_at` do mixin).
- ⚠️ **Duplicação de helper de auditoria (não de tabela)**: `audit_log.py::log_action` (+ atalhos `log_login`/`log_create`/etc.) é o caminho **realmente usado** (importado em ~20 módulos, granularidade por ação de negócio, descarta o log se não houver tenant no contexto). `audit.py::log_audit` existe, bem escrito, mas **nunca é importado em lugar nenhum** — código morto em nível de service, mesma categoria de achado já vista em módulos ORM inteiros.

## Relacionamentos
- FK de saída: `user_id → users.id` (nullable).

## Utilizado por
- Escrita: `audit_log.py::log_action` (rotas de vendas, clientes, auth, cadastros, config de empresa, NF-e, replay engine, read models, event handlers).
- Leitura: `services/audit_event_report_service.py`, `audit/queries.py`.

## Não identificado
- 🟡 Não confundir com [[security_audit_logs]] (`whatsapp/security.py`) — tabela diferente, específica de segurança do WhatsApp.
- Recomenda-se remover `audit.py::log_audit` (código morto) e corrigir o override de `id` nas 4 tabelas afetadas.
