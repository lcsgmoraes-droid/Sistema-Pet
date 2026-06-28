# Design - Onboarding inicial, guia de implantacao e criativos

Data: 2026-06-28

## Objetivo

Revisar a experiencia de entrada do Sistema Pet para que novos usuarios saibam
configurar o sistema na ordem certa, sem depender de tentativa e erro. O trabalho
tambem cria uma base organizada para videos demonstrativos e criativos de venda.

O foco inicial e o guia de configuracao. Os criativos e videos usam esse guia
como roteiro de produto, mas ficam como etapa seguinte.

## Problema atual

A tela `IntroducaoGuiada` existe e cobre uma parte importante do fluxo, mas ficou
defasada em relacao ao sistema atual. Desde que ela foi criada, cresceram modulos
como compras, entrada XML, Bling, ecommerce, campanhas, app mobile, veterinario,
banho e tosa, fiscal, IA e WhatsApp.

A Central de Ajuda tambem tem conteudo util, mas mistura instrucoes antigas,
nomes genericos e caminhos que precisam ser conferidos contra as rotas reais.
Os tours guiados existem para poucas telas principais: Dashboard, Pessoas,
Produtos, PDV, Lembretes e Caixas.

## Principio de desenho

O onboarding deve existir em dois niveis:

1. Guia do cliente: simples, visual, dentro do sistema, com passos claros e links
   diretos para cada tela.
2. Checklist interno de implantacao: mais completo, para Lucas/suporte validar
   dependencias, modulos ativos, dados minimos e funcionamento ponta a ponta.

O guia do cliente nao deve assustar. O checklist interno pode ser mais rigoroso.

## Estrutura proposta do guia do cliente

### 1. Empresa e acesso

Objetivo: deixar a conta identificada e pronta para operar.

Itens:

- Conferir dados da empresa.
- Conferir dados fiscais basicos.
- Revisar usuarios e permissoes.
- Conferir plano e modulos ativos.

Telas relacionadas:

- `/configuracoes`
- `/configuracoes/fiscal`
- `/admin/usuarios`
- `/admin/roles`
- `/meu-plano`

### 2. Financeiro obrigatorio

Objetivo: garantir que venda, recebimento, caixa, DRE e relatorios tenham base.

Itens:

- Conferir bancos, caixas e carteiras.
- Conferir formas de pagamento.
- Cadastrar operadoras de cartao quando houver cartao.
- Revisar categorias financeiras.
- Revisar DRE e tipos de despesa.

Telas relacionadas:

- `/cadastros/financeiro/bancos`
- `/cadastros/financeiro/formas-pagamento`
- `/cadastros/financeiro/operadoras`
- `/cadastros/categorias-financeiras`
- `/cadastros/tipos-despesa`
- `/financeiro/dre`

Dependencias:

- Sem forma de pagamento ativa, o PDV nao deve ser considerado pronto.
- Sem banco/caixa/carteira, recebimentos e conciliacao ficam incompletos.
- Sem categorias financeiras/DRE, relatorios podem existir, mas ficam pouco
  confiaveis.

### 3. Cadastros base

Objetivo: preparar os dados que sustentam venda, estoque, clientes e pets.

Itens:

- Conferir departamentos, categorias e marcas.
- Cadastrar ou importar produtos.
- Conferir estoque minimo e estoque inicial.
- Cadastrar pessoas: clientes, fornecedores, funcionarios, veterinarios e
  entregadores quando aplicavel.
- Cadastrar pets.
- Revisar especies, racas e opcoes de racao.

Telas relacionadas:

- `/cadastros/departamentos`
- `/cadastros/marcas`
- `/cadastros/categorias`
- `/produtos`
- `/clientes`
- `/pets`
- `/cadastros/especies-racas`
- `/cadastros/opcoes-racao`

### 4. Operacao de venda

Objetivo: validar o ciclo minimo do dia a dia.

Itens:

- Abrir caixa.
- Fazer venda teste.
- Usar pagamento em dinheiro/PIX.
- Usar pagamento em cartao quando houver operadora cadastrada.
- Conferir baixa de estoque.
- Conferir conta a receber quando a forma de pagamento gerar recebivel.
- Fechar caixa.

Telas relacionadas:

- `/pdv`
- `/meus-caixas`
- `/financeiro/contas-receber`
- `/financeiro/vendas`
- `/financeiro/fluxo-caixa`

### 5. Compras, estoque e fiscal de entrada

Objetivo: validar reposicao, custo e entrada de mercadorias.

Itens:

- Criar fornecedor.
- Registrar pedido de compra quando o modulo estiver ativo.
- Processar entrada XML quando o modulo estiver ativo.
- Conferir custo, frete, impostos e divergencias.
- Validar se o estoque foi atualizado corretamente.
- Validar integracao Bling quando estiver ativa.

Telas relacionadas:

- `/compras/pedidos`
- `/compras/entrada-xml`
- `/compras/pendencias`
- `/produtos/sinc-bling`
- `/vendas/bling-pedidos`
- `/vendas/bling-monitor`

### 6. Modulos por tipo de operacao

Objetivo: mostrar somente o que faz sentido para o cliente.

Itens condicionais:

- Entregas: configurar taxas, origem, entregadores, rotas e rastreio.
- Comissoes: configurar funcionarios comissionados e regras.
- Banho e Tosa: configurar servicos, parametros, recursos, agenda e fila.
- Veterinario: configurar agenda, catalogos, parceiros, consultorios e fluxos
  clinicos.
- Ecommerce: configurar aparencia, loja, pagamento online, entrega/retirada e
  analytics.
- Campanhas: configurar canais, regras, segmentacao e disparos.
- WhatsApp: configurar bot, atendimento e handoff quando ativo.
- App mobile: configurar loja publica, perfis, push e acesso por tenant.
- IA: configurar chaves/integracoes quando o recurso depender disso.

Telas relacionadas:

- `/configuracoes/entregas`
- `/entregas/abertas`
- `/comissoes`
- `/banho-tosa`
- `/veterinario`
- `/ecommerce/configuracoes`
- `/ecommerce/aparencia`
- `/campanhas`
- `/ia/whatsapp`
- `/configuracoes/integracoes`

### 7. Validacao final

Objetivo: sair da implantacao com o sistema realmente pronto.

Checklist final do cliente:

- Venda teste feita.
- Caixa aberto e fechado.
- Estoque conferido.
- Contas a receber conferidas.
- Fluxo de caixa conferido.
- DRE revisado.
- Relatorios de vendas conferidos.
- Usuario operacional consegue fazer o fluxo sem permissao de admin.

## Checklist interno de implantacao

O checklist interno deve ter os mesmos blocos do guia do cliente, mas com campos
extras para suporte:

- Cliente/tenant.
- Plano e modulos ativos.
- Responsavel pela implantacao.
- Data de inicio.
- Data de validacao final.
- Pendencias bloqueantes.
- Pendencias nao bloqueantes.
- Evidencias: prints, video curto ou anotacao.
- Observacoes comerciais: dores do cliente, modulos com potencial de venda,
  recursos que merecem criativo.

## Checks automaticos recomendados

A `IntroducaoGuiada` ja executa alguns checks automaticos. Eles devem ser
mantidos e ampliados.

Checks atuais a manter:

- empresa fiscal preenchida;
- dados cadastrais preenchidos;
- contas bancarias ativas;
- formas de pagamento ativas;
- operadoras ativas;
- categorias de produto;
- produtos;
- pessoas;
- pets;
- configuracao de entrega;
- entregadores;
- configuracao de comissoes;
- opcoes de racao;
- caixa aberto;
- existencia de vendas.

Novos checks sugeridos:

- usuarios criados alem do admin;
- roles/permissoes revisadas;
- categorias financeiras;
- tipos de despesa;
- DRE com categorias/subcategorias;
- fornecedores;
- marcas;
- estoque minimo em produtos vendaveis;
- pedido de compra existente, se modulo compras ativo;
- entrada XML processada, se modulo compras ativo;
- integracao Bling configurada, se modulo Bling ativo;
- configuracao de ecommerce, se modulo ecommerce ativo;
- campanha criada, se modulo campanhas ativo;
- servico de banho e tosa cadastrado, se modulo banho_tosa ativo;
- configuracao veterinaria minima, se modulo veterinario ativo;
- configuracao WhatsApp, se modulo whatsapp ativo;
- loja/app mobile habilitada, se modulo app_mobile ativo.

## Relacao com videos e criativos

Depois que o guia estiver revisado, ele vira uma matriz de conteudo.

Videos demonstrativos:

- "Primeiros passos no Sistema Pet"
- "Como deixar o financeiro pronto"
- "Como cadastrar produtos e vender no PDV"
- "Como conferir estoque, compras e entrada XML"
- "Como usar entregas"
- "Como usar banho e tosa"
- "Como usar veterinario"
- "Como vender pelo ecommerce/app"

Criativos comerciais:

- dor: "nao sei se estou tendo lucro";
- dor: "estoque some e ninguem percebe";
- dor: "venda no caixa nao conversa com financeiro";
- dor: "cartao, PIX e dinheiro ficam baguncados";
- dor: "banho e tosa sem agenda organizada";
- dor: "clinica veterinaria sem prontuario centralizado";
- dor: "pet shop quer vender tambem pelo app/ecommerce".

## Fora do escopo desta primeira fase

- Criar videos finais.
- Criar artes finais.
- Implementar um painel inteligente completo de onboarding 2.0.
- Automatizar pre-configuracao com um clique.
- Alterar regras de negocio de venda, fiscal, estoque ou financeiro.

## Plano de implementacao posterior

Quando este design for aprovado, a implementacao deve ser planejada em etapas:

1. Revisar e reordenar `IntroducaoGuiada`.
2. Separar passos obrigatorios, opcionais e condicionais por modulo.
3. Ampliar checks automaticos possiveis sem criar endpoints novos.
4. Atualizar Central de Ajuda com caminhos reais.
5. Identificar tours que faltam nas telas mais importantes.
6. Criar documento interno de implantacao.
7. Criar matriz de roteiros para videos e criativos.

## Criterios de aceite

- O cliente novo entende a ordem minima para comecar a usar o sistema.
- Lucas/suporte tem um checklist interno mais completo.
- O guia diferencia obrigatorio, opcional e condicional.
- Os caminhos usados no texto existem no menu ou nas rotas reais.
- Os checks automaticos nao quebram se um modulo estiver desativado.
- O guia nao promete funcionalidades que ainda nao existem.
- O material serve de base para roteiro de video e criativos comerciais.
