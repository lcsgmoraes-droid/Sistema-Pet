# Roadmap Completo — Sistema de Campanhas

> Criado em Março 2026.
> Baseado em `docs/CAMPANHAS_IDEIAS.md`.
> Atualizar este arquivo conforme itens forem concluídos.

**Legenda:** ✅ Feito · 🔄 Em progresso · ❌ Pendente · ⚠️ Parcial

---

## Situação Atual (Resumo Rápido) — atualizado em 05/03/2026

| Camada                   | O que está pronto                                                                                                                                                                                                                                                 |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Banco de dados**       | Modelos completos: campanhas, cupons, cashback, carimbos, ranking, sorteios, notificações, execuções (idempotência)                                                                                                                                               |
| **Backend API**          | Endpoints: campanhas CRUD, ranking, dashboard (alertas + próximos eventos), relatório, saldo, cupons, anular cupom, sorteios CRUD, destaque mensal (calcular + enviar), unificação CPF, notificações inativos; scheduler integrado no main.py                     |
| **Workers automáticos**  | ✅ birthday_customer + birthday_pet (job 08h diário); ✅ cashback por nível (hook em vendas_routes); ✅ loyalty_stamp (hook em vendas_routes); ✅ inactivity (job semanal); ✅ ranking mensal (job dia 1); ✅ notification_sender (SMTP real, batch a cada 5 min) |
| **Frontend**             | Campanhas.jsx com 9 abas: Dashboard, Campanhas, Ranking, Sorteios, Destaque Mensal, Unificação, Cupons, Relatórios, **Gestor de Benefícios** (busca por cliente ou por campanha; gerencia carimbos/cashback/cupons/ranking de forma unificada)                    |
| **PDV**                  | Badge de nível de ranking no painel do cliente + campo de cupom de desconto                                                                                                                                                                                       |
| **Cadastro de clientes** | Badge de nível de ranking no modal do cliente                                                                                                                                                                                                                     |
| **App Mobile**           | Campo CPF no cadastro + Aba "Meus Cupons" · ❌ Falta: tela "Meus Benefícios" (carimbos, cashback, ranking, progresso, vantagens por nível)                                                                                                                        |
| **Ecommerce**            | CPF obrigatório no cadastro                                                                                                                                                                                                                                       |
| **Lembretes**            | Alertas de campanhas integrados em Lembretes.jsx (Sprint 9)                                                                                                                                                                                                       |

**O que ainda falta (06/03/2026):** Push FCM real (bloqueado — app não publicado na Play Store). Todos os demais itens do roadmap estão concluídos.

---

## FASE 1 — Base e Campanhas Simples

### 1.1 Infraestrutura de Base

| Item                                                                   | Backend  | Frontend                                                          | Status |
| ---------------------------------------------------------------------- | -------- | ----------------------------------------------------------------- | ------ |
| Tabelas: Campaign, CampaignEventQueue, CampaignExecution, CampaignLock | ✅ Feito | —                                                                 | ✅     |
| Tabelas: CashbackTransaction, LoyaltyStamp, Coupon, CouponRedemption   | ✅ Feito | —                                                                 | ✅     |
| Tabelas: CustomerRankHistory                                           | ✅ Feito | —                                                                 | ✅     |
| Tabelas: Drawing, DrawingEntry                                         | ✅ Feito | —                                                                 | ✅     |
| Tabelas: NotificationQueue, NotificationLog                            | ✅ Feito | —                                                                 | ✅     |
| Tabela `campanha_cliente_log` (controle de não-duplicidade de envio)   | ✅ Feito | `campaign_executions` com UNIQUE(tenant+campaign+customer+period) | ✅     |

> **Nota:** Idempotência garantida pela tabela `campaign_executions` com constraint único por (tenant, campanha, cliente, período).

---

### 1.2 Campanhas Sazonais — Aniversário do Cliente

| Item                                                                                   | Status     | Detalhe                                                         |
| -------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------- |
| Tipo `birthday_customer` existe no enum                                                | ✅ Feito   | —                                                               |
| Worker: job diário que busca clientes aniversariantes de hoje                          | ✅ Feito   | `BirthdayHandler` + `daily_birthday_check` às 08:00             |
| Worker: gera cupom automaticamente para o aniversariante                               | ✅ Feito   | `BirthdayHandler._reward_customer()` via `coupon_service`       |
| Worker: envia e-mail com o cupom                                                       | ✅ Feito   | `NotificationSender` — SMTP real, batch a cada 5 min            |
| Controle de duplicidade (não enviar 2x no mesmo aniversário)                           | ✅ Feito   | `reference_period = today.isoformat()` em `campaign_executions` |
| **UI — Ativar/desativar**                                                              | ⚠️ Parcial | Botão de pausar existe, mas não há config específica            |
| **UI — Parametrizar** aniversários (cliente e pet): valor do cupom, validade, mensagem | ✅ Feito   | Sprint 10 — editor visual com CampanhaField                     |
| Mostrar aniversariantes de hoje no Dashboard                                           | ✅ Feito   | `aniversarios_hoje` renderizado no Dashboard (clientes + pets)  |

---

### 1.3 Campanhas Sazonais — Aniversário do Pet

| Item                                                                | Status   |
| ------------------------------------------------------------------- | -------- | ----------------------------------------------------------------- |
| Tipo `birthday_pet` existe no enum                                  | ✅ Feito |
| Worker: job diário buscando pets aniversariantes                    | ✅ Feito | `BirthdayHandler._run_birthday_pet()`                             |
| Worker: gera cupom / notifica dono                                  | ✅ Feito | Mesmo fluxo que birthday_customer                                 |
| Controle de duplicidade                                             | ✅ Feito | `campaign_executions` com `reference_period`                      |
| **UI — Parametrizar** pets (birthday_pet): valor do cupom, mensagem | ✅ Feito | Sprint 10 — renderFormCampaign inclui birthday_pet                |
| Mostrar aniversários de pets de hoje no Dashboard                   | ✅ Feito | Incluído em `aniversarios_hoje` (backend combina clientes + pets) |

---

### 1.4 Boas-Vindas — 1ª Compra no App

| Item                                                                          | Status   |
| ----------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------- |
| Tipo `welcome_app` existe no enum                                             | ✅ Feito |
| Worker: disparo no evento de cadastro no app                                  | ✅ Feito | `ecommerce_auth.py` publica `customer_registered` após cadastro — Sprint 11 |
| Worker: gera cupóm de boas-vindas                                             | ✅ Feito | `WelcomeHandler._process()` via `coupon_service`                            |
| Cupom visível em "Meus Cupons" no app                                         | ✅ Feito | `CouponsScreen.tsx` — via aba Benefícios → "Ver todos os cupons"            |
| **UI — Parametrizar** pets (birthday_pet): valor do cupom, mensagem, validade | ✅ Feito | Sprint 10 — renderFormCampaign inclui birthday_pet                          |

---

### 1.5 Boas-Vindas — 1ª Compra no Ecommerce

| Item                                               | Status                 |
| -------------------------------------------------- | ---------------------- | ----------------------------------------------------- |
| Tipo `welcome_ecommerce` existe no enum            | ✅ Feito (placeholder) |
| Worker: disparo no evento de cadastro no ecommerce | ✅ Feito               | Mesmo endpoint `ecommerce_auth.py` — Sprint 11        |
| Ecommerce: CPF obrigatório no cadastro             | ✅ Feito               |
| **UI — Parametrizar**                              | ✅ Feito               | `renderFormCampaign` inclui `welcome` e `welcome_app` |

---

### 1.6 Dashboard de Campanhas

| Item                                                                  | Status   | Detalhe                                                          |
| --------------------------------------------------------------------- | -------- | ---------------------------------------------------------------- |
| Endpoint `GET /campanhas/dashboard` existe                            | ✅ Feito | Retorna dados básicos                                            |
| Seção: campanhas ativas (por nome)                                    | ✅ Feito | Backend retorna `{total, nomes}` — UI exibe lista de nomes       |
| Seção: cupons emitidos/utilizados/expirados hoje                      | ✅ Feito | Dashboard exibe card de cupons ativos no total                   |
| Alertas do dia: aniversariantes de hoje (clientes e pets)             | ✅ Feito | Dashboard endpoint retorna `aniversarios_hoje`                   |
| Alertas do dia: clientes inativos 30d/60d e sorteios pendentes        | ✅ Feito | Sprint 9 — endpoint `alertas`                                    |
| Alertas do dia: brindes pendentes de retirada                         | ✅ Feito | Backend + Lembretes.jsx — card de brindes pendentes              |
| Próximos eventos: aniversários amanhã, fim do mês, sorteios da semana | ✅ Feito | Sprint 9 — endpoint `proximos_eventos`                           |
| Próximos eventos: destaque mensal em X dias                           | ✅ Feito | Card no Dashboard com countdown + alerta amarelo quando ≤ 3 dias |

---

## FASE 2 — Fidelidade e Ranking

### 2.1 Cartão Fidelidade Virtual (Carimbos)

| Item                                                                                                                          | Status   | Detalhe                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------- |
| Modelo `LoyaltyStamp` existe                                                                                                  | ✅ Feito | —                                                                                |
| Endpoint `/campanhas/clientes/{id}/saldo` retorna total de carimbos                                                           | ✅ Feito | —                                                                                |
| Worker: carimbo automático ao registrar venda no PDV                                                                          | ✅ Feito | `LoyaltyHandler` + evento `purchase_completed` em vendas_routes                  |
| Worker: detecta quando cliente completou o cartão e gera recompensa                                                           | ✅ Feito | `LoyaltyHandler._check_completion()` gera cupom de recompensa                    |
| Worker: recompensa intermediária (ex: brinde com 5 carimbos)                                                                  | ✅ Feito | `_give_reward()` suporta tipo "brinde" (sem cupom, só notificação) além de cupom |
| **Lançamento manual de carimbo** (para quem usa cartão físico)                                                                | ✅ Feito | Endpoint `POST /campanhas/carimbos/manual` — Sprint 10                           |
| **UI — Lançamento manual de carimbo** (botão na aba Campanhas — Fidelidade)                                                   | ✅ Feito | Botão "+ Lançar Carimbo Manual" + modal — Sprint 10                              |
| **UI — Parametrizar**: valor mínimo de compra por carimbo, total de carimbos, recompensa ao completar, brindes intermediários | ✅ Feito | Sprint 10 — editor visual com CampanhaField                                      |
| **UI — Parametrizar por nível de ranking**: `rank_filter` (todos/bronze/silver/gold/diamond/platinum)                         | ✅ Feito | Sprint 10 — selector na aba Fidelidade                                           |
| **UI — Lançamento manual no cadastro do cliente** (ClientesNovo.jsx)                                                          | ✅ Feito | Botão "🏷️ Lançar Carimbo" dentro do card de fidelidade                           |

---

### 2.2 Cashback

| Item                                                                                       | Status   | Detalhe                                                                            |
| ------------------------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------- |
| Modelo `CashbackTransaction` existe                                                        | ✅ Feito | —                                                                                  |
| Endpoint de saldo retorna `saldo_cashback`                                                 | ✅ Feito | —                                                                                  |
| Worker: gera cashback automático ao fechar venda                                           | ✅ Feito | `CashbackHandler` + evento `purchase_completed` em vendas_routes                   |
| **Cashback % por nível de ranking**: Bronze 0%, Prata 1%, Ouro 2%, Diamante 3%, Platina 5% | ✅ Feito | Worker CashbackHandler usa `{nivel}_percent` dos params                            |
| **Cashback % por canal**: PDV, App e Ecommerce com percentuais diferentes                  | ✅ Feito | Bônus aditivo: `pdv_bonus_percent`, `app_bonus_percent`, `ecommerce_bonus_percent` |
| Cashback entra no sistema de crédito existente                                             | ✅ Feito | Crédito manual via PDV — não descontado automático por decisão do produto          |
| **UI — Parametrizar % por nível**: tabela editável com Bronze→Platina                      | ✅ Feito | Sprint 10 — grid com CampanhaField para cada nível                                 |
| **UI — Parametrizar % por canal**: PDV / App / Ecommerce                                   | ✅ Feito | Seção de bônus no formulário de cashback em Campanhas.jsx                          |
| Endpoint `GET /campanhas/relatorio` mostra histórico de cashback                           | ✅ Feito | —                                                                                  |

---

### 2.3 Ranking de Clientes (Bronze → Platina)

| Item                                                                                               | Status   | Detalhe                                                                                           |
| -------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------- |
| Modelo `CustomerRankHistory` existe                                                                | ✅ Feito | —                                                                                                 |
| Enum de níveis: bronze, silver, gold, diamond, platinum                                            | ✅ Feito | —                                                                                                 |
| Endpoint `GET /campanhas/ranking` retorna clientes por nível                                       | ✅ Feito | —                                                                                                 |
| Endpoint `GET /campanhas/clientes/{id}/saldo` retorna `rank_level`                                 | ✅ Feito | —                                                                                                 |
| Badge de ranking no PDV (painel do cliente)                                                        | ✅ Feito | —                                                                                                 |
| Badge de ranking no cadastro do cliente                                                            | ✅ Feito | —                                                                                                 |
| Recalculo mensal automático (job scheduler)                                                        | ✅ Feito | `monthly_ranking_recalc` — dia 1 às 06:00 via `RankingHandler`                                    |
| **Critérios de ranking parametrizáveis**: gasto acumulado 12 meses, nº de compras, meses distintos | ✅ Feito | `_calculate_rank()` lê `params.get(…, default)` — `GET/PUT /ranking/config` persistêm os limiares |
| **UI — Configurar critérios por nível**: tabela gasto mínimo, nº compras, meses ativos             | ✅ Feito | Aba Ranking — tabela editável `silver_min_spent`, `gold_min_spent` etc.                           |
| **UI — Configurar benefícios por nível**: cashback %, regra do carimbo, acesso a sorteio           | ✅ Feito | Seção colapsável "📊 Benefícios por Nível" na aba Ranking com tabela de critérios por nível       |
| **Envio em lote por nível**: filtrar clientes Ouro → escrever mensagem → enviar e-mail para todos  | ✅ Feito | Sprint 10 — modal na aba Ranking + `POST /ranking/envio-em-lote`                                  |
| Backend: endpoint `POST /campanhas/ranking/envio-em-lote`                                          | ✅ Feito | Sprint 10 — usa idempotency_key + email_address                                                   |
| Backend: endpoint `POST /campanhas/ranking/recalcular` (forçar recalculo)                          | ✅ Feito | Sprint 10 — botão "Recalcular Agora" na aba Ranking                                               |

---

### 2.4 Sorteios por Nível de Ranking

| Item                                                                                              | Status   | Detalhe                                                                          |
| ------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------- |
| Modelos `Drawing` e `DrawingEntry` existem                                                        | ✅ Feito | —                                                                                |
| Endpoint `GET /campanhas/sorteios` (listar sorteios)                                              | ✅ Feito | —                                                                                |
| Endpoint `POST /campanhas/sorteios` (criar sorteio)                                               | ✅ Feito | —                                                                                |
| Endpoint `PUT /campanhas/sorteios/{id}` (editar sorteio: nível elegível, prêmio, data)            | ✅ Feito | —                                                                                |
| Endpoint `POST /campanhas/sorteios/{id}/inscrever` (inscrever clientes elegíveis automaticamente) | ✅ Feito | —                                                                                |
| Endpoint `POST /campanhas/sorteios/{id}/executar` (executar sorteio com seed auditável)           | ✅ Feito | —                                                                                |
| Endpoint `GET /campanhas/sorteios/{id}/resultado` (ver ganhador, lista de inscritos)              | ✅ Feito | —                                                                                |
| Sorteio automático no dia configurado                                                             | ✅ Feito | Backend: job `_auto_execute_drawings` (10h diário) + campo `auto_execute` na UI  |
| Sorteio manual: gerar lista de códigos por nível para sorteio offline                             | ✅ Feito | Backend: `GET /sorteios/{id}/codigos-offline` + botão "📋 Códigos Offline" na UI |
| Comunicar ganhador: e-mail + push                                                                 | ✅ Feito | E-mail enviado via `enqueue_email` após execução do sorteio                      |
| **UI — Aba Sorteios** (criar, editar, executar, ver resultado)                                    | ✅ Feito | Sprint 7 — aba completa no Campanhas.jsx                                         |
| **UI — Configurar: nível elegível (Prata+, Ouro+…), prêmio, data, modo (automático ou manual)**   | ✅ Feito | —                                                                                |

---

## FASE 3 — Retenção, Destaque Mensal e Recursos Avançados

### 3.1 Campanhas de Retenção (Clientes Inativos)

| Item                                                                                      | Status                 | Detalhe                                                              |
| ----------------------------------------------------------------------------------------- | ---------------------- | -------------------------------------------------------------------- |
| Tipo `inactivity` existe no enum                                                          | ✅ Feito (placeholder) | —                                                                    |
| Backend: CRUD dinâmico de campanhas de retenção (criar, editar, excluir)                  | ✅ Feito               | Endpoints `GET/POST/PUT/DELETE /campanhas/retencao`                  |
| Worker: job diário que detecta clientes sem compra há X dias                              | ✅ Feito               | `InactivityHandler` + `weekly_inactivity_check` — toda segunda 09:00 |
| Worker: gera cupom de desconto e envia notificação                                        | ✅ Feito               | `InactivityHandler._reward_customer()` via coupon_service            |
| Controle de "já enviou" (não reenviar na mesma "rodada")                                  | ✅ Feito               | `campaign_executions` com `reference_period`                         |
| **UI — Lista dinâmica com botão +**: adicionar múltiplas regras (30d, 60d, 90d…)          | ✅ Feito               | Aba "🔄 Retenção" em Campanhas.jsx — Sprint 11                       |
| **UI — Parametrizar cada regra**: dias de inatividade, valor do cupom, validade, mensagem | ✅ Feito               | Sprint 10 — editor visual com CampanhaField                          |

---

### 3.2 Campanhas de Destaque Mensal

| Item                                                                                              | Status   | Detalhe                                                                        |
| ------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------ |
| Tipo `ranking_monthly` existe (mas é o ranking, não o destaque)                                   | ✅ Feito | Campanha `ranking_monthly` com parâmetro `auto_destaque_mensal`                |
| Backend: endpoint `GET /campanhas/destaque-mensal/calcular` (calcular vencedores do mês anterior) | ✅ Feito | Sprint 6                                                                       |
| Lógica anti-duplicidade: cliente ganha no máximo 1 brinde neste grupo/mês                         | ✅ Feito | `meta_key = destaque:{periodo}:{categoria}`                                    |
| Lógica de desempate: se 1º já foi premiado em outra categoria, usa o 2º colocado                  | ✅ Feito | `desempate_info` retornado e exibido na UI da aba Destaque Mensal              |
| Três categorias: maior gasto, mais compras                                                        | ✅ Feito | Terceira categoria (mais unidades) descartada por decisão do produto           |
| Endpoint `POST /campanhas/destaque-mensal/enviar` (enviar para vencedores)                        | ✅ Feito | Sprint 6 — aceita `tipo_premio` (cupom ou mensagem)                            |
| Envio automático no dia 1 (configurável) OU envio manual com confirmação                          | ✅ Feito | Job `_auto_enviar_destaque_mensal` (dia 1 às 08h) com configuração             |
| Mensagem de brinde com prazo de retirada (ex: "retire do dia 3 ao dia 10")                        | ✅ Feito | Sprint 9 — campos `retirar_de` / `retirar_ate`                                 |
| **UI — Ver vencedores sugeridos** com Top 5 de cada categoria                                     | ✅ Feito | Aba Destaque Mensal em Campanhas.jsx                                           |
| **UI — Painel de configuração de prêmio** (cupom OU brinde na loja + datas + mensagem editável)   | ✅ Feito | Sprint 9 — sessão atual                                                        |
| **UI — Configurar envio automático vs manual**                                                    | ✅ Feito | Toggle `auto_destaque_mensal` + valor e validade do cupom na aba Configurações |

---

### 3.3 Campanha de Recompra Rápida

| Item                                                              | Status                 | Detalhe                                                                   |
| ----------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------- |
| Tipo `quick_repurchase` existe no enum                            | ✅ Feito (placeholder) | —                                                                         |
| Worker: ao fechar venda, envia cupom único com validade de X dias | ✅ Feito               | `QuickRepurchaseHandler` + evento `purchase_completed` em vendas_routes   |
| Controle: não reenviar se já tem cupom ativo da mesma campanha    | ✅ Feito               | `campaign_executions` com UNIQUE por (tenant, campanha, cliente, período) |
| **UI — Parametrizar**: janela em dias, valor do cupom, validade   | ✅ Feito               | Sprint 10 — editor visual com CampanhaField                               |

---

### 3.4 Unificação via CPF Cross-Canal

| Item                                                                                              | Status      | Detalhe                                  |
| ------------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------- |
| PDV: campo CPF existe                                                                             | ✅ Feito    | Opcional                                 |
| App: campo CPF no cadastro                                                                        | ✅ Feito    | Sprint 8 — RegisterScreen.tsx            |
| Ecommerce: CPF obrigatório no cadastro                                                            | ✅ Feito    | Sprint 9 — validação + mínimo 11 dígitos |
| Backend: endpoint `GET /campanhas/unificacao/sugestoes` (compara nome+fone+email e sugere merges) | ✅ Feito    | Sprint 8                                 |
| Backend: endpoint `POST /campanhas/unificacao/confirmar` (merge manual com confirmação)           | ✅ Feito    | Sprint 8                                 |
| Backend: endpoint `DELETE /campanhas/unificacao/{id}` (desfazer merge)                            | ✅ Feito    | Sprint 8                                 |
| Após merge: todo histórico cross-canal conta junto para campanhas                                 | ✅ Feito    | Merge transfere Vendas + CampaignExecution + EventQueue; rollback também restaura os três |
| **UI — Tela de sugestões de unificação** (aba 🔗 Unificação em Campanhas.jsx)                     | ✅ Feito    | Sprint 8                                 |

---

## FASE 4 — Notificações e Canais

### 4.1 Sistema de Notificações

| Item                                                                       | Status      | Detalhe                                                                        |
| -------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------ |
| Modelos `NotificationQueue` e `NotificationLog` existem                    | ✅ Feito    | —                                                                              |
| E-mail: infraestrutura configurada                                         | ✅ Feito    | Provedor cadastrado, funciona                                                  |
| Push FCM: configurado                                                      | ✅ Feito    | —                                                                              |
| Worker real de despacho de e-mails (consome NotificationQueue e envia)     | ✅ Feito    | `NotificationSender.process_batch()` SMTP real, a cada 5 min                   |
| Worker real de despacho de push FCM                                        | ❌ Pendente | App ainda não publicado na Play Store (testar com EAS Preview APK)             |
| Template de e-mail por tipo de campanha (aniversário, boas-vindas, cupom…) | ✅ Feito    | `_render_email_html()` com cores distintas por tipo de campanha                |
| Envio escalonado em lotes (ex: 50 e-mails a cada 30 min) para evitar spam  | ✅ Feito    | BATCH_SIZE=50 em `notification_sender.py`                                      |
| **UI — Configurar horário de envio** preferencial por tipo de campanha     | ✅ Feito    | Aba Configurações — tabela de horários por tipo de campanha (scheduler config) |

---

### 4.2 Canais — PDV, App, Ecommerce

| Item                                                         | Status            | Detalhe                                                                            |
| ------------------------------------------------------------ | ----------------- | ---------------------------------------------------------------------------------- |
| Cupom: campo canal (PDV / app / ecommerce / todos)           | ✅ Feito (modelo) | —                                                                                  |
| PDV: campo para digitar código de cupóm na venda             | ✅ Feito          | PDV.jsx: `codigoCupom`, `aplicarCupom()`, card "Cupóm de desconto"                 |
| PDV: validação e aplicação automática do cupóm               | ✅ Feito          | Endpoint de resgate encadeado na finalização                                       |
| App: aba "Meus Cupons" com lista de cupons ativos do cliente | ✅ Feito          | `CouponsScreen.tsx` — acessível via aba Benefícios                                 |
| App: QR code do cupom para mostrar no caixa                  | ✅ Feito          | `CouponsScreen.tsx`: botão "Mostrar QR Code" + modal com `react-native-qrcode-svg` |
| Ecommerce: campo de cupóm no checkout                        | ✅ Feito          | `ecommerce_checkout.py`: campo `cupom` no payload                                  |
| Ecommerce: validação e aplicação do desconto                 | ✅ Feito          | `_calcular_desconto()` aplica o cupom antes de fechar o pedido                     |

---

## FASE 5 — Polimento e Integrações

### 5.1 Gestão de Cupons (UI Completa)

| Item                                                                  | Status                          |
| --------------------------------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------- |
| Listar todos os cupons com status (ativo/utilizado/expirado)          | ✅ Feito                        | Aba Cupons com filtros de status (ativo/usado/expirado/cancelado/todos) |
| Filtrar por campanha, data, cliente específico                        | ✅ Feito                        | Dropdown de campanha + datas de criação + campo de busca                |
| Ver detalhes do cupom: quando criado, quando usado, por qual campanha | ✅ Feito                        | Detalhe expande com `created_at`, `valid_until`, `used_at`, campanha    |
| Criar cupom manual (casos especiais, sem vínculo com campanha)        | ✅ Feito (endpoint + UI básica) |
| Anular/cancelar cupom                                                 | ✅ Feito                        | Sprint 9 — botão 🚫 na tabela + `DELETE /campanhas/cupons/{code}`       |

---

### 5.2 Lembretes Integrados

| Item                                                              | Status   |
| ----------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------- |
| Mostrar aniversários amanhã na aba de Lembretes existente         | ✅ Feito | Lembretes.jsx usa `proximos_eventos.aniversarios_amanha`                                           |
| Mostrar sorteios agendados para os próximos X dias                | ✅ Feito | Card "Sorteio(s) esta semana" em Lembretes.jsx                                                     |
| Mostrar brindes pendentes de retirada (campanhas destaque mensal) | ✅ Feito | Card "🎁 Brinde(s) pendente(s)" em Lembretes.jsx via `alertas.total_brindes_pendentes`             |
| Mostrar clientes que atingiram inatividade hoje                   | ✅ Feito | Card "🚨 Atingiram 30 dias de inatividade hoje" em Lembretes.jsx via `alertas.novos_inativos_hoje` |

---

## Prioridade de Execução Recomendada

```
SPRINT 5 — Worker + Sazonais + Parametrização básica
  1. Criar tabela campanha_cliente_log (pré-requisito para tudo)
  2. Worker: job diário (aniversários de clientes)
  3. Worker: job diário (aniversários de pets)
  4. Worker: cashback automático ao registrar venda
  5. Worker: carimbo automático ao registrar venda + detectar cartão completo
  6. UI: parametrizar Cartão Fidelidade (valor/carimbo, total carimbos, recompensa)
  7. UI: parametrizar Cashback (% por nível de ranking, % por canal)
  8. UI: parametrizar campanhas sazonais (valor cupom, mensagem, validade)
  9. Backend: POST /campanhas/carimbos/manual + UI de lançamento manual

SPRINT 6 — Retenção + Destaque Mensal + Recompra Rápida
  1. CRUD dinâmico de campanhas de retenção (backend + UI com botão +)
  2. Worker: inatividade (job diário, lógica de não-duplicidade)
  3. Backend + UI: destaque mensal (calcular vencedores, anti-duplicidade, enviar)
  4. Worker: recompra rápida (ao fechar venda → cupom de retorno)
  5. Backend: recalculo de ranking (job mensal) + endpoint forçar recalculo
  6. UI: configurar critérios de ranking por nível
  7. UI: configurar benefícios por nível (cashback %, regra carimbo, sorteio)

SPRINT 7 — Sorteios + Envio em Lote + Notificações
  1. Backend: CRUD completo de sorteios (criar, inscrever, executar, resultado)
  2. Backend: sorteio com seed auditável + lista para sorteio offline
  3. UI: Aba Sorteios completa no Campanhas.jsx
  4. Backend: POST /campanhas/ranking/envio-em-lote
  5. UI: Envio em lote por nível (filtrar → mensagem → enviar)
  6. Worker real de despacho de e-mails (consome NotificationQueue)
  7. Templates de e-mail por tipo de campanha

SPRINT 8 — Canais + App + Ecommerce  ✅ CONCLUÍDO
  1. ✅ App: campo CPF no cadastro (RegisterScreen.tsx + auth.service.ts + auth.store.ts)
  2. ✅ App: aba "Meus Cupons" (CouponsScreen.tsx + aba no MainNavigator.tsx)
  3. ✅ PDV: campo de cupom na tela de venda + validação/aplicação (pré-existente)
  4. ✅ Ecommerce: CPF obrigatório + campo cupom no checkout (pré-existente)
  5. ✅ Backend: unificação via CPF (GET /unificacao/sugestoes, POST /confirmar, DELETE /{id})
  6. ✅ UI: tela de sugestões de unificação (aba 🔗 Unificação em Campanhas.jsx)

SPRINT 9 — Dashboard completo + Lembretes + Polimento  ✅ CONCLUÍDO
  1. ✅ Dashboard: alertas do dia (inativos 30d/60d, sorteios pendentes)
  2. ✅ Dashboard: próximos eventos (aniversariantes amanhã, fim do mês, sorteios da semana)
  3. ✅ Lembretes integrados: alertas de campanhas em Lembretes.jsx (aniversários, inativos, sorteios, destaque mensal)
  4. ✅ Cupons: anulação (botão 🚫 Anular na tabela + endpoint DELETE /campanhas/cupons/{code})
  5. ✅ Envio escalonado frontend: botão + modal em cards de inativos 30d/60d (POST /campanhas/notificacoes/inativos)
  6. ✅ Destaque Mensal: painel de configuração de prêmio (cupom OU brinde na loja, datas de retirada, mensagem editável)
  7. ✅ Bugs 500 corrigidos: timeline do cliente (timezone naive/aware) + whatsapp/ultimas (tabela não migrada)
  8. ✅ Loyalty rank_filter: parâmetro "Quem participa?" no editor de campanhas fidelidade
  9. ✅ Destaque Mensal por vencedor: prêmio e mensagem individuais + checkbox de seleção

SPRINT 10 — UI Parametrização + PDV Cupom + Carimbo Manual ✅ CONCLUÍDO
  1. ✅ UI: editor visual Aniversário (cliente e pet) — campos coupon_type, coupon_value, coupon_valid_days, notification_message
  2. ✅ UI: editor visual Cartão Fidelidade — campos min_purchase, stamps_to_complete, reward_type, reward_value, coupon_days_valid, rank_filter
  3. ✅ UI: editor visual Cashback — tabela de % por nível (Bronze→Platina) com grid
  4. ✅ Backend: POST /campanhas/carimbos/manual + UI de lançamento (botão "Lançar Carimbo Manual" na aba Fidelidade de Campanhas.jsx)
  5. ✅ PDV: campo de cupom na tela de venda (digitar código → aplicar → desconto automático com removerCupom)
  6. ✅ UI: configurar critérios de ranking por nível — aba Ranking em Campanhas.jsx com GET/PUT /ranking/config
  7. ✅ Backend + UI: POST /campanhas/ranking/recalcular + botão "Recalcular Agora" na aba Ranking
  8. ✅ Backend + UI: POST /campanhas/ranking/envio-em-lote + modal de envio por nível na aba Ranking

SPRINT 11 — Boas-Vindas, Cashback por Canal, Triggers Pendentes
  1. ✅ App Mobile: publicar evento `customer_registered` ao cadastrar — Sprint 11
  2. ✅ Ecommerce: publicar evento `customer_registered` ao cadastrar — Sprint 11
  3. ✅ Cashback % por canal (PDV / App / Ecommerce com percentuais independentes)
  4. ✅ Retenção dinâmica: CRUD de regras (30d / 60d / 90d) + aba UI em Campanhas.jsx
  5. ✅ Critérios de ranking parametrizáveis (gasto mín., nº compras, meses ativos) — `_calculate_rank()` já lê de `params`
  6. ✅ Botão "Lançar Carimbo" no cadastro do cliente (ClientesNovo.jsx) — já implementado
  7. ✅ Destaque Mensal: aviso de desempate na UI — bloco ⊠ Desempate aplicado mostra nome do pulado, eleito e posição
  8. ✅ Gestor de Benefícios: aba completa com modo Por Cliente e Por Campanha (carimbos/cashback/cupons/ranking)
  8. ✅ Aniversariantes de hoje: exibir lista no Dashboard — já implementado (UI + backend)
```

---

## Resumo de Endpoints Que Precisam Ser Criados

```
GET    /campanhas/sorteios                       → Listar sorteios
POST   /campanhas/sorteios                       → Criar sorteio
PUT    /campanhas/sorteios/{id}                  → Editar sorteio
POST   /campanhas/sorteios/{id}/inscrever        → Inscrever clientes elegíveis
POST   /campanhas/sorteios/{id}/executar         → Executar sorteio (seed auditável)
GET    /campanhas/sorteios/{id}/resultado        → Ver ganhador e inscritos
GET    /campanhas/retencao                       → Listar campanhas de retenção
POST   /campanhas/retencao                       → Criar campanha de retenção
PUT    /campanhas/retencao/{id}                  → Editar campanha de retenção
DELETE /campanhas/retencao/{id}                  → Excluir campanha de retenção
```

Endpoints já implementados (não precisam ser criados):

```
✅ POST   /campanhas/carimbos/manual
✅ POST   /campanhas/ranking/recalcular
✅ POST   /campanhas/ranking/envio-em-lote
✅ GET    /campanhas/destaque-mensal/calcular
✅ POST   /campanhas/destaque-mensal/enviar
✅ GET    /campanhas/unificacao/sugestoes
✅ POST   /campanhas/unificacao/confirmar
✅ DELETE /campanhas/unificacao/{id}
✅ DELETE /campanhas/cupons/{code}
```

---

## Telas Que Precisam Ser Criadas ou Completadas

| Tela                                                                     | Onde             | Status                                               |
| ------------------------------------------------------------------------ | ---------------- | ---------------------------------------------------- |
| Campanhas.jsx — Dashboard completo (alertas, próximos eventos)           | frontend         | ✅ Feito — Sprint 9                                  |
| Campanhas.jsx — Aba Sorteios (criar, executar, resultado)                | frontend         | ✅ Feito — Sprint 7                                  |
| Campanhas.jsx — Campanhas Sazonais (config individual por tipo)          | frontend         | ✅ Feito — `renderFormCampaign` cobre todos os tipos |
| Campanhas.jsx — Retenção dinâmica (lista + botão +)                      | frontend         | ✅ Feito — Sprint 11                                 |
| Campanhas.jsx — Destaque Mensal (vencedores + painel de prêmio + enviar) | frontend         | ✅ Feito — Sprint 9                                  |
| Campanhas.jsx — Configurar Cartão Fidelidade (parâmetros completos)      | frontend         | ✅ Feito — Sprint 10                                 |
| Campanhas.jsx — Configurar Cashback (% por nível + % por canal)          | frontend         | ✅ Feito — Sprint 10                                 |
| Campanhas.jsx — Configurar Ranking (critérios + benefícios por nível)    | frontend         | ✅ Feito — Sprint 10                                 |
| Campanhas.jsx — Envio em lote por nível                                  | frontend         | ✅ Feito — Sprint 10                                 |
| Campanhas.jsx — Carimbo manual (botão + modal)                           | frontend         | ✅ Feito — Sprint 10                                 |
| Campanhas.jsx — Recompra Rápida (config)                                 | frontend         | ✅ Feito — Sprint 10                                 |
| PDV — Campo de cupom na venda                                            | PDV.jsx          | ✅ Feito — Sprint 10                                 |
| Cadastro cliente — Lançar carimbo manualmente                            | ClientesNovo.jsx | ✅ Feito — Sprint 11                                 |
| App Mobile — Campo CPF no cadastro                                       | app-mobile       | ✅ Feito — Sprint 8                                  |
| App Mobile — Aba "Meus Cupons" + QR code                                 | app-mobile       | ✅ Feito — Sprint 8                                  |
| Ecommerce — CPF obrigatório + cupom no checkout                          | ecommerce        | ✅ Feito — Sprint 9                                  |
| Unificação cross-canal — Tela de sugestões                               | frontend         | ✅ Feito — Sprint 8                                  |

---

## SPRINT 12 — App Mobile: Painel de Benefícios do Cliente

> **Objetivo:** O cliente abre o app e vê, em uma tela só, tudo o que tem e o que pode conquistar.

### 12.1 Tela "Meus Benefícios" no App Mobile

| Item                                                                                 | Status    | Detalhe                                                                                          |
| ------------------------------------------------------------------------------------ | --------- | ------------------------------------------------------------------------------------------------ |
| **Backend:** endpoint `GET /ecommerce/auth/meus-beneficios` — retorna saldo completo | ✅ Pronto | Retorna carimbos, saldo cashback, ranking com thresholds, cupons ativos — em `ecommerce_auth.py` |
| **App:** tela `BeneficiosScreen.tsx` com 4 blocos                                    | ✅ Pronto | `app-mobile/src/screens/benefits/BeneficiosScreen.tsx` — 4 seções implementadas                  |
| **App:** Bloco Carimbos — mostrar N/Total carimbos + barra visual de carimbos        | ✅ Pronto | `SecaoCarimbos`: grid de carimbos, texto "X de Y" e info de compra mínima                        |
| **App:** Bloco Cashback — mostrar saldo disponível em reais                          | ✅ Pronto | `SecaoCashback`: mostra saldo e lista de transações                                              |
| **App:** Bloco Ranking — mostrar categoria atual com badge colorido                  | ✅ Pronto | `SecaoRanking`: badge colorido por nível, nome em pt-BR, gasto total                             |
| **App:** Bloco Ranking — barra de progresso para próximo nível + o que falta         | ✅ Pronto | Barra de progresso + texto "Faltam R$ X para [Próximo Nível]"                                    |
| **App:** Bloco Vantagens por nível — lista com checkmarks por categoria              | ✅ Pronto | `NIVEL_VANTAGENS`: lista de strings por nível, renderizado com ✓ colorido                        |
| **App:** Navegação — aba "Benefícios" no `MainNavigator.tsx`                         | ✅ Pronto | Tab registrada com ícone `gift-outline` e título "Benefícios"                                    |

### 12.2 Backend — endpoint `/app/meu-painel`

O endpoint precisa retornar, para o cliente autenticado via CPF no app:

```
{
  "carimbos": {
    "ativos": 7,
    "total_para_completar": 10,
    "faltam": 3
  },
  "cashback": {
    "saldo": 12.50
  },
  "ranking": {
    "nivel_atual": "bronze",
    "label": "Bronze",
    "pontos_atuais": 420,
    "pontos_proximo_nivel": 500,
    "faltam_pontos": 80,
    "proximo_nivel": "prata",
    "proximo_nivel_label": "Prata"
  },
  "vantagens": [
    { "nivel": "bronze",  "label": "Bronze",  "vantagens": ["Cashback básico em todas as compras", "Participa do Cartão Fidelidade"] },
    { "nivel": "prata",   "label": "Prata",   "vantagens": ["Cashback maior", "Participa de sorteios mensais", "Cupom de aniversário especial"] },
    { "nivel": "ouro",    "label": "Ouro",    "vantagens": ["Cashback alto", "Sorteios com prêmios melhores", "Brinde mensal na loja"] },
    { "nivel": "platina", "label": "Platina", "vantagens": ["Cashback máximo", "Sorteios exclusivos Platina", "Destaque do mês", "Atendimento prioritário"] }
  ]
}
```

### 12.3 Prioridade de execução

```
1. Backend: GET /app/meu-painel (lê carimbos, cashback, ranking do cliente logado)
2. App: BenefitsScreen.tsx (4 blocos: carimbos, cashback, ranking, vantagens)
3. App: MainNavigator.tsx — adicionar aba "⭐ Benefícios"
```

---

_Documento gerado em Março 2026 — atualizar à medida que itens forem concluídos._
