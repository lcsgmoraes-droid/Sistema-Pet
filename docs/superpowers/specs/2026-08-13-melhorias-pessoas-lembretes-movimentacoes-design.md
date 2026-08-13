# Melhorias Visuais em Pessoas, Lembretes e Movimentacoes

## Objetivo

Melhorar tres pontos de uso diario do CorePet sem alterar regras de negocio: facilitar a copia de dados na lista de Pessoas, modernizar a area de validade em Lembretes e impedir que observacoes longas deformem a tabela de movimentacoes de estoque.

## Direcao visual aprovada

A direcao escolhida foi **Clean operacional (Opcao A)**:

- fundo predominantemente branco e cinza-claro;
- verde-petroleo do CorePet como acao principal;
- cores de alerta usadas de forma suave e sem grandes blocos saturados;
- botoes compactos, arredondados e com texto objetivo;
- densidade suficiente para operacao diaria, sem transformar a pagina em uma grade apertada;
- componentes e icones ja existentes no sistema devem ser reutilizados sempre que possivel.

## 1. Lista de Pessoas

### Comportamento

- Exibir um pequeno icone de copiar ao lado do codigo, nome e celular de cada pessoa.
- Usar exatamente a linguagem visual ja aplicada na lista de Produtos: icone de dois quadrados sobrepostos, sem caixa ou borda permanente.
- O botao deve ter `title` e `aria-label` especificos: `Copiar codigo`, `Copiar nome` e `Copiar celular`.
- O clique no icone nao pode abrir a edicao da pessoa nem acionar a linha da tabela.
- Depois de uma copia bem-sucedida, o icone muda temporariamente para um check verde e volta ao estado normal.
- Valores inexistentes continuam exibindo `-` e nao recebem botao de copia.

### Desktop

Os icones ficam imediatamente depois de cada valor, nas proprias colunas ID, Nome e Celular. A coluna Acoes permanece reservada para WhatsApp, editar e excluir.

### Celular

O cartao responsivo tambem deve permitir copiar codigo, nome e celular. Os alvos de toque devem manter area suficiente para uso com o dedo, mesmo que o desenho do icone continue pequeno.

### Implementacao esperada

Reutilizar `frontend/src/components/ui/CopyableValue.jsx`, que ja oferece o icone Lucide `Copy`, confirmacao com `Check`, acesso ao clipboard e bloqueio de propagacao do clique.

## 2. Lembretes de validade

### Cabecalho e resumo

- Substituir o aspecto roxo e quadrado do botao `Verificar validade agora` por um botao compacto de tom verde-petroleo suave.
- Manter o estado `Verificando...` e o bloqueio contra cliques repetidos durante o processamento.
- Apresentar o total de produtos bloqueados em uma pequena capsula, sem disputar destaque com o titulo.
- Manter o alerta semantico de validade em amarelo/ambar suave.

### Cartoes de produto

Cada pendencia deve aparecer em um cartao branco com borda cinza-clara e hierarquia consistente:

- nome do produto como informacao principal;
- lote e vencimento como informacao secundaria;
- quantidade bloqueada e custo estimado alinhados a direita no desktop;
- no celular, metricas devem quebrar para uma nova linha sem corte;
- espaco vertical menor que o desenho atual, mas sem comprimir o texto.

### Acoes

- `Descartar`: fundo vermelho muito claro, borda e texto vermelhos.
- `Registrar troca`: fundo indigo muito claro, borda e texto indigo.
- `Retornar ao estoque`: acao primaria em verde-petroleo.
- Os rotulos usam verbos claros; `Trocado` passa a ser `Registrar troca` para representar a acao que ainda sera executada.
- Os icones atuais podem permanecer, desde que tenham tamanho uniforme e nao dominem o botao.

### Estados existentes

Os estados de protecao desativada, protecao ativa sem pendencias e lista com pendencias continuam funcionando. A mudanca e visual e de texto; chamadas de API e regras de resolucao nao mudam.

## 3. Historico de movimentacoes do produto

### Problema a resolver

A coluna Observacao atualmente pode ficar estreita demais. Em observacoes longas, o navegador quebra o texto quase letra por letra e aumenta exageradamente a altura da linha.

### Comportamento aprovado

- A tabela recebe largura minima suficiente para manter colunas operacionais legiveis e usa rolagem horizontal quando o espaco nao comportar tudo.
- A coluna Observacao recebe largura minima e largura preferencial maiores que as colunas curtas.
- O texto usa quebra por palavras, nunca quebra agressiva caractere por caractere.
- Por padrao, mostrar no maximo duas linhas da observacao.
- Quando houver conteudo oculto, mostrar `Ver mais`.
- `Ver mais` expande somente a observacao daquela movimentacao dentro da propria linha e muda para `Ver menos`.
- Clicar em `Ver mais` ou `Ver menos` nao pode abrir o modal da movimentacao.
- Badges de status e motivo devem ficar separados do texto, com possibilidade de quebra controlada.
- A observacao completa continua disponivel no modal existente, independentemente da expansao da linha.

### Responsividade

Em telas estreitas, a prioridade e preservar informacao. A tabela pode usar rolagem horizontal; nao deve comprimir a observacao ate ficar ilegivel.

## Acessibilidade

- Todos os novos controles devem ser acessiveis por teclado.
- Icones sem texto visivel precisam de `title` e `aria-label`.
- Estados de foco devem permanecer visiveis.
- Cor nao pode ser a unica forma de comunicar a acao; os botoes mantem rotulos textuais.
- A confirmacao de copia muda o icone e o texto acessivel para `Copiado`.

## Fora do escopo

- Alterar APIs, banco de dados ou regras de negocio.
- Redesenhar toda a pagina de Pessoas, Lembretes ou Movimentacoes.
- Mudar o fluxo de resolucao de validade.
- Adicionar exclusao, edicao ou copia em massa.
- Alterar sidebar, dashboard ou outras tabelas.

## Arquivos previstos

- `frontend/src/components/clientes/ClientesNovoTabelaSection.jsx`
- `frontend/src/pages/lembretes/LembretesValidadeSection.jsx`
- `frontend/src/components/estoque/MovimentacoesLancamentosTable.jsx`
- testes focados novos ou existentes para os comportamentos extraidos como funcoes testaveis;
- componentes auxiliares pequenos apenas se forem necessarios para manter os arquivos acima legiveis.

## Criterios de aceitacao

1. Codigo, nome e celular podem ser copiados diretamente na lista de Pessoas usando o mesmo icone visual da lista de Produtos.
2. Copiar nao abre a pessoa e exibe check verde temporario.
3. A secao de validade segue o visual clean aprovado, sem botao roxo quadrado nem grandes blocos saturados.
4. Todos os fluxos de validade continuam chamando as mesmas acoes do controller.
5. Observacao longa ocupa no maximo duas linhas inicialmente e nao quebra letra por letra.
6. `Ver mais` e `Ver menos` funcionam por linha e nao abrem o modal.
7. As tres areas continuam usaveis no desktop e no celular.
8. Testes focados, lint dos arquivos alterados e build do frontend passam antes do fechamento da tarefa.

## Validacao visual

- Conferir `/clientes` em desktop e largura de celular.
- Conferir `/lembretes` com pendencias de validade e com estado sem pendencias.
- Conferir `/produtos/:id/movimentacoes` com observacao curta, longa, sem observacao e com badges de motivo/status.
- Confirmar ausencia de erros novos no console durante esses fluxos.
