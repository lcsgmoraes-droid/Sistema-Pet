# Ficha de entrega: produtos vendidos por fornecedor em PDF

## Identificação

| Campo | Valor |
|---|---|
| Título | Exportação PDF e filtro de fornecedores na Análise de Produtos |
| Data | 2026-10-26 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| Issue/PR | PR da branch `feat/20261019-1708-cadastro-e-central-ifood`, associado à conversa no Codex |
| Prioridade | P2 |
| Risco | Médio: consulta de vendas e exportação financeira; não grava dados |
| Domínios afetados | Produtos, fornecedores, vendas e relatórios |

## 1. Necessidade e requisitos

- Permitir que a equipe gere o relatório de produtos vendidos por fornecedor
  diretamente em PDF, usando o período e os filtros já aplicados na tela.
- Corrigir o filtro que considerava somente o fornecedor principal e ignorava
  vínculos alternativos ativos do mesmo produto.
- Preservar o CSV, os totais existentes e os critérios de seleção das vendas.
- Critérios de aceite: PDF com empresa, período, filtros, produto, SKU,
  quantidade, faturamento, subtotais, total geral e paginação; nenhum valor
  duplicado quando houver mais de um vínculo; nomes extensos legíveis.
- Fora do escopo: alterar cadastros automaticamente, reconstruir a origem de
  lotes, reprocessar vendas ou publicar em produção.

## 2. Regras de negócio e dados

- Com fornecedor selecionado, a consulta aceita o fornecedor principal ou um
  vínculo alternativo ativo em `ProdutoFornecedor`, sempre na empresa atual.
- Sem fornecedor selecionado, o agrupamento continua pelo fornecedor principal
  atual. Produtos sem fornecedor permanecem identificáveis no resultado geral.
- Produto sem vínculo cadastral com o fornecedor selecionado fica fora do
  filtro, mesmo que tenha sido vendido. A investigação encontrou esse tipo de
  inconsistência cadastral; a revisão dos vínculos permanece pendente.
- O PDF usa os resultados da consulta e os filtros aplicados, sem realizar
  outra busca nem atribuir fornecedor pela marca ou pelo nome do produto.
- Não há migration, importação, mudança de histórico, retenção ou escrita no
  banco. A existência de múltiplos vínculos não multiplica as linhas de venda.

## 3. Arquitetura e integrações

- Backend: `backend/app/produtos/relatorios_analise_routes.py`, na consulta
  `GET /produtos/relatorio/analise-vendas`; existência de vínculo evita somas
  duplicadas de junções com fornecedores alternativos.
- Frontend: página, filtros e controlador de `analise-produtos`; gerador
  `analiseProdutosPdf.js` com a biblioteca jsPDF já instalada.
- A geração ocorre no navegador. Não há novo serviço externo, dependência ou
  contrato de escrita. O PDF não depende de capturar a tela ou abrir impressão.
- Falhas de consulta ou geração produzem aviso na tela; exportações ficam
  indisponíveis durante carregamento e quando não há resultado exportável.
- Timeout, retry, idempotência e reconciliação: não se aplica nova estratégia;
  preserva-se o cliente de consulta existente e não há efeito persistente.

## 4. Segurança e privacidade

- Mantidas autenticação e permissão de visualizar produtos da rota existente.
- Consulta e vínculos de fornecedor respeitam o tenant atual. O PDF recebe
  somente os dados já consultados para essa empresa.
- Testes cobrem vínculo de outra empresa e ausência de permissão.
- Nenhum segredo ou configuração adicional é necessário. Dados de vendas e
  identificação da empresa pertencem ao relatório solicitado; não registrar
  tokens, cadastros, relatórios reais ou dados pessoais em logs e evidências.
- Sem alteração de finalidade ou retenção no servidor. O arquivo baixado fica
  sob controle do usuário; esta entrega não cria compartilhamento externo.

## 5. Desenvolvimento e qualidade

- Fatias: corrigir filtro e contratos; gerar PDF; integrar botão e estados;
  aplicar componentes V2 nos filtros; atualizar a Central de Ajuda.
- Backend: 36 testes focados aprovados, incluindo consulta SQL com SQLite,
  fornecedor principal/alternativo, vínculo inativo, duplicidade, período,
  isolamento e permissão, além de regressões dos relatórios de produtos.
- Frontend: 14 testes focados aprovados, cobrindo dados do PDF, paginação,
  nomes extensos, empresa, filtros aplicados, carregamento e falhas.
- `npm run build`, na pasta `frontend`: aprovado.
- PDF com dados fictícios: seis páginas renderizadas e inspecionadas, sem
  cortes de linhas, cabeçalhos ou totais.
- Evidências executáveis ficam nos testes
  `backend/tests/unit/test_produtos_analise_fornecedor.py`,
  `test_produtos_analise_vendas.py`, `test_produtos_relatorio_quantidade.py`,
  `frontend/src/pages/analise-produtos/analiseProdutosPdf.test.mjs` e
  `useAnaliseProdutos.test.mjs`. Artefatos temporários não são versionados.

## 6. Ambientes e homologação

- Validação local por testes de consulta/contrato, controlador React, build e
  inspeção do PDF fictício. Nenhuma nova variável por ambiente é necessária.
- Teste E2E com a stack integrada pendente: Docker Desktop estava indisponível.
- A consulta ao sistema em uso foi somente de leitura para investigar a
  divergência. Dados identificáveis dessa consulta não fazem parte desta ficha.
- Registro separado de homologação: não se aplica nesta etapa; os cenários e
  limites da validação técnica estão consolidados nesta ficha. O aceite de
  negócio no ambiente integrado continua necessário antes da publicação.
- Pendências: conferir a jornada integrada e revisar os vínculos dos produtos
  sem fornecedor com Lucas, sem atualização cadastral automática.

## 7. Publicação e rollback

- Tipo: backend, frontend e documentação; sem mobile ou migration.
- Versão: commit final da branch e head do PR, a registrar na revisão.
- Publicação ainda não executada. Exige revisão, fluxo de release e autorização
  explícita do Lucas, com rebuild do backend e build do frontend pelo fluxo
  oficial. A ficha e o PR não autorizam deploy.
- Após publicação autorizada: consultar um período conhecido, conferir filtro
  principal/alternativo e resultado sem fornecedor, baixar PDF/CSV e comparar
  quantidades e faturamento com a tela, além dos health checks oficiais.
- Abortar/reverter se houver diferença de totais, vazamento entre empresas ou
  falha de consulta/exportação. Rollback: reverter o commit e repetir o fluxo
  oficial autorizado; não há dado ou schema a desfazer.

## 8. Observabilidade e sustentação

- Preservados tratamento de erro e avisos de carregamento/exportação existentes.
  Sem novo agendamento, alerta ou coleta de dados.
- Sucesso: PDF baixado e totais iguais aos filtros aplicados; vínculo
  alternativo ativo aparece sem duplicação.
- Resultado vazio pode indicar período sem venda ou ausência de vínculo no
  cadastro. Consultar sem fornecedor ajuda a distinguir esses casos; não
  presumir fornecedor por nome de produto.
- Falha de geração admite o CSV como alternativa operacional. Divergência de
  dados exige revisão cadastral; recorrências devem motivar melhoria separada
  de qualidade de cadastro, sem alterar vendas ou vínculos em massa nesta tarefa.

## 9. Mudança, comunicação e treinamento

- Caminho: **Produtos / Estoque → Análise de Produtos**. Selecionar período e
  fornecedor, aplicar filtros e usar **Gerar PDF por fornecedor**.
- Central de Ajuda atualizada no artigo **Como usar o relatório de produtos**,
  incluindo CSV, PDF, vínculos ativos e produtos sem fornecedor cadastrado.
- Público: equipe de gestão, vendas e compras. Orientação curta na liberação
  autorizada; sem treinamento ou mudança de processo financeiro adicional.

## 10. Fechamento

- [x] Critérios técnicos de aceite atendidos nos testes e PDF fictício.
- [x] Testes e limites das evidências registrados.
- [x] Tenant, permissões, dados e histórico preservados.
- [x] Central de Ajuda atualizada.
- [x] Homologação técnica consolidada e pendência integrada justificada.
- [x] Publicação, observabilidade e rollback definidos.
- [x] Comunicação e treinamento avaliados.
- [ ] PR revisável associado e aceite de negócio registrado.

Decisão técnica: aprovado com pendências de homologação integrada e revisão
cadastral. Não representa aprovação de publicação.

Pendências, responsável e prazo: executor técnico valida a jornada integrada
quando o DEV estiver disponível; Lucas revisa os vínculos cadastrais e o aceite
antes de autorizar a publicação. Nenhum dado real foi alterado nesta entrega.
