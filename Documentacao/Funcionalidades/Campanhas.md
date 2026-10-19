---
tipo: funcionalidade
atualizado: 2026-10-19
---

# Campanhas

Ver [[Funcionalidades]], [[Cliente]]. Fonte pré-existente: `docs/CAMPANHAS_IDEIAS.md`, `docs/CAMPANHAS_ROADMAP.md`, `docs/PLANO_CAMPANHAS_FASE1.md`.

## Identificação

- **Menu:** Vendas e relacionamento → Campanhas (submenus: Estúdio de Ofertas, Ranking de clientes e Cashback e contatos)
- **Rota frontend:** `/campanhas`
- **Módulo de rota:** `frontend/src/app/routes/SalesMarketingRoutes.jsx`
- **Módulo de plano (SaaS):** flag `campanhas`

## Objetivo

Motor de campanhas de marketing/fidelidade: cupons, sorteios, ranking de clientes, fidelidade por pontos/carimbos.

## Backend (confirmado — ~28 arquivos em `campaigns/`)

`campaigns/routes.py`, `campaigns/engine.py` (motor de regras), cupons, sorteios, ranking; `campaigns/scheduler.py` (`CampaignScheduler`, APScheduler); fila própria (`campaign_event_queue`, tabela Postgres com `SELECT FOR UPDATE SKIP LOCKED` — ver [[Arquitetura]]).

## Testes de risco já mapeados pelo projeto

`backend/tests/domain/test_coupon_service.py`, `test_loyalty_service.py`, `test_campaign_coupon_rules.py`, `test_campaigns_routes_cupom_anulacao.py` (`docs/auditorias/testes-ci-cobertura-critica.md`) — risco principal identificado pelo próprio time: "cupom/carimbo duplicado, não consumido ou não revertido".

## Dependências

[[Cliente]] (destinatário), [[PDV-Vendas]] (aplicação de cupom/consumo de fidelidade), [[WhatsApp-WAHA]] (potencial canal de disparo).

## Cashback e contatos

Abra **Campanhas → Cashback e contatos** (`/campanhas/cashback-crm`). A lista
mostra os clientes com cashback disponível, saldo, vencimento próximo, último
contato e status do acompanhamento. A busca, a paginação e os filtros de status
e retorno pendente ajudam a organizar as abordagens.

1. Edite o modelo de mensagem da sessão usando `{nome}` e `{saldo}`.
2. No cliente, use **WhatsApp** para revisar e personalizar a mensagem.
3. Ao abrir a conversa, o CorePet registra texto, data, saldo e operador.
4. Envie a mensagem no WhatsApp e atualize o acompanhamento em **Histórico**:
   mensagem enviada, aguardando retorno, interessado, retornar depois, concluído,
   sem interesse ou não contatar. Inclua uma observação e data de retorno.

“Conversa aberta” registra a ação iniciada pelo operador; envio e leitura não
são confirmados pelo CorePet. “Concluído” é um status manual, sem comprovação
automática de compra ou resgate. Contatos anteriores permanecem no histórico.
Clientes com bloqueio de contato não podem abrir uma nova abordagem pela tela.

O saldo respeita vencimentos e estornos com a mesma regra da carteira do PDV.
Esta tela não altera o crédito do cliente nem gera cashback novo.

Detalhes de validação e operação: `docs/entregas/2026-10-19-cashback-crm.md`.

## Não identificado

- ⚠️ Contrato detalhado do "Estúdio de Ofertas" (`ofertas_estudio_routes.py`) não foi aprofundado nesta rodada.
