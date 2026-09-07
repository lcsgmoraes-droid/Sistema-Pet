# Ficha de entrega — visão comercial por empresa

Data: 2026-09-05. Responsável de negócio: Lucas. Executor: Codex.
Prioridade: P2. Risco: médio (leitura de valores financeiros e isolamento).
Domínios: configuração geral, dashboard e relatório comercial web.
PR: [#1308](https://github.com/lcsgmoraes-droid/Sistema-Pet/pull/1308), publicado em 2026-09-07.

## 1. Necessidade e requisitos

Permitir escolher uma única visão por tenant: data da venda (padrão existente)
ou data do recebimento. A mesma entrada do relatório apresenta a visão escolhida.
O indicador principal do dashboard acompanha a preferência. Quantidade, ticket,
lucro, estoque, fiscal e comissões mantêm suas regras e rótulos de vendas.
Aceite: venda não recebida soma zero em recebimentos; baixa de venda antiga entra
na data da baixa; parcelas são somadas individualmente; outra empresa não muda.

## 2. Regras e dados

EmpresaConfigGeral guarda `visao_comercial`, validada na API e no banco.
Migration aditiva com padrão `venda`, sem reprocessamento de histórico.
Recebimentos vêm das baixas individuais; conciliação validada/amarrada é contada
uma vez, inclusive antecipação de várias parcelas. Contas antigas com data real
e valor recebido podem suprir a ausência de baixas individuais, sem duplicá-las.
Devolução em dinheiro é saída na data registrada. Crédito e cashback não são
entrada nova. Cancelamento que invalida a operação segue o comportamento atual;
não se reconstrói um movimento que o fluxo legado apagou.

## 3. Arquitetura e integrações

Consultas financeiras compartilhadas entre dashboard e relatório de recebimentos.
Entradas e devoluções no resumo e no gráfico do dashboard seguem a mesma fonte.
Relatório por venda permanece disponível internamente com o contrato original.
Sem integração externa, retry ou credenciais novas. Falhas de consulta são
exibidas como erro, sem substituir dados indisponíveis por zero.

## 4. Segurança e privacidade

Tenant vem da autenticação em todos os joins. Alteração exige
`configuracoes.editar`; leitura da preferência usa sessão autenticada. Consulta
e PDF de recebimentos exigem `relatorios.financeiro`, com o mesmo acesso financeiro
da tela existente. Perfis restritos mantêm seu histórico permitido. Mudança de preferência
auditada na mesma transação. Nenhum segredo ou dado real entra nos testes.
Finalidade e retenção dos dados existentes permanecem.

## 5. Desenvolvimento e qualidade

Fatias: preferência/migration; consulta financeira; telas/exportação; testes.
Testar meses distintos, parcial, quitação, conciliação, duplicidade, devolução,
crédito, tenant, permissões, persistência e retorno ao padrão. Executar lint,
build e regressões focadas. Validação final: 31 testes de backend passaram;
testes de exportação e contratos do dashboard passaram; Ruff, ESLint, Prettier
e build de produção do frontend passaram. Migration smoke passou em banco
limpo, histórico e cenário de tenants UUID.

## 6. Ambientes e homologação

Validação inicial em DEV/local com dados fictícios. Lucas autorizou a publicação
em 2026-09-07 com “vamos publicar”, além dos lançamentos na conta demo.
Publicação e testes nessa conta concluídos pelo navegador autenticado em produção.
Homologação local executada pelo fluxo oficial, em `127.0.0.1:18080`, com
quatro vendas fictícias, duas baixas posteriores e uma devolução.
Evidências: [registro de homologação](../homologacao/2026-09-05-visao-comercial-tenant.md).

## 7. Publicação e rollback

Entrega backend/frontend. Aplicar migration antes do backend; publicar pelo
fluxo oficial após PR/checks e autorização explícita. Rollback de código mantém
a coluna aditiva; selecionar `venda` restaura a visão anterior. Abortagem se
totais divergirem, houver duplicidade ou falha de isolamento.

## 8. Observabilidade e sustentação

Auditoria de preferência com autor e tenant; logs normais de erro da API.
Indicador de sucesso: total e detalhes/exportação concordam para o mesmo período.
Histórico sem data/baixa comprovada não recebe data estimada silenciosamente.

## 9. Comunicação e treinamento

A própria configuração explica as duas opções; títulos indicam recebimentos
quando selecionados. Documentar a regra no manual desta entrega. Sem mudança
na rotina de registrar vendas ou receber contas.

Para ativar: **Configurações → Parâmetros Gerais → Visão dos indicadores
comerciais → Pela data do recebimento → Salvar Configurações**. A seleção vale
para os usuários da empresa. O card principal do dashboard abre o relatório
no mesmo período. Nesse relatório, cada baixa mostra sua data e a data original
da venda; Excel e PDF mantêm as mesmas informações. Para voltar, selecione
**Pela data da venda** e salve. A preferência de outras empresas não muda.

Essa preferência é uma visão gerencial comercial. Não seleciona regime fiscal
nem altera DRE, estoque, contas, vendas, comissões ou documentos fiscais.

## 10. Fechamento

Implementação e homologação técnica local concluídas. No exemplo inicial,
vendas de setembro somaram R$ 1.200 e recebimentos R$ 1.500; agosto apresentou
R$ 2.000 em vendas sem recebimentos. Uma devolução posterior de R$ 200 reduziu
o indicador de recebimentos para R$ 1.300. Saldo parcial de R$ 700 confirmado
na própria venda pelo navegador.

Publicado em produção em 2026-09-07 às 15:07 (Brasília), commit
`6bdb6e1e1816131a1996f2d05490a06680dd4507`, após gate completo, oito checks
obrigatórios do commit final e backup. Migration `zzj20260905a1` aplicada;
backend, banco, nginx, workers e verificações públicas de saúde aprovados.

Na demo de produção, uma venda a prazo de R$ 1.000 manteve recebimentos em zero.
A baixa parcial de R$ 300 deixou R$ 700 em aberto. Uma parcela de venda de agosto
recebida hoje acrescentou R$ 47,48; uma venda Pix acrescentou R$ 200.
Antes da devolução, a visão por venda mostrou R$ 1.200 e a de recebimentos
R$ 547,48. A devolução de R$ 200 reduziu recebimentos para R$ 347,48.
Dashboard e relatório concordaram; Excel/PDF gerados. A demo ficou na visão
por recebimento, com os lançamentos identificados como teste.
Evidência operacional e IDs constam no registro de homologação vinculado acima.
