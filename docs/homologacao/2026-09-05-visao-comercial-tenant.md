# Registro de homologação — visão comercial por tenant

## Identificação

| Campo | Valor |
|---|---|
| Entrega | [Visão comercial por empresa](../entregas/2026-09-05-visao-comercial-tenant.md) |
| PR | PR que contém esta entrega |
| Versão testada | Alterações desta entrega sobre `23eadc2b5`, com build local atualizado |
| Data | 2026-09-05 |
| Ambiente | HOMOLOG local, `http://127.0.0.1:18080` |
| Responsável técnico | Codex |
| Aceite de negócio | Lucas — pendente |
| Massa de teste | Empresa fictícia Demo Visão Comercial 2026 |

## Pré-condições

Ambiente oficial de `scripts/homologacao_local.ps1 -Acao subir`, com PostgreSQL
isolado de produção e backend/frontend saudáveis. Migration aplicada pelo
serviço oficial. Nenhum dado real copiado. Cadastro, produto, estoque, caixa,
vendas, baixas e devolução criados pelas APIs normais autenticadas, somente no
tenant fictício. Para simular agosto, apenas a data de duas vendas recém-criadas
foi retrocedida no PostgreSQL local, com filtros de tenant, ID e observação exata.
Não se usou esse procedimento em produção.

O volume local preexistente tinha uma senha diferente da configuração de
homologação. A credencial foi sincronizada somente nesse PostgreSQL, preservando
seus dados, e o fluxo oficial foi repetido com sucesso. Segredos não registrados.

## Cenários de aceite

| ID | Cenário | Esperado e obtido | Evidência | Status |
|---|---|---|---|---|
| H01 | Venda atual a prazo, R$ 1.000 | Zero nos recebimentos; conta em aberto | API local, teste unitário | Aprovado |
| H02 | Venda de agosto, R$ 1.000, recebida em setembro | Setembro recebe R$ 1.000; agosto zero | API, datas distintas na tabela e PDF | Aprovado |
| H03 | Outra venda de agosto, baixa parcial R$ 300 | Setembro recebe R$ 300; saldo R$ 700 | API e tela da venda aberta pelo relatório | Aprovado |
| H04 | Pix atual R$ 200 | Entrada única de R$ 200 | API e tabela | Aprovado |
| H05 | Comparação inicial, antes da devolução | Vendas atuais R$ 1.200; recebimentos R$ 1.500 | Resumo do dashboard, relatório e gráfico | Aprovado |
| H06 | Devolução em dinheiro da venda Pix | R$ 1.500 recebidos − R$ 200 devolvidos = R$ 1.300 | API oficial de devolução, quatro movimentos, dashboard | Aprovado |
| H07 | Escolher visão na configuração e salvar | Preferência persiste e relatório segue a empresa | Chrome autenticado na homologação e HTTP unitário | Aprovado |
| H08 | Parcelas recebidas em meses diferentes | Cada valor no respectivo mês, sem duplicar total da conta | `test_recebimentos_vendas.py` | Aprovado |
| H09 | Antecipação e conta espelhada | Conciliação confirmada contada uma única vez | `test_recebimentos_vendas.py` | Aprovado |
| H10 | Tenant diferente e vínculo inconsistente | Valores de outra empresa não aparecem | `test_recebimentos_vendas.py` | Aprovado |
| H11 | Sem permissão ou valor inválido na preferência | Alteração negada; leitura permitida ao usuário autenticado | HTTP: 403/422; preferência padrão e reversão | Aprovado |
| H12 | Exportar pelos botões da tela | XLSX e PDF com três movimentos, datas e R$ 1.500 antes da devolução | Arquivos baixados pelo Chrome e conferidos por openpyxl/pypdf; PDF renderizado | Aprovado |
| H13 | Atalhos de mês e link do dashboard | Agosto zero, setembro R$ 1.500 antes da devolução; link preserva período | Chrome | Aprovado |
| H14 | Tema claro/escuro | Texto e indicador legíveis | Capturas inspecionadas no Chrome | Aprovado |
| H15 | Migration e compatibilidade | Padrão venda, sem recalcular histórico | Smoke oficial: clean/history/production_uuid | Aprovado |
| H16 | Relatório/PDF sem permissão financeira | HTTP 403 em ambos; tela mantém o acesso restrito existente | `test_recebimentos_vendas.py`; conferência da proteção na tela | Aprovado |

## Inconsistências e limites

Os atalhos de mês usavam inicialmente data de apresentação no campo ISO, e o
gráfico existente convertia a data civil para o dia anterior no fuso de Brasília.
Ambos corrigidos e conferidos novamente. O contraste do total no tema escuro
também foi corrigido e verificado. Nenhuma inconsistência bloqueante conhecida
nos cenários acima. Responsividade em dispositivo móvel não foi exercitada.

Contas antigas sem data comprovada de recebimento não recebem data presumida.
O cancelamento legado que invalida/apaga baixas mantém seu comportamento;
esta entrega não reconstrói eventos removidos. A devolução normal em dinheiro
foi verificada no fluxo real local. Não houve alteração de regime fiscal.

## Evidências de execução

- Backend: `python -m pytest tests/unit/test_recebimentos_vendas.py tests/unit/test_empresa_config_routes.py tests/unit/test_dashboard_resumo_numeric_types.py tests/unit/test_dashboard_periodo_bounds_contract.py tests/unit/test_relatorio_vendas_routes_refactor_contract.py -q` → **31 passaram**.
- Frontend: testes `test-dashboard-executive-layout`, `test-dashboard-overview`,
  `test-dashboard-contextual-filters` e `recebimentosVendasUtils.test.mjs` → passaram.
- Ruff nos Python alterados, ESLint nos componentes/hooks, Prettier → passaram.
- Contrato de tamanho dos componentes preservado com a seleção de visão em componente próprio e reutilização dos auxiliares existentes.
- `npm run build` → concluído. Log local ignorado: `runtime/visao-comercial-frontend-build.log`.
- `scripts/ci_migration_smoke.py` em PostgreSQL DEV local → três cenários aprovados.
  Log local ignorado: `runtime/visao-comercial-migration-smoke.log`.
- `scripts/homologacao_local.ps1 -Acao subir` → frontend/backend saudáveis.
  Log local ignorado: `runtime/visao-comercial-homolog-final-build.log`.
- Navegador: mesma sessão Chrome disponibilizada pelo Lucas, em nova aba local.
  Produção foi apenas identificada; nenhuma mutação realizada nela.

Impacto: código e massa fictícia de homologação local; nenhum deploy em produção.
Hash final e resultados do CI ficam no PR que contém este registro. Arquivos
temporários, credenciais e massa de testes não foram versionados.

## Decisão

Homologação técnica local aprovada nos cenários listados. Aceite de negócio
pendente com Lucas. Próxima ação: revisar o PR e obter autorização explícita
para publicar pelo fluxo oficial e testar na conta demo de produção.
