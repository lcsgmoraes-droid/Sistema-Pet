---
tipo: seguranca
atualizado: 2026-09-21
---

# Terceiros e fluxos de dados — índice para a Política de Privacidade

Parte do eixo [[Seguranca]]. Este documento é a base viva para manter a
Política de Privacidade (`frontend/src/pages/LegalPage.jsx`, seção 10 —
"Fornecedores, destinatários e integrações") correta sem precisar varrer o
sistema inteiro (backend, frontend, app mobile) toda vez que alguém quiser
saber "quem recebe dado de quem hoje". Ver também [[Integracoes]],
[[OpenAI-IA]], [[Vulnerabilidades]], [[EmpresaGrupo]] (consentimento de
compartilhamento entre lojas do mesmo Grupo Comercial, que não é um
terceiro, mas é tratado aqui por ser outro destinatário novo de dados).

## Como manter este documento atualizado

Toda vez que um código novo passar a enviar dado do usuário, cliente, tutor
ou pet — de forma deliberada (integração nova) ou incidental (biblioteca que
chama um domínio externo por baixo) — para fora do próprio backend:

1. Adicionar uma linha na tabela correspondente abaixo (Backend/Frontend/Mobile), com arquivo:linha e o dado exato enviado.
2. Marcar o status: ✅ já refletido na política vigente | ⚠️ política cobre de forma genérica mas não nomeia o provedor | 🔴 não documentado.
3. Se o status for ⚠️ ou 🔴, revisar se a seção 10 de `LegalPage.jsx` precisa de uma frase nova — não precisa reescrever a política inteira, só ajustar a lista de destinatários.

## Backend

| Serviço | Onde no código | Dado enviado | Status na política |
|---|---|---|---|
| Groq (`llama-3.3-70b-versatile`) | `backend/app/cliente_info_pdv_chat.py:327-346` (chat IA do PDV) e `backend/app/veterinario_ia.py:642-706` (copiloto clínico) | Nome, CPF/CNPJ, telefone, cidade e histórico de compras do cliente (PDV); espécie, peso, alergias, doenças crônicas, medicamentos em uso e histórico clínico do pet (veterinário) | ✅ nomeado na seção 10 desde a versão 21/09/2026 |
| Google Gemini (`gemini-1.5-flash`) | Mesmos dois arquivos, usado como terceira opção quando não há `GROQ_API_KEY` nem `OPENAI_API_KEY` | Mesmo dado do item acima | ✅ nomeado na seção 10 desde a versão 21/09/2026 |
| OpenAI (chat/completions e responses API) | Mesmos dois arquivos, segunda opção de fallback (entre Groq e Gemini) | Mesmo dado do item acima | ✅ seção 10 agora detalha que o contexto inclui CPF/CNPJ e dado de saúde do pet |
| OpenAI (Vision, via `image_url`) | `backend/app/veterinario_exames_arquivos.py:114-182` | Imagem do exame/laudo do pet, enviada como `data:` URL para leitura de achados | ✅ "leitura de exame por imagem" citada como recurso na seção 10 |
| Mercado Pago | `backend/app/services/mercado_pago_checkout.py:99-127` (`build_preference_payload`) | `endereco_entrega` completo do pedido, junto com valor, forma de pagamento e identificadores, no metadata da preference | ✅ seção 10 agora cita "incluindo endereço de entrega quando houver" |
| Asaas | `backend/app/services/asaas_billing_service.py` | Identificação da empresa, contato de cobrança, valor, vencimento e status da assinatura | ✅ já nomeado na seção 10 |
| Bling, iFood, SEFAZ/IntNFe, EcommerceAI, WhatsApp (Meta/360dialog/WAHA), SMTP, Expo Push, Apple/Google push, Google Maps (geocodificação de rota) | Ver [[Integracoes]] | Produto/estoque/pedido/documento fiscal (Bling, iFood, fiscal); contato e conteúdo de mensagem (WhatsApp/SMTP); token de dispositivo (push); endereço/coordenadas (Google Maps) | ✅ já nomeados na seção 10 |

## Frontend (`frontend/`)

| Serviço | Onde no código | Dado enviado | Status na política |
|---|---|---|---|
| Google Analytics 4 | `frontend/index.html:52-70` carrega `gtag.js` com o ID de `frontend/.env.production` (`VITE_GA_MEASUREMENT_ID=G-WPC2ZCFNWW`, **arquivo versionado no git**, usado pelo build real de produção) | IP, user-agent, cookies `_ga`/`_gid`, `page_view` (URL completa), termo de busca, e eventos de carrinho/compra da loja online — inclusive `transaction_id` (`pedido_id`) | ⚠️ nomeado na seção 10 desde 21/09/2026, mas **ainda carrega sem consentimento prévio** (sem banner de cookies) e o `.env.production` **continua versionado no git** — pendência técnica, não de texto |
| Google Fonts | `frontend/index.html:41-46` (`fonts.googleapis.com`, `fonts.gstatic.com`) | IP e user-agent, em toda tela — ERP administrativo e loja online | ✅ citado na seção 10 desde 21/09/2026 |
| ViaCEP | `frontend/src/hooks/useClientesNovoEnderecos.js:41`, `useClientesNovoCadastro.js:218`, `usePDVEndereco.js:38`, `pages/ecommerce/ecommerceMvpUtils.js:127`, `pages/configuracoes/entregasConfig/useEntregasConfigController.js:55` | CEP digitado pelo cliente/atendente, chamado direto do navegador (sem passar pelo backend) | ✅ citado na seção 10 desde 21/09/2026 |
| BrasilAPI | `frontend/src/pages/configuracoes/ConfiguracaoFiscalEmpresa.jsx:226` | CNPJ da empresa, direto do navegador | ✅ citado na seção 10 desde 21/09/2026 |
| OpenStreetMap (tiles do Leaflet) | `frontend/src/pages/entregas/RastreioPublico.jsx:109` (página pública, sem login) e `RastreamentoMapa.jsx:36` | IP de quem visualiza + área aproximada da entrega (via tiles do mapa) | ✅ citado na seção 10 desde 21/09/2026 |
| Google Maps JS API (browser) | `frontend/src/utils/googleMaps.js`, usado só por `frontend/src/components/GoogleMapsTest.jsx` | Nenhum hoje — componente de teste não roteado (código morto) | Informativo — risco latente, sem ação na política enquanto não for usado |

## App mobile (`app-mobile/`)

| Ponto de coleta | Onde no código | Dado coletado | Status na política |
|---|---|---|---|
| Localização — seleção de loja | `app-mobile/src/screens/SelecionarLojaScreen.tsx:144-170` | Pede permissão de localização em primeiro plano, lê a posição atual e faz geocodificação reversa para sugerir a loja mais próxima | ✅ bullet próprio adicionado na seção 4 desde 21/09/2026 |
| Localização — captura pontual do entregador | `app-mobile/src/screens/entregador/detalhe/DetalheEntregaUtils.ts:237-244` (`obterLocalizacaoOpcional`), usada em `DetalheEntregaScreen.tsx:208` (marcar entregue) e `:296` (iniciar rota) | Posição pontual do dispositivo, capturada ao confirmar início de rota e ao marcar cada parada como entregue — distinta do fluxo contínuo (`deliveryLocationTracking.ts`) | ✅ bullet próprio adicionado na seção 4 desde 21/09/2026 |
| Localização — rota ativa do entregador | `app-mobile/src/services/deliveryLocationTracking.ts` | Localização precisa, contínua, durante rota ativa | ✅ já descrito na seção 4/8/12 da política |
| Atualização do aplicativo (OTA) | `app-mobile/src/hooks/useAppUpdates.ts` (EAS Update) | Identificador do dispositivo e versão instalada, para os servidores da Expo | ✅ citado na seção 10 desde 21/09/2026 |

## Resumo por severidade

**Atualização 21/09/2026:** a Política de Privacidade (`LegalPage.jsx`, versão 21/09/2026) passou a nomear Groq, Gemini, OpenAI Vision, Mercado Pago/endereço, Google Analytics, Google Fonts, ViaCEP, BrasilAPI, OpenStreetMap, localização na seleção de loja, captura pontual de localização do entregador (início de rota e confirmação de entrega) e EAS Update. **Toda a tabela acima está ✅** — nenhum ponto de contato levantado nesta auditoria ficou sem menção na política. Restam dois tipos de pendência, nenhuma delas é "falta de texto":

1. **Decisão de negócio pendente** — manter Groq e Gemini como fallback de IA (agora documentados, mas ainda recebendo CPF/CNPJ e dado de saúde do pet) ou removê-los. Prioridade Alta.
2. **Pendência técnica, não de texto** — Google Analytics 4 já está nomeado na política, mas: (a) continua carregando sem consentimento prévio (sem banner de cookies); (b) `frontend/.env.production` com o ID real continua versionado no git (o `.gitignore` foi adicionado depois do arquivo já estar rastreado, sem efeito). Prioridade Alta.
3. Informativo, sem ação — `GoogleMapsTest.jsx` (Google Maps JS no browser) é código morto, não roteado.

## Relação com outros documentos

- [[Integracoes]] / [[OpenAI-IA]] — catálogo técnico de cada integração (este documento resolve o ❓ de `OpenAI-IA.md` sobre Groq/Google AI estarem realmente implementados: estão, confirmado em `cliente_info_pdv_chat.py` e `veterinario_ia.py`).
- [[Vulnerabilidades]] — 2 achados novos adicionados a partir desta auditoria (Groq/Gemini sem disclosure; GA4 sem consentimento + `.env.production` versionado).
- [[EmpresaGrupo]] — Grupo Comercial: novo destinatário interno de dados (não é terceiro) coberto pela mesma atualização de política.
- Política aplicada: `frontend/src/pages/LegalPage.jsx`, seção 10.

## Metodologia

Auditoria realizada em 2026-09-21 por 3 agentes de exploração (backend, frontend, mobile) rodando em paralelo, leitura de código apenas, sem execução ofensiva. Complementa a auditoria de segurança geral de 2026-09-12 (ver [[Vulnerabilidades]]), que já havia sinalizado a dúvida sobre Groq/Google AI sem confirmar o uso real.

## Não identificado

- Auditoria de bibliotecas de terceiros nativas do app mobile (crash reporting, analytics nativo) não foi feita nesta rodada — só os pontos de coleta de localização e o fluxo de atualização OTA foram confirmados.
- Não foi verificado se o Google Analytics também está ativo em algum fluxo do app mobile (fora de escopo desta rodada, focada no frontend web).
