---
tipo: base
atualizado: 2026-09-12
---

# API

Ver [[Arquitetura]], [[Funcionalidades]]. A API é grande (confirmado: ~90 chamadas `include_router` em `backend/app/main_routers.py`, sem prefixo global único) — este documento indexa por domínio em vez de listar endpoint a endpoint, para evitar um arquivo gigante e de baixo valor de navegação.

## Como a API é organizada (confirmado)

- Entrada: `backend/app/main.py` monta a aplicação FastAPI.
- Registro de rotas: `backend/app/main_routers.py` (`register_routers(app)`), sem prefixo global — cada router define seu próprio prefixo.
- Muitos routers usam `dependencies=_module_dependencies("<modulo>")` — a rota só responde (ou responde negando acesso) se o módulo estiver contratado pelo tenant. Ver [[Arquitetura#Módulos ligáveis por tenant]].
- Toda rota autenticada passa por [[Autenticacao]] (JWT) e a maioria por [[Autorizacao]] (permissão explícita via `require_permission`).
- Documentação automática OpenAPI/Swagger disponível (`/docs`, `/openapi.json` — confirmado excluídos do rate limiting em `middlewares/rate_limit.py`), é a fonte mais precisa de contrato de request/response por ser gerada do próprio código Pydantic.

## Índice por domínio (arquivo de rota → funcionalidade)

| Domínio | Arquivo(s) de rota principal | Funcionalidade |
|---|---|---|
| Auth/RBAC | `auth_routes_multitenant.py`, `usuarios_routes.py`, `roles_routes.py`, `permissions_routes.py` | [[Autenticacao]], [[Autorizacao]] |
| Clientes/Pets | `clientes_routes.py`, `pets_routes.py`, `cadastros_routes.py` | [[Cliente]], [[Pet]] |
| Veterinário | `veterinario_routes.py` | [[Veterinario]] |
| Banho e Tosa | `banho_tosa_routes.py` + `banho_tosa_api/` | [[Banho-e-Tosa]] |
| Produtos | `produtos_routes.py`, `variacoes_routes.py` | [[Produtos-Estoque]] |
| Estoque | ~15 routers `estoque_*` | [[Produtos-Estoque]] |
| Compras | `pedidos_compra_routes.py`, `notas_entrada_routes.py` | [[Compras]] |
| Vendas/Caixa | `vendas_routes.py`, `caixa_routes.py` | [[PDV-Vendas]] |
| Fiscal | `nfe_routes.py`, `intnfe/routes.py`, `api/v1/*fiscal*` | [[Fiscal-IntNFe-SEFAZ]] |
| Financeiro | `contas_pagar_routes.py`, `contas_receber_routes.py`, `dre_*_routes.py`, `conciliacao_*` | [[Financeiro]] |
| Comissões | `comissoes_routes.py` + variantes | [[Comissoes]] |
| Bling | `bling_routes.py`, `bling_oauth_routes.py`, `integracao_bling_*` | [[Bling]] |
| IA/Chat | `ia_routes.py`, `chat_routes.py`, `dre_ia_routes.py` | [[OpenAI-IA]] |
| WhatsApp | `api/endpoints/whatsapp.py`, `whatsapp/webhook.py`, `routers/whatsapp_*` | [[WhatsApp-WAHA]] |
| E-commerce | `routes/ecommerce*.py` | [[E-commerce]] |
| App mobile | `routes/app_mobile_routes.py`, `routes/app_vet_routes.py` | App mobile (ver [[Pendencias]]) |
| Campanhas | `campaigns/routes.py`, `ofertas_estudio_routes.py` | [[Campanhas]] |
| Entregas | `api/endpoints/rotas_entrega.py` (+ pública) | [[Entregas]] |
| RH | `cargos_routes.py`, `funcionarios_routes.py` | Funcionalidades → RH (sem doc dedicado) |
| Billing/plataforma | `routes/asaas_billing_routes.py`, `routes/modulos_routes.py` | [[Asaas]] |

## Webhooks recebidos (ver detalhe de segurança em [[API-Security]])

`POST /integracoes/bling/pedido`, `POST /webhook/mercadopago(/{token})`, `POST /webhook/whatsapp/...`, `POST /internal/whatsapp-orchestrator/...`, `POST /webhook` (Asaas), `POST /pagarme` (legado).

## Não identificado

- ⚠️ Não identificado no código analisado (nesta rodada): contratos completos de request/response por endpoint. A fonte mais confiável para isso é a documentação OpenAPI automática do próprio backend (`/docs`), não recriada aqui para evitar desatualização — este índice aponta para onde procurar por domínio.
