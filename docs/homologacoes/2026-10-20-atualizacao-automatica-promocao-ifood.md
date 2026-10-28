# Homologação — atualização automática da promoção iFood

| Campo | Valor |
|---|---|
| Data / responsável técnico | 2026-10-20 / Codex |
| Branch / PR | `codex/ifood-calculadora-central` / #1533 |
| Ambiente | DEV isolado `corepet-ifood-dev`, porta 18081 |
| Responsável de negócio | Lucas, revisão em DEV |
| Massa | CorePet Homologacao Local; produto fictício `DEV-IFOOD-3KG`, ID 2 |

## Pré-condições

Backend/frontend reconstruídos a partir do worktree. Backend saudável,
`SYSTEM_VERSION=ifood-promocao-auto-dev-20261020`. Flags de escrita, operação e
polling iFood continuam falsas. Sem dados de produção e sem chamadas externas.

Produto com ERP 100, custo 60, específico iFood 150, estoque 4, foto principal,
sem pausa. Promoção iFood 120 salva para 20/10/2026, 16:10–16:12 Brasília. Depois
do salvamento, abriu-se o cadastro, alterou-se o nome para conter “rascunho não
salvo”, sem gravar; na central, busca por SKU e calculadora com preço 160 não
aplicado e cenário Entrega iFood. Nenhuma recarga após essa preparação.

O reparo de convergência do histórico DEV preservou o produto e sua imagem,
com [pré/pós-condições e comandos registrados](2026-10-20-ifood-convergencia-migrations-dev.md).

## Cenários de aceite

| ID | Cenário | Esperado | Obtido / evidência | Status |
|---|---|---|---|---|
| H01 | Antes do início | Cadastro/oferta salva 150; simulação 160; sem aviso de margem | Cadastro 46,50/31%; calculadora 53,80/33,63%; nome e preço digitados preservados | Aprovado |
| H02 | Virada real do início, sem recarga | Cadastro e oferta 120; simulação 120 apesar de input 160; margem 24,60/20,50% e aviso de meta | Às 16:10, sem nenhuma ação de recarga/edição, as três leituras mudaram para 120; nome não salvo, busca por SKU e input 160 intactos. Capturas `ifood-auto-promocao-ativa-dev-2026-10-20.png` e `ifood-auto-cadastro-rascunho-ativo-dev-2026-10-20.png` | Aprovado |
| H03 | Virada real do fim, sem recarga | Cadastro/oferta 150; simulação 160; aviso removido, rascunhos intactos | Às 16:12, apenas observando, cadastro/oferta voltaram a 150 (46,50/31%), simulação a 160 (53,80/33,63%), sem aviso; nome não salvo, busca e input 160 intactos. Capturas `ifood-auto-fim-rascunhos-preservados-dev-2026-10-20.png` e `ifood-auto-cadastro-rascunho-final-dev-2026-10-20.png` | Aprovado |
| H04 | Datas, fuso, fim inclusivo, filtro/página, tenant e sem persistência | Metadados corretos e nenhum acesso cruzado | 47 testes backend aprovados | Aprovado |
| H05 | Suspensão, StrictMode, timers atrasados, retries e cancelamento | Recuperar consulta sem loops nem polling contínuo | 18 testes do agendador aprovados | Aprovado |
| H06 | Regressão do cadastro e datas | Salvar/clonar/campos/datas preservados | 28 testes frontend aprovados | Aprovado |
| H07 | Retornar de segundo plano após início | Relê preço 120, contribuição 24,60/20,50% e aviso; mantém nome e input 160 | Confirmado hidden nas duas abas antes/depois da virada. Ao retornar após 16:22, cadastro, lista e calculadora recuperaram 120 e aviso, sem recarga; nome não salvo, busca e input 160 intactos. Captura `ifood-segundo-plano-retorno-inicio-dev-2026-10-20.png` | Aprovado |
| H08 | Retornar de segundo plano após fim | Oferta volta a 150, simulação a 160, aviso removido e rascunhos intactos | Confirmado hidden nas duas abas antes/depois da virada. Ao retornar após 16:24, cadastro e lista recuperaram 150 (46,50/31%); calculadora manteve input 160 e voltou a simular 160 (53,80/33,63%), sem pendências. Nome não salvo e busca intactos. Captura `ifood-segundo-plano-retorno-fim-dev-2026-10-20.png` | Aprovado |

## Evidências técnicas

- Backend: `python -m pytest tests/unit/test_ifood_management.py tests/unit/test_ifood_catalog_contract.py tests/unit/test_ifood_routes_contract.py tests/unit/test_ifood_orders_contract.py tests/unit/test_ifood_client_contract.py -q`: 47 aprovados; Ruff aprovado.
- Frontend: `node --test src/utils/ifoodPromotionRefresh.test.mjs src/components/produto/ifoodProdutoDates.test.mjs`: 21 aprovados. Mais 25 testes de produto/margem/recorrência aprovados.
- `npm run test:app-routes-refactor`: aprovado.
- ESLint dos arquivos alterados e Prettier: aprovados.
- `npm run build`: aprovado; aviso já existente de chunk PDV maior que 500 KB.
- Rebuild Compose somente no projeto 18081; frontend/backend atualizados. Nenhum volume removido ou alteração no ambiente 18080.
- Migração aplicada até `zzzzm20261020a1`: quatro colunas fiscais e seis campos iFood presentes, produto preservado. Teste AST detecta revisões duplicadas.
- Leitura independente do banco às 16:11:24 e 16:12:36 Brasília: nome original, ERP 100/custo 60, iFood salvo 150 (não 160), promoção 120 e datas 16:10–16:12 preservados; estoque 4, foto, seleção ativa e pausa falsa. Flags externas falsas. Nenhuma escrita automática ocorreu.
- Leitura independente em transação somente leitura às 16:24:23 Brasília: nome original, ERP 100/custo 60, iFood salvo 150 (não 160), promoção 120 e nova janela 16:22–16:24 preservados; estoque 4, foto, seleção ativa e pausa falsa. As três flags externas iFood permaneceram falsas; todas as assertions passaram.
- As leituras de visibilidade, preço, contribuição, pendências e rascunhos do teste em segundo plano estão no artefato local `ifood-segundo-plano-evidencias-2026-10-20.json`.
- `scripts/fluxo_unico.ps1 -Acao check`: aprovado, uma head e nenhum artefato proibido. Main atualizada no início e conferida antes de fechar a branch.
- Capturas são artefatos locais deste chat, sem dados reais, e não são versionadas como arquivos da aplicação.

## Procedimento do teste em segundo plano

Nova janela de 20/10/2026, 16:22–16:24 Brasília, salva em uma aba de preparação
separada para não gravar o nome em edição. O rascunho do cadastro recebeu as
mesmas datas, sem salvar; nome e preço simulado anteriores foram preservados.

O controlador mantém foco emulado nas abas por padrão. Para este teste, a
emulação foi desligada temporariamente pelo comando oficial CDP
`Emulation.setFocusEmulationEnabled(false)`. A leitura real do documento confirmou
`document.hidden=true` e `visibilityState='hidden'` nas duas abas. Nenhum evento
JavaScript sintético foi disparado, nenhum documento foi recarregado/descartado
e o relógio não foi alterado. A retomada ativa a aba e restaura o foco emulado,
confirmando estado visível e reconsulta. Isso testa segundo plano; não constitui
teste de descarte da aba, encerramento do navegador ou suspensão do Windows.

As duas retomadas foram aprovadas. Ao encerrar, a configuração anterior de foco
foi restaurada e a aba separada de preparação foi fechada. Cadastro e central
continuaram abertos com os respectivos rascunhos, sem salvar/aplicar.

## Inconsistências e limites

Sem bloqueador identificado na revisão independente. Se o navegador suspender a
aba, a consulta é recuperada quando voltar. Em indisponibilidade de rede, os
últimos dados têm aviso e tentativas limitadas; não há confirmação fictícia de
preço atualizado. O relógio de referência é o servidor, não o computador.

## Decisão

Validação técnica integrada e retornos de segundo plano no início e no fim da
janela 16:22–16:24 aprovados. As abas ficaram abertas para revisão do
Lucas, com nome em edição e simulação 160 sem aplicar. A promoção de teste ficou
armazenada e encerrada; seu preço vigente já voltou a 150. Nenhuma recarga ou
edição foi feita entre a preparação e as duas viradas. Nenhum envio ao iFood,
merge ou deploy de produção executado. Próximo passo: aceite de negócio em DEV.
