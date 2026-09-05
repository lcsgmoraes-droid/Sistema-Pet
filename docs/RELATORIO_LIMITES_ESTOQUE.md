# Estoque mínimo e máximo

Acesso: **Produtos / Estoque → Estoque mínimo e máximo**.

O relatório compara o saldo atual com os limites cadastrados em cada produto.
Mostra código, categoria, marca, fornecedor principal, unidade, saldo, mínimo,
máximo, situação, falta até o mínimo e excesso sobre o máximo.

## Regras

- **Abaixo do mínimo:** saldo menor que o mínimo positivo cadastrado.
- **No mínimo:** saldo igual ao mínimo positivo cadastrado.
- **Acima do máximo:** saldo maior que o máximo positivo cadastrado.
- **Dentro dos limites:** respeita os limites definidos; inclui saldo igual ao máximo.
- **Sem limites:** mínimo e máximo vazios ou zero. Um limite isolado é suficiente
  para comparar o estoque; o limite ausente não gera falta ou excesso.
- **Revisar limites:** algum limite é negativo ou o máximo positivo é menor que
  o mínimo. As quantidades de falta e excesso ficam em branco até corrigir o cadastro.

A falta é a quantidade necessária para atingir o mínimo, não uma sugestão para
comprar até o máximo. Um saldo negativo aumenta essa falta. Não se somam unidades
de produtos diferentes no resumo (por exemplo, quilos e unidades).

O saldo usado é o atual, antes de descontar reservas. Variações e kits físicos
entram individualmente; serviços, produtos pai e kits virtuais ficam de fora.
O relatório exige a permissão `produtos.visualizar` e respeita o escopo de empresa.

## Consulta e exportação

Há filtros por nome/código/EAN, categoria, marca, fornecedor principal ou alternativo,
situação, cadastro ativo/inativo e saldo zerado/negativo. Clicar nos indicadores
seleciona uma situação. O resumo considera os demais filtros antes da paginação.

**Exportar Excel** gera um `.xlsx` com todos os resultados do filtro atual, em todas
as páginas. Quantidades continuam numéricas e códigos preservam zeros à esquerda.
O nome do produto abre suas movimentações para conferência.

## Validação

- Backend: `python -m pytest tests/unit/test_relatorio_limites_estoque.py tests/unit/test_produtos_relatorios_routes_contract.py -q`.
- Frontend: `node --test src/pages/estoque-limites/estoqueLimitesUtils.test.mjs`.
- Compilação: `npm run build` na pasta `frontend`.
- Conferência visual e exportação em navegador com dados fictícios.

Endpoint: `GET /produtos/relatorio/limites-estoque`. A implementação não requer
migração nem alteração nos aplicativos mobile.

## Ficha de entrega

- Identificação: relatório de limites de estoque; 05/09/2026; responsável de negócio
  Lucas; execução Codex; prioridade P2; risco baixo, por ser consulta sem gravação.
- Necessidade e aceite: listar as situações documentadas acima, calcular falta e
  excesso, aplicar filtros e exportar todas as páginas. Manter o cadastro e a
  movimentação existentes. Não inclui sugestão automática de pedido de compra.
- Dados: limites e saldo pertencem ao produto. Não há migração, importação ou
  alteração de registros. Os dados comerciais seguem o acesso da empresa.
- Arquitetura: endpoint de relatório paginado com totais calculados no banco,
  página React e exportação Excel. Sem nova integração externa. Requisições antigas
  são canceladas na troca de filtro; falhas mostram erro e permitem atualizar.
- Segurança: autenticação existente e `produtos.visualizar`; sem novos segredos.
  Não registrar tokens nem exportações em logs. A finalidade continua sendo a
  gestão do estoque, sem nova coleta ou retenção de dados pessoais.
- Qualidade: 20 testes backend e 3 testes frontend, contratos de navegação,
  lint e compilação. Cenários incluem isolamento, permissão negada, limites
  ausentes/invertidos, frações, saldo negativo e exportação sem corte por página.
- Homologação: banco SQLite isolado e Chrome com massa fictícia. Filtro, vazio,
  falha de consulta e arquivo Excel foram conferidos. Este manual registra essa
  homologação; a conferência operacional pós-publicação ocorre no sistema real.
- Publicação: backend e frontend pelo script oficial após release-check e checks
  do GitHub. Sem mudança mobile. Validar health, watchdog, versão publicada e
  abertura do relatório. Autorização de Lucas registrada na conversa de publicação.
- Rollback: reverter o commit do relatório por PR e repetir o deploy oficial;
  não há downgrade de banco. Abortá-lo em falha persistente de health ou erro no
  relatório. Usar logs de requisição para diagnóstico, sem dados exportados.
- Sustentação: sucesso comprovado pela consulta e filtros sem erro, com totais
  coerentes. Em indisponibilidade, usar a listagem de produtos existente. Lentidão
  recorrente exige medição da consulta antes de alterar a implementação.
- Comunicação: orientar usuários em Produtos / Estoque → Estoque mínimo e máximo
  e no botão Exportar Excel; regras e limites estão neste manual e na própria tela.
- Fechamento: critérios de aceite, testes, isolamento, documentação, homologação,
  publicação, rollback e comunicação revisados; PR sem artefatos ou segredos.
  Decisão técnica: aprovado para publicação após os gates obrigatórios.
