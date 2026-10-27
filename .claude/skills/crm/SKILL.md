---
name: crm
description: Use ao mexer no módulo CRM do tutor (/crm): funil de leads (Kanban), ficha 360, conversas de WhatsApp ligadas ao lead, multi-loja, permissões crm.* ou nas tabelas crm_*.
---

# CRM do tutor

Fonte de verdade simplificada do módulo CRM. O planejamento completo, as decisões e o andamento por etapa ficam em `docs/crm/ROADMAP.md` (documento vivo); as regras de negócio em `docs/crm/CONTRATOS_CONCEITUAIS.md`; o protótipo aprovado (v11, congelado) em `docs/crm/prototipo/crm-prototipo.html`.

## Objetivo

Relacionamento com o tutor por loja: funil de leads em quadro, ficha 360 (compras, pets, vacinas, contatos), conversa por WhatsApp com IA e atendente humano, e oportunidades geradas por sinais do sistema.

## Identificação

- Módulo: `crm` (fora da oferta pública e de contratação separada até decidir planos e preço — ROADMAP 1.2). Não entra em beta, teste completo nem planos "todos os módulos".
- Rota frontend: `/crm` (`frontend/src/pages/crm/`: `CrmPage` + `useCrmQuadro` (dados e filtro de lojas), `CrmQuadro`/`CrmColuna`/`CrmCard` (arrastar pela alça, dnd-kit), modais `CrmFichaModal`, `CrmNovoCardModal`, `CrmConcluirModal`, `CrmColunasModal`, `crmUtils.js` testado em Node; rota em rota em `app/routes/DeliveryAiRoutes.jsx`, menu em `components/layout/menuConfig.js`).
- Permissões: `crm.visualizar`, `crm.atender`, `crm.leads`, `crm.configurar`, `crm.todas_lojas` (migração `zzzzl20261022a1`; perfil Gerente padrão recebe todas; quem tinha `ia.whatsapp` recebeu o backfill).

## Backend

- Pacote `backend/app/crm/`:
  - `models.py` — tabelas `crm_funis`, `crm_colunas`, `crm_leads`, `crm_oportunidades`, `crm_movimentacoes`, `crm_interacoes`, `crm_acoes`, `crm_proximos_passos` (migração `zzzzm20261022a1`, todas com RLS por loja).
  - `lojas.py` — multi-loja: `lojas_permitidas`, `resolver_lojas`, `consultar_por_loja`. Cada consulta roda em UMA loja por vez e marca `loja_id`/`loja_nome`.
  - `leads_service.py` — funil padrão sob demanda e `identificar_ou_criar_lead`.
  - `funil_service.py` — regras: colunas (1 entrada, 1 concluído, máx. 8), mover card, ciclos, oportunidades (`registrar_sinal`).
  - `acoes_service.py` — criar card, registrar ação, agendar passo, ficha, buscar pessoa e vincular a cadastro.
  - `quadro_service.py` — leitura do quadro de uma loja (50 cards por coluna; card sem telefone).
  - `routes.py` — `/crm/lojas`, `/crm/quadro`, `/crm/tutores`, `/crm/leads` (+ `/mover`, `/acoes`, `/proximo-passo`, `/vincular`), `PUT /crm/funil/colunas`. Router montado em `main_routers.py` com o módulo `crm` exigido; cada rota age em UMA loja e confere a permissão nela.
- Canal oficial da Meta (decidido em 26/10): `app/whatsapp/meta_cloud.py` (cliente e tradução de erros), `app/routers/whatsapp_meta.py` (`/whatsapp/config/meta`: estado, credenciais, testar, inscrever-app, ativar; exige módulo `crm` e `crm.configurar`), colunas `meta_*` em `tenant_whatsapp_config`. O token tem coluna própria e salvar credenciais NUNCA troca o provedor em uso; só `/ativar` (após teste ok). O POST do webhook da Meta é autenticado só pela assinatura com a chave secreta do app (o token de verificação serve só ao GET). Página de apoio: `frontend/src/pages/crm/ConectarWhatsAppPage.jsx` (textos em `guiaMeta.js`).
- Conversas de WhatsApp: `backend/app/whatsapp/` (webhook, processor, handoff, websocket). A criação de uma sessão nova registra o card do tutor quando o CRM está ativo na loja.

## Regras que não são óbvias

- **Loja = tenant.** O CRM é por loja; ver várias lojas exige `crm.todas_lojas`, vínculo ativo, `crm.visualizar` e módulo ativo em cada uma. Nunca consultar duas lojas na mesma query.
- **Um card por tutor por loja** (índices únicos parciais); exceção: cards separados (`separado_de_lead_id`).
- **Telefone:** identificar o tutor sempre por `app/whatsapp/customer_lookup.py` (nunca chutar). Ambíguo ou desconhecido = card sem cadastro; identificador `@lid` não vira card.
- **Não confundir** `crm_*` com a tabela `opportunities` (sugestões de venda no PDV).
- **Cores:** o que pede atenção usa amarelo/laranja/vermelho; informativo usa azul/verde/rosa/roxo.
- Telas novas usam só componentes v2 (`frontend/src/components/v2/`); 3+ ações em linha usam `BotaoMenuAcoes`.

## Testes

`backend/tests/unit/test_crm_*.py` (registro do módulo, modelo/migração, multi-loja, identificação do tutor) e `tests/test_permission_catalog_migration_contract.py`.

## Pendências de decisão

Ver as marcas `[?] DECIDIR` no ROADMAP (planos e preço, colunas iniciais do funil, convivência com Lembretes e o dashboard de WhatsApp, conexão do número por loja, créditos de IA).
