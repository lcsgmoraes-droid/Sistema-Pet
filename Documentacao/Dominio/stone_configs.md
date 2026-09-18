---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — stone_configs

Ver [[stone_transactions]], [[bling_connections]], [[tenant_whatsapp_config]].

## Definição
⚠️ Código morto, parte do mesmo módulo órfão de [[stone_transactions]]. Adicionalmente, contém uma promessa de segurança não cumprida.

## Confirmado no código
- Modelo: `stone_models.py:212-306` (`StoneConfig`). FK: `user_id → users.id`.
- 🔴 **Credenciais em texto puro apesar do comentário dizer o contrário**: `client_id`, `client_secret`, `webhook_secret`, `conciliacao_client_id`, `conciliacao_client_secret`, `conciliacao_username` são todos `String` sem criptografia. Só `conciliacao_password_enc` tem comentário dizendo "Senha CRIPTOGRAFADA (AES-256-CBC) — nunca armazenar em texto plano", mas **não há setter/getter que efetivamente criptografe** — nenhum uso de `app.security.tenant_config_crypto` (o módulo usado corretamente por [[bling_connections]] e [[tenant_whatsapp_config]]) em todo o arquivo.

## Relacionamentos
- FK: `user_id → users.id`.

## Utilizado por
- Nada — código morto (parte do módulo Stone inteiro nunca importado fora de si mesmo).

## Não identificado
- 🔴 Mesmo que o módulo seja reativado no futuro, `client_secret` ficaria em claro no banco e `conciliacao_password_enc` dependeria de código externo inexistente para cifrar antes do insert — corrigir isso é pré-requisito caso o módulo seja retomado.
