---
tipo: seguranca
atualizado: 2026-09-12
---

# API Security

Parte do eixo [[Seguranca]]. Ver [[Autorizacao]], [[Vulnerabilidades]], [[CI-CD]].

## Rate limiting — 🟠 wiring parcial (confirmado)

Existem **dois mecanismos independentes**, e nenhum dos dois cobre 100% do sistema:

1. **`slowapi`** — instalado (`requirements.txt`) e instanciado em `main.py:76` como `Limiter(key_func=get_remote_address, default_limits=["1000/hour"])`. 🟠 **Nenhuma rota usa `@limiter.limit(...)` especificamente** — só existe o limite genérico global de 1000/hora por IP e o exception handler.
2. **Middleware customizado in-memory** (`backend/app/middlewares/rate_limit.py`, `RateLimitMiddleware`): rotas de autenticação (login, registro, forgot/reset-password, refresh, select-tenant, auth do e-commerce) limitadas a **5 requisições/minuto por IP**; demais rotas de API a **100/minuto**; `/health`, `/docs`, `/openapi.json` excluídas.

🟠 **Limitação documentada no próprio código-fonte** (`rate_limit.py:5-8`): o armazenamento é em memória, não persiste entre restarts e **não funciona corretamente com múltiplos processos/réplicas** — cada worker Uvicorn teria seu próprio contador, multiplicando o limite efetivo pelo número de processos em produção.

🟡 A maioria das ~90 rotas do sistema (fora dos grupos `AUTH_ROUTES`/`API_ROUTES` explicitamente listados) não tem rate limit nenhum aplicado além do genérico (que, por sua vez, não tem decorator em nenhuma rota).

**Recomendação:** migrar o rate limit crítico (login, reset de senha) para um backend compartilhado (Redis — que já existe no projeto, ainda que opcional) antes de rodar múltiplos processos/réplicas em produção; caso contrário o controle de força bruta perde eficácia real.

## CORS (confirmado — configuração correta por padrão)

`CORSMiddleware` (`backend/app/main_http.py:74-81`), `allow_origins` vindo de `ALLOWED_ORIGINS` (`app/config.py`), `allow_credentials=True`. Lista fechada por padrão (`localhost:5173`, `localhost:3000`, `corepet.com.br`, `www.corepet.com.br`, `mlprohub.com.br`) — **sem wildcard**, com comentário explícito no código: `"NUNCA use '*' em produção!"`. 🔵 Confirmado correto no código; a configuração real do `.env` de produção está fora do repositório e não foi auditada.

## Webhooks (ver detalhe por integração em [[Integracoes]])

| Webhook | Validação de assinatura | Status |
|---|---|---|
| Bling — `POST /integracoes/bling/pedido` | HMAC-SHA256 (`X-Bling-Signature-256`) via `require_bling_webhook_signature` | 🔵 Confirmado ativo e protegido |
| Bling — `integracao_bling_webhook_routes.py` (`POST /integracoes/bling/webhook`) | **Nenhuma** — apenas loga e responde `{"status":"ok"}` | ⚪ Confirmado **não registrado** em `main_routers.py`/`main.py` — código morto, não exposto atualmente. Recomenda-se remover para evitar registro acidental futuro. |
| Mercado Pago — `POST /webhook/mercadopago/{token}` e `/webhook/mercadopago` | Token opaco por tenant + validação HMAC do provedor (gate por `MERCADO_PAGO_WEBHOOK_VALIDATE_SIGNATURE`) | 🔵 Confirmado; backend reconsulta o pagamento real após o webhook, não confia só no payload |
| WhatsApp (360dialog / WAHA) | HMAC-SHA256 ou token customizado (`X-CorePet-Webhook-Token`), comparação com `hmac.compare_digest` | 🔵 Confirmado |
| Asaas | Token de webhook (`ASAAS_WEBHOOK_TOKEN`) | Confirmado existir; profundidade de validação não auditada a fundo |
| EcommerceAI | HMAC com nonce/timestamp | Confirmado |
| Pagar.me (`POST /pagarme`) | Legado/condicional | ❓ Decisão de aposentar ou formalizar ainda pendente, conforme achado do agente de integrações |

## Uploads (confirmado)

| Fluxo | Validação | Avaliação |
|---|---|---|
| Imagem de produto (`services/product_image_storage.py`) | Valida imagem real via PIL, reconverte sempre para WEBP (elimina payload malicioso embutido), nome de arquivo gerado pelo servidor (`uuid4`), limite de 10MB, chave S3 validada contra path traversal | 🔵 Bem protegido |
| XML de NF-e (`notas_entrada/upload_routes_parts/xml_route.py`) | Valida apenas extensão `.xml` por nome; **sem limite de tamanho**; parse via `xml.etree.ElementTree` (stdlib, bloqueia entidades externas por padrão, mas não usa `defusedxml`) | 🟡 Risco de negação de serviço por XML muito grande ou expansão de entidades internas ("billion laughs"); não há path traversal porque o conteúdo não é salvo com nome do usuário |
| Fotos de pet/banho-tosa | Não encontrada rota que grave arquivo usando `file.filename` do usuário diretamente no path | ⚪ Sem evidência de risco, mas não auditado a fundo — ❓ necessita validação |

**Recomendação:** aplicar limite de tamanho explícito no upload de XML de NF-e, equivalente ao já existente para imagens.

## Mass assignment, paginação, filtros

⚠️ **Não identificado no código analisado** — não foi feita uma varredura dedicada de schemas Pydantic quanto a mass assignment (campos que não deveriam ser setáveis pelo cliente, ex. `tenant_id`, `is_admin`, em payloads de criação/edição). ❓ Necessita validação/auditoria futura antes de assinar esta seção como coberta.

## Não identificado

- Rate limiting por conta em vez de por IP para operações sensíveis (envio de e-mail, geração de relatório pesado, endpoints de IA).
- Auditoria completa de todas as rotas de upload de arquivo do sistema (só produto e XML NF-e foram verificados nesta rodada).
