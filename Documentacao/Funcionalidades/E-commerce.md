---
tipo: funcionalidade
atualizado: 2026-09-12
---

# E-commerce

Ver [[Funcionalidades]], [[Mercado-Pago]], [[Venda]].

## Identificação
- **Menu:** Vendas e relacionamento → E-commerce (submenu: Prévia, Aparência, Divulgação, Config., Saúde do Catálogo, Analytics)
- **Rota frontend (admin):** `/ecommerce` (dentro de `SalesMarketingRoutes.jsx`)
- **Rota frontend (loja pública):** `/ecommerce` e `/:tenantId` (públicas, fora de `Layout`, em `PublicRoutes.jsx`) — cada tenant tem sua própria loja acessível publicamente
- **Módulo de plano (SaaS):** habilitado por tenant via flag `ecommerce`

## Objetivo
Loja virtual pública por tenant, com carrinho, checkout, aparência configurável (branding próprio da loja) e analytics de conversão.

## Backend (confirmado — ~15 arquivos `routes/ecommerce*.py`)
Rotas públicas, carrinho, checkout, webhooks de pagamento, aparência, configuração, notificações, analytics, "drive" (retirada). Modelos: `ecommerce_analytics_models.py`, `ecommerce_payment_models.py`.

## Integrações
[[Mercado-Pago]] (checkout/pagamento), EcommerceAI (parceria de catálogo/eventos B2B, ver [[Integracoes]]), Pagar.me (webhook legado, ver [[Integracoes]]).

## Segurança
Loja pública = superfície exposta sem autenticação por padrão (rotas em `PublicRoutes.jsx`) — reforça a importância da validação de webhook de pagamento (ver [[API-Security]]) e do isolamento de tenant por slug/URL pública.

## Dependências
[[Produto]] (catálogo publicado), [[Venda]]/`Pedido` (pedido gerado pelo canal e-commerce, ver [[Venda#Não identificado]]).

## Não identificado
- ❓ Se há rate limiting específico para as rotas públicas de e-commerce (potencial alvo de scraping/abuso por serem acessíveis sem login) — ver [[API-Security]], que confirma rate limit apenas para grupos `AUTH_ROUTES`/`API_ROUTES` explícitos.
