---
tipo: base
atualizado: 2026-09-12
---

# Matriz de Cobertura

Ver [[README]], [[Funcionalidades]]. Legenda: ✅ confirmado e documentado nesta fase · 🟡 confirmado que existe, documentação rasa · ❌ não documentado nesta fase (rota confirmada, resto não aprofundado).

| Funcionalidade | Frontend | Backend | Banco | API | Integração | Segurança | Documentado |
|---|---|---|---|---|---|---|---|
| PDV/Vendas | ✅ | ✅ | ✅ | 🟡 | ✅ (Stone, MP, Bling) | ✅ | [[PDV-Vendas]] |
| Produtos/Estoque | ✅ | ✅ | ✅ | 🟡 | ✅ (Bling) | ✅ | [[Produtos-Estoque]] |
| Financeiro | ✅ | ✅ | ✅ | 🟡 | ✅ (Stone) | ✅ | [[Financeiro]] |
| Comissões | 🟡 | ✅ | 🟡 | ❌ | — | ❌ | [[Comissoes]] |
| Compras | 🟡 | ✅ | ✅ | ❌ | ✅ (Bling) | ✅ | [[Compras]] |
| Banho e Tosa | ✅ | ✅ | ✅ | ❌ | 🟡 | 🟡 | [[Banho-e-Tosa]] |
| Veterinário | ✅ | ✅ | 🟡 | ❌ | ✅ (IA) | 🟡 | [[Veterinario]] |
| Campanhas | 🟡 | ✅ | 🟡 | ❌ | 🟡 | 🟡 | [[Campanhas]] |
| E-commerce | ✅ | ✅ | 🟡 | ❌ | ✅ (MP, EcommerceAI) | ✅ | [[E-commerce]] |
| Entregas | ✅ | ✅ | 🟡 | ❌ | 🟡 (Google Maps) | 🟡 | [[Entregas]] |
| Bling (integração) | — | ✅ | ✅ | ✅ | ✅ | ✅ | [[Bling]] |
| WhatsApp | 🟡 | ✅ | ❌ | ❌ | ✅ | ✅ | [[WhatsApp-WAHA]] |
| Fiscal (SEFAZ/IntNFe) | ❌ | ✅ | 🟡 | ❌ | ✅ | 🟡 | [[Fiscal-IntNFe-SEFAZ]] |
| iFood | ❌ | ✅ | 🟡 | ❌ | ✅ | 🟡 | [[iFood]] |
| Stone (conciliação) | 🟡 | ✅ | ✅ | ❌ | ✅ | ✅ (achado 🟠) | [[Stone]] |
| IA (OpenAI) | 🟡 | ✅ | ❌ | ❌ | ✅ | 🟡 | [[OpenAI-IA]] |
| Asaas (billing) | ❌ | ✅ | 🟡 | ❌ | ✅ | 🟡 | [[Asaas]] |
| Autenticação/Autorização | ✅ | ✅ | ✅ | 🟡 | — | ✅ | [[Autenticacao]], [[Autorizacao]] |
| Dashboard | 🟡 | ❌ | ❌ | ❌ | — | ❌ | ❌ não documentado |
| Lembretes | ❌ | 🟡 | ❌ | ❌ | — | ❌ | ❌ não documentado |
| Calculadora de Ração | ❌ | 🟡 | ❌ | ❌ | 🟡 (IA) | ❌ | ❌ não documentado |
| Cadastros auxiliares | ❌ | 🟡 | 🟡 | ❌ | — | ❌ | ❌ não documentado |
| RH | ❌ | 🟡 | ❌ | ❌ | — | ❌ | ❌ não documentado |
| Configurações (fiscal/geral/grupos) | ❌ | 🟡 | ❌ | ❌ | — | ❌ | ❌ não documentado |
| Alertas do gestor | ❌ | 🟡 | ❌ | ❌ | — | ❌ | ❌ não documentado |
| Painel `/ops` (plataforma) | 🟡 | 🟡 | ❌ | ❌ | ✅ (Asaas) | ❌ | ❌ não documentado |

## Leitura da matriz

- **19 de 25** áreas de menu/integração identificadas têm pelo menos documentação parcial nesta primeira fase.
- **7 áreas** (Dashboard, Lembretes, Calculadora de Ração, Cadastros auxiliares, RH, Configurações, painel `/ops`) foram identificadas (rota confirmada) mas não aprofundadas — candidatas naturais para a próxima rodada de documentação, listadas em [[Pendencias]].
- Nenhuma funcionalidade tem coluna "API" ✅ completa — o contrato detalhado de payload não foi extraído em nenhum domínio nesta fase (ver [[API]]); é o maior gap sistemático desta análise, não específico de um módulo.
