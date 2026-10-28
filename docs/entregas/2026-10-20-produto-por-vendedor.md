# Vendas de um produto por vendedor

## Identificação

| Campo | Valor |
|---|---|
| Data | 2026-10-20 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| PR | #1535 |
| Prioridade | P2 |
| Risco | Baixo: consulta e exportação, sem gravação de vendas |
| Domínios | Vendas e financeiro |

## 1. Necessidade e requisitos

Consultar quanto cada vendedor vendeu de um produto em um período. A aba
**Financeiro → Vendas → Por vendedor** já existia, mas somava a venda inteira
e não tinha filtro por produto.

O seletor de produto agora permite busca por nome ou ID entre os itens vendidos
no período. Mostra resumo por vendedor, quantidade, valor bruto e vendas
detalhadas, com exportação do mesmo recorte para Excel. Os componentes de
formulário são V2. Sem produto selecionado, mantém a consulta anterior.

Aceite: uma venda contendo ração e areia só soma a ração quando ela é escolhida;
duas linhas da mesma ração contam como uma venda e somam suas quantidades.
A central geral de relatórios fica fora desta entrega.

## 2. Regras de negócio e dados

- Vendedor é o funcionário indicado na venda, independente de operador/comissão.
- Produtos e vendedores são agrupados por ID, inclusive quando têm nomes iguais.
- Ausência de vendedor aparece como **Sem vendedor**.
- Valor do produto é **bruto**, antes de descontos e taxas, sem abater devoluções.
  A regra aparece na tela e nos títulos dos valores exportados.
- Vendas canceladas são excluídas pela lista existente. Todos os canais são considerados.
- Quantidades preservam três casas na resposta do relatório usando o item original.
  Snapshots financeiros armazenados e valores monetários não são alterados.
- Não há migration, importação ou nova gravação de dados.

## 3. Arquitetura e integrações

Reutiliza `GET /relatorios/vendas/relatorio` e a aba existente. Filtro, resumo
e Excel usam os mesmos grupos de itens, evitando somar produtos alheios ao filtro.
O enriquecimento do backend associa o snapshot pelo ID do item; mantém fallback
por produto/posição para snapshots antigos sem ID.
Não há integração externa nova. Falhas de exportação usam o aviso existente.

## 4. Segurança e privacidade

Mantém autenticação, permissão `relatorios.financeiro`/admin e isolamento do
endpoint existente. A consulta inclui nomes dos clientes já autorizados no
relatório. Não adiciona segredo, configuração, log de dados pessoais ou retenção.

## 5. Desenvolvimento e qualidade

- 8 testes de agrupamento/Excel: venda mista, linhas repetidas, ID string,
  homônimos, quantidade fracionada, valor zero, dados imutáveis e formato anterior.
- 16 testes backend: precisão da quantidade, associação dos itens, contratos
  das rotas e snapshots financeiros.
- 2 testes Playwright com Chrome local e API sintética: resumo, filtros,
  canceladas, vendedor ausente, restauração dos totais e download do Excel.
- Build de produção frontend, ESLint e verificação de formato dos arquivos alterados.
- Banco e permissões não foram alterados; não se aplica teste integrado de gravação.

## 6. Ambientes e homologação

Validação local em `http://127.0.0.1:5173`, com todas as chamadas API do navegador
interceptadas. Massa inteiramente fictícia; nenhum dado real foi usado no E2E.
Registro separado de homologação dispensado: evidência local registrada nesta ficha,
sem publicação ou aceite em produção.

Limitação existente: empresas no modo comercial **recebimento** continuam vendo
a tela de recebimentos no lugar das abas de consulta por venda. Este trabalho
não muda a preferência da empresa nem a navegação desse modo.

## 7. Publicação e rollback

Entrega backend/frontend compatível, sem migration. Requer revisão do PR e
autorização explícita antes do deploy pelo fluxo oficial. Smoke após publicação:
abrir Por vendedor, selecionar período/produto e conferir Excel.
Reverter o commit desta entrega se os totais do produto divergirem dos itens;
não há alteração de dados para desfazer.

## 8. Observabilidade e sustentação

Indicador de sucesso: quantidade e bruto do resumo/Excel coincidem com os itens
do produto nas vendas exibidas. Se houver diferença, conferir período, ID do
produto, vendedor indicado e a regra de bruto/devoluções. Sem alertas ou logs novos.

## 9. Mudança, comunicação e treinamento

Orientar Lucas a selecionar período em **Financeiro → Vendas → Por vendedor**,
escolher produto e usar **Exportar Excel**. A futura central de relatórios pode
reaproveitar esta consulta; nenhum novo menu geral foi criado nesta entrega.

## 10. Fechamento

Aceite técnico local atendido, com testes e limitações registrados. Publicação
depende da autorização específica de Lucas. Conferência do produto/período real
fica para o aceite de negócio após disponibilização no ambiente autorizado.

## Atualização em 2026-10-21: exportação PDF

A aba **Por vendedor** também oferece **Exportar PDF**, ao lado do Excel.
Ambos recebem os mesmos grupos filtrados por período, produto e vendedor.
O PDF contém filtros, totais, resumo por vendedor e detalhes das vendas;
com produto selecionado, informa quantidade e valor bruto somente desse produto.
Sem produto selecionado, mantém os totais originais das vendas.

Geração local no navegador com a dependência jsPDF já existente, sem novo
endpoint, dependência, configuração ou alteração de banco. Layout A4 paisagem,
nomes com quebra de linha, cabeçalhos repetidos e páginas numeradas. Uma venda
com muitos itens pode continuar nas páginas seguintes sem perder produtos.
Quantidades não recebem unidade fixa, pois o payload não informa UN/KG.

Validação adicional: 12 testes unitários de dados/relatório, 4 testes Playwright
com API sintética (incluindo PDF filtrado e geral), build frontend, ESLint,
Prettier e contrato de texto. Três amostras fictícias foram geradas e renderizadas
com Poppler para conferência visual; a amostra extensa preservou 60 itens em
seis páginas, além de quantidades fracionadas e valores no formato brasileiro.
Os arquivos de amostra são temporários e não entram no Git.

Entrega somente frontend. O rollback é reverter o commit desta atualização;
nenhum dado precisa ser restaurado. A publicação continua dependendo de revisão
do PR e autorização explícita de Lucas para produção.
