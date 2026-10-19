# Homologação técnica — Cashback e contatos

## Identificação

- Data: 2026-10-19, America/Sao_Paulo.
- Entrega: `docs/entregas/2026-10-19-cashback-crm.md`.
- Código testado: `c80f2a031`, incluindo a instalação local descrita abaixo.
- Responsável técnico: Codex, com revisão independente.
- Aceite de negócio: pendente com Lucas.
- Ambientes: testes SQLite em memória, PostgreSQL 16 descartável local e Chrome
  no perfil CorePet com prévia isolada em `127.0.0.1:5186` e sistema completo
  de homologação em `127.0.0.1:18080`.

## Pré-condições

Nenhum dado de cliente real foi necessário. Testes backend desativaram leitura
de `.env` e usaram configurações fictícias. O smoke oficial usou os bancos
`petshop_cashback_crm_smoke_*`, criados exclusivamente para esta validação,
e removeu esses bancos e a role temporária ao terminar. A prévia visual
renderizou os componentes reais com respostas de API simuladas em memória;
  não acessou a sessão nem os dados da outra homologação local.

Na validação posterior solicitada por Lucas, o sistema completo de homologação
foi atualizado pelo script oficial, preservando seus volumes e registros.
Foram acrescentados somente três clientes fictícios identificados pelos códigos
`CRM-DEMO-001/002/003`, com R$ 45,00, R$ 128,50 e R$ 22,00 de crédito manual
de demonstração. Telefones são fictícios, sem assinante válido; não houve
abertura externa nem envio de mensagem. O seed foi repetido em simulação e
confirmou zero inserções adicionais.

## Cenários de aceite

| Cenário | Resultado | Evidência |
|---|---|---|
| Expiração, saldo utilizado e estorno | Saldo disponível correto; vencidos/zerados ausentes | `backend/tests/unit/test_cashback_crm.py` |
| Lista maior que 500 e filtros | Todos alcançáveis por paginação; resumo geral preservado | Mesmo teste backend |
| Abertura com texto, operador e saldo | Evento persistido sem afirmar envio da mensagem | Mesmo teste backend |
| Repetição e cliques simultâneos | Mesmo pedido não duplica; retry revalida bloqueios | Testes backend e `useCashbackCrm.test.mjs` |
| Status, nota e retorno | Eventos anteriores preservados; agenda validada | Testes backend e frontend |
| Consentimento, telefone, saldo e não contatar | API bloqueia abertura inválida | Testes backend |
| Perfil sem clientes.editar | Consulta permitida; gravação e abertura negadas | Testes API e handlers frontend |
| Outra empresa | Consulta/gravação de cliente alheio negadas | Testes backend e RLS PostgreSQL real |
| Popup bloqueado, API falhando e link inesperado | Não navega; fecha aba em erro; mantém texto e chave de retry | `cashbackCrmUtils.test.mjs` e `useCashbackCrm.test.mjs` |
| StrictMode e resposta antiga de filtro | Loading inicial único; resposta cancelada ignorada | `useCashbackCrm.test.mjs` |
| Interface desktop | Lista, mensagem personalizada e histórico legíveis; status/nota atualizados ao salvar | Chrome, massa fictícia Marina/Rafael/Ana |
| Sistema local completo | Login preservado; lista real com três clientes e total R$ 195,50; histórico/nota/status persistidos pela API PostgreSQL | Chrome, CorePet Homologacao Local, códigos CRM-DEMO |
| Migration PostgreSQL | Clean, histórico e tenant UUID chegam ao head; gate RLS aprovado | `scripts/ci_migration_smoke.py` |
| RLS com role não administrativa | Empresa A só vê A; B só vê B; INSERT/UPDATE cruzado negado; sem tenant não lê | Cinco cenários SQL em banco descartável |

## Comandos e resultados

- `FLUXO_UNICO.bat check` e `FLUXO_UNICO.bat dev-up`: aprovados.
- Pytest: 17 testes em `backend/tests/unit/test_cashback_crm.py` aprovados;
  37 regressões de carteira, vencimento, relatório, lembretes e tenant aprovadas.
- `node --test src/components/campanhas/cashback-crm/*.test.mjs`: 14 aprovados.
- `npm run test:app-routes-refactor`: aprovado.
- Ruff nos arquivos backend alterados; ESLint e Prettier nos arquivos frontend
  alterados; `git diff --check`: aprovados.
- `npm run build`: aprovado. Aviso existente de chunk do PDV acima de 500 kB.
- `scripts/ci_migration_smoke.py`: três caminhos PostgreSQL aprovados, com uma
  única head `zzzzf20261019a1` e gate RLS sem dívida.
- `scripts/homologacao_local.ps1 -Acao subir`: imagens frontend/backend
  reconstruídas; migration `zzzze20261019a1 -> zzzzf20261019a1` aplicada;
  health frontend/backend aprovados.
- Chrome em `http://127.0.0.1:18080/campanhas/cashback-crm`, com a sessão
  existente do Operador Homologacao: listagem e mensagem personalizada
  verificadas; CRM-DEMO-002 alterado de Aguardando retorno para Interessado;
  observação de teste salva, segundo evento consultado no histórico e estado
  atualizado na lista. Nenhum contato externo realizado.

## Inconsistências preexistentes e limites

- O teste legado de enumeração `test_campaigns_routes_preserva_paths_publicos_extraidos`
  não enxerga subrouters no FastAPI instalado. A falha foi reproduzida carregando
  o `routes.py` inalterado do commit base; não é causada pelo CRM.
- O teste antigo de badge de convites em `menuConfig.test.mjs` falha porque a
  base não trata `convitesGruposCount`. A ausência foi confirmada executando o
  `menuConfig.js` inalterado do commit base. Quatro outros testes de menu passaram.
- Revisão visual e acompanhamento foram aprovados também no sistema completo
  local com sessão autenticada, API e PostgreSQL reais. Revisão em viewport mobile
  e aceite de negócio continuam pendentes. WhatsApp externo foi simulado nos
  testes; nenhuma mensagem foi enviada e nenhum recebimento/leitura foi presumido.
- O modelo de mensagem fica na sessão da tela; não é uma configuração compartilhada.

## Decisão

Aprovado tecnicamente para revisão do PR, com limites de homologação registrados.
Lucas permanece responsável pelo aceite de negócio. Antes de produção, executar
o gate oficial de release e obter a autorização específica de publicação.
