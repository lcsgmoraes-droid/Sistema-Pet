# Tema Escuro do Sistema Pet

## Objetivo

Adicionar uma opcao de tela escura no frontend do Sistema Pet sem prejudicar leitura,
icones, imagens, graficos, tabelas, cabecalhos, formularios ou modais.

## Decisao de Produto

O sistema tera um controle manual de tema no topo da area logada. A primeira visita
seguira a preferencia do sistema operacional quando nao houver escolha salva. Depois
que o usuario escolher claro ou escuro, a preferencia ficara salva no navegador.

## Abordagem Escolhida

Usar a configuracao existente do Tailwind com `darkMode: "class"` e aplicar a classe
`dark` no elemento `html`. O tema sera apoiado por tokens CSS globais para fundos,
superficies, textos, bordas, controles, foco e graficos.

A implementacao priorizara componentes compartilhados e layout:

- `Layout`, `OpsLayout` e topo/sidebar.
- Componentes de UI em `frontend/src/components/ui`.
- Tabelas, filtros, paginacao, cards metricos, estados vazios e formularios.
- Ajustes focados em telas criticas: Dashboard, Dashboard Financeiro, PDV,
  Produtos, Pessoas/Clientes, Configuracoes, Financeiro, Veterinario e Ops.

## Regras Visuais

- Texto principal deve continuar claro e legivel em fundo escuro.
- Texto secundario nao pode ficar apagado demais.
- Bordas e divisorias devem existir sem competir com o conteudo.
- Inputs e selects devem ter fundo, texto, placeholder e foco visiveis.
- Tabelas devem preservar cabecalho, linhas, hover e divisorias.
- Modais e drawers devem ter contraste proprio, sem depender do fundo da pagina.
- Graficos Recharts devem usar grade, eixos, legenda e tooltip adaptados ao tema.
- Logos e imagens nao devem ser invertidos automaticamente.
- Botoes coloridos de acao devem preservar intencao: sucesso, alerta, perigo,
  informacao e acoes primarias.

## Validacao

Antes de finalizar:

- Rodar testes focados de tema/contrato quando adicionados.
- Rodar `npm run build` em `frontend`.
- Abrir o frontend no Chrome e conferir telas representativas em claro e escuro.
- Verificar visualmente cabecalho, sidebar, conteudo, tabelas, graficos, modais,
  botoes, inputs, icones e imagens.
- Nao versionar `frontend/dist`.

