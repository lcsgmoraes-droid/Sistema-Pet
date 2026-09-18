---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — tenant_whatsapp_config

Ver [[Tenant]], [[whatsapp_ia_sessions]], [[stone_configs]].

## Definição
Configuração da integração WhatsApp (360dialog) por tenant — provider, regras de negócio, estilo do bot.

## Confirmado no código
- Modelo: `whatsapp/models.py:42-123` (`TenantWhatsAppConfig`). Usa `TenantScoped` + `Base`, mas **declara `tenant_id` explicitamente com `ForeignKey("tenants.id")` real** — diferente do padrão fantasma do resto do sistema.
- Colunas: `provider` (default "360dialog"), `phone_number`, `webhook_url`, `model_preference` (default "gpt-4o-mini"), `auto_response_enabled`, `human_handoff_keywords`, `working_hours_start/end`, `bot_name`, `greeting_message`, `tone`.
- ✅ **Migração legado→criptografado bem implementada**: `api_key`, `webhook_secret`, `openai_api_key` cada um tem par de colunas `_legacy` (texto puro, antiga) e `_encrypted`. O getter prioriza o valor criptografado e cai para o legado se não houver; o setter sempre grava criptografado e zera o campo legado automaticamente — migração transparente na escrita. Contraste positivo com [[stone_configs]].

## Relacionamentos
- FK de saída real: `tenant_id → tenants.id`.
- Sem referências de entrada.

## Utilizado por
- `routers/whatsapp_config.py` (lê `api_key`/`webhook_secret`/`openai_api_key`, instancia `Dialog360Client`).

## Não identificado
- Bom exemplo de padrão de migração de segredo — vale usar como referência para outros módulos que ainda armazenam texto puro.
