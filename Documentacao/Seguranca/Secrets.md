---
tipo: seguranca
atualizado: 2026-09-12
---

# Secrets

Parte do eixo [[Seguranca]]. **Nenhum valor real de secret é reproduzido neste documento ou em qualquer outro de `/Documentacao`.** Ver [[Autenticacao]], [[Integracoes]].

## Variáveis que exigem secret/credencial (confirmado, `.env.example` da raiz — só nomes)

| Variável | Finalidade |
|---|---|
| `JWT_SECRET_KEY` | Assinatura de JWT — validado com mínimo 32 caracteres em produção/staging (`config.py:133-141`) |
| `PAYMENT_CONFIG_ENCRYPTION_KEY` / `ENCRYPTION_KEY` | Chave mestra Fernet para segredos de configuração por tenant |
| `DATABASE_URL` | Contém credencial de banco |
| `BLING_CLIENT_ID` / `BLING_CLIENT_SECRET` | OAuth Bling |
| `INTNFE_INTEGRADOR_ID` / `INTNFE_INTEGRADOR_SECRET` | Ativação fiscal IntNFe |
| `SEFAZ_CERT_PATH` / `SEFAZ_CERT_PASSWORD` | Certificado digital A1 para SEFAZ |
| `MERCADO_PAGO_OAUTH_CLIENT_ID` / `_SECRET` / `MERCADO_PAGO_ACCESS_TOKEN` / `MERCADO_PAGO_WEBHOOK_SECRET` | Pagamento e-commerce |
| `IFOOD_CLIENT_ID` / `IFOOD_CLIENT_SECRET` | Integração iFood |
| `ASAAS_API_KEY` / `ASAAS_WEBHOOK_TOKEN` | Billing SaaS |
| `WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN` / `_WRITE_TOKEN` | Ponte interna n8n/WAHA |
| `ECOMMERCEAI_INTEGRATION_BOOTSTRAP_SECRET` | Integração EcommerceAI |
| `GOOGLE_MAPS_API_KEY` | Geocodificação/rotas |
| `OPENAI_API_KEY` (+ `GROQ_API_KEY`, `GOOGLE_AI_API_KEY` como alternativos) | Provedores de IA |
| `FIREBASE_SERVER_KEY` / `FIREBASE_PROJECT_ID` | ❓ Presente no `.env.example`, **sem uso ativo confirmado** no grep do backend — pode ser legado, substituído por Expo Push. Necessita validação. |

## Onde secrets vivem (confirmado)

- **Nunca no Git**: `.env` real, certificados, dumps — `docs/MAPA_CODIGO_FONTE.md` e `.gitignore` confirmam a exclusão.
- **Produção**: arquivo `.env` no servidor, com `chmod 0600` aplicado automaticamente pelo próprio script de deploy (`scripts/deploy_producao_seguro.sh`).
- **GitHub Secrets**: usados apenas pelo workflow `e2e-long.yml` (variáveis `E2E_*`); se ausentes, a suite pula em vez de falhar.
- **Segredos por tenant** (ex. credencial de gateway de pagamento configurada pelo próprio cliente): criptografados no banco com Fernet (AES-128-CBC autenticado), chave lida de `PAYMENT_CONFIG_ENCRYPTION_KEY`/`ENCRYPTION_KEY` — ver `backend/app/security/tenant_config_crypto.py`.

## Busca por secret hardcoded no código (confirmado — nenhum encontrado)

Busca por padrões `api_key=`, `password=`, `secret=` com valor literal plausível em arquivos `.py` do backend (fora de `.env.example`): **nenhuma ocorrência de secret real**. Dois pontos notáveis, ambos identificados como não sendo vazamento real:

- `backend/app/config.py:18` — `JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"` é um valor sentinela; `_validate_security_settings()` **bloqueia a inicialização** se esse valor persistir em produção/staging (linhas 133-144). ⚪
- `backend/app/security/tenant_config_crypto.py:36-38` — fallback de chave de criptografia para DEV usa `JWT_SECRET_KEY` ou a string fixa `"corepet-dev-only-payment-key"`, **só quando `ENVIRONMENT != production`**; em produção sem a chave real definida, o código força `RuntimeError`. ⚪ Conveniência de desenvolvimento, não secret exposto.

## pycryptodome — dependência instalada, sem uso confirmado

`pycryptodome==3.23.0` está no `requirements.txt` com o comentário "Stone Conciliação - descriptografia de senha (AES-256-CBC)". **Confirmado por grep**: nenhum arquivo `.py` do backend importa `Crypto.Cipher` ou `Crypto` — a dependência parece não ter sido efetivamente usada. Ver seção seguinte.

## ⚠️ Achado que precisa de validação: `StoneConfig.conciliacao_password_enc`

- O modelo `StoneConfig` (`backend/app/stone_models.py:242`) tem um campo `conciliacao_password_enc` com comentário "Senha CRIPTOGRAFADA (AES-256-CBC)".
- **Confirmado por grep dedicado**: nenhum outro arquivo do backend lê ou escreve esse campo. Não há código de cifragem/decifragem associado a ele.

**Isso não é um vazamento de senha em texto puro** (porque nada popula esse campo hoje, confirmado) — é uma funcionalidade que parece nunca ter sido implementada, ou implementada em um caminho não coberto por esta análise.

❓ **Necessita validação com o responsável**: a conciliação Stone usa esse campo hoje, em produção? Se sim, como a senha chega ao sistema — há algum caminho de código não localizado? Se não, recomenda-se remover o campo/comentário para não sugerir uma proteção inexistente, ou implementar a cifragem antes de usar esse fluxo em produção com dados reais.

## Não identificado

- ❓ Confirmação sobre uso de `pycryptodome` em algum módulo de certificado digital/NF-e (PKCS12/RSA), que costuma exigir manipulação binária — não explorado a fundo nesta rodada.
- ❓ Rotação efetiva de secrets em produção — `docs/SEGURANCA_ROTACAO_SSH_SECRETS.md` existe mas não foi auditado linha a linha contra o código.
