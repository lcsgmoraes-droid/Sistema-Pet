---
tipo: roadmap
atualizado: 2026-09-12
---

# Fase 3 — Organização das Integrações

Parte de [[Roadmap]]. Base: [[Integracoes]] e seus 8 documentos filhos, [[Vulnerabilidades]].

## Objetivo da fase

Depois que o código está mais componentizado (Fase 1) e as funcionalidades que consomem cada integração estão bem mapeadas (Fase 2), padronizar o **como** cada integração se comunica — hoje cada uma resolve timeout, retry e validação de webhook do seu próprio jeito.

## 3.1 — Padrão único de resiliência (timeout/retry/backoff)

[[Integracoes]] já mapeia isso por integração. Resumo do que falta padronizar:

| Integração | Retry hoje | Ação |
|---|---|---|
| [[Bling]] | ✅ backoff 1-8s, 5 tentativas | Referência a copiar |
| [[Mercado-Pago]] | 🟡 sem fila durável | Adicionar retry/fila |
| [[iFood]] | 🟡 sem retry exponencial central | Adicionar |
| [[WhatsApp-WAHA]] | 🟡 sem contrato único de fila para saída | Adicionar |
| Google Maps (ver [[Integracoes]]) | 🟡 sem retry/cache | Adicionar cache (geocoding muda pouco) + retry |
| [[OpenAI-IA]] | ✅ retry configurável + fallback determinístico | Referência a copiar |

Ação concreta: extrair um **cliente HTTP base compartilhado** (wrapper fino sobre `httpx`/`requests`) com timeout, retry com backoff e log padronizado, e migrar as integrações da coluna "🟡" para usá-lo — em vez de cada uma reimplementar o próprio `try/except`. Isso também resolve parte da duplicação apontada na Fase 2 (item 2.4).

## 3.2 — Padrão único de validação de webhook

Confirmado em [[API-Security]]: Bling (pedido), Mercado Pago, WhatsApp e EcommerceAI já validam assinatura corretamente. Pagar.me está em zona cinzenta (legado/condicional). Ações:

- [ ] Decidir o destino do webhook `POST /pagarme` — formalizar validação de assinatura ou aposentar de vez (já é [[Pendencias]] em aberto).
- [ ] Remover `integracao_bling_webhook_routes.py` (confirmado código morto, não registrado — ver [[Vulnerabilidades]] item 7) para não deixar um exemplo sem assinatura disponível para cópia acidental futura.
- [ ] Documentar o padrão de validação de webhook (HMAC + comparação `hmac.compare_digest`) como referência obrigatória para qualquer integração nova — hoje está correto na prática mas não formalizado como regra escrita em `docs/BLUEPRINT_BACKEND.md` ou equivalente.

## 3.3 — Esclarecer sobreposições conhecidas

- [ ] **SEFAZ vs. IntNFe** (ver [[Fiscal-IntNFe-SEFAZ]]): documentar formalmente se são complementares por função (consulta/importação vs. emissão) ou se um substitui o outro no roadmap de produto. Isso está em [[Pendencias]] como bloqueio de entendimento, não só de documentação.
- [ ] **Bling emitindo fiscal enquanto IntNFe está em ativação**: confirmar o plano de transição (se houver) antes de investir mais na Fase 3 nessas duas integrações — evita retrabalho se a decisão for "IntNFe substitui Bling para emissão em 2027".

## 3.4 — Observabilidade consolidada de integrações

- [ ] Hoje cada integração loga/monitora à sua maneira (ex.: worker Bling tem heartbeat próprio, `bling_flow_monitor_*`). Avaliar um painel único (mesmo que simples, reaproveitando o painel Ops já existente conforme `docs/GESTAO_INCIDENTES_SUSTENTACAO.md`) mostrando: última sincronização bem-sucedida, taxa de erro recente, fila pendente — por integração, não só por Bling.

## 3.5 — Dependências não confirmadas (resolver antes de investir tempo de engenharia)

- [ ] Confirmar se Firebase ainda é usado (ver [[Secrets]]) — se não, remover do `.env.example` e do `requirements.txt`/`package.json` correspondente, reduz superfície de configuração morta.
- [ ] Confirmar se os providers de IA alternativos (Groq, Google AI) têm implementação real — se não, não vale investir em padronizar retry/timeout para código que não existe.

## Critério de avanço para a Fase 4

- Cliente HTTP compartilhado adotado por pelo menos as integrações "🟡" da tabela 3.1.
- Decisão registrada (não necessariamente implementada) sobre Pagar.me, SEFAZ vs. IntNFe, e Firebase.
- Webhook morto do Bling removido.

## Não identificado

- ❓ Se existe apetite/orçamento para um painel de observabilidade dedicado, ou se o painel Ops existente é suficiente ampliado.
