/**
 * CentralAjuda.jsx
 * Base de conhecimento completa do Sistema Pet.
 * Pesquisável por palavra-chave, organizada por módulo.
 */
import { useMemo, useState } from "react";
import {
  FiBarChart2,
  FiBookOpen,
  FiCalendar,
  FiChevronDown,
  FiChevronUp,
  FiCpu,
  FiDollarSign,
  FiGlobe,
  FiPackage,
  FiSearch,
  FiSettings,
  FiShoppingCart,
  FiTruck,
  FiUsers,
} from "react-icons/fi";

/* ──────────────────────────────────────────────────────────────
   BASE DE CONHECIMENTO — adicione artigos aqui
────────────────────────────────────────────────────────────── */
const BASE_CONHECIMENTO = [
  // ────────────── DASHBOARD ──────────────
  {
    modulo: "dashboard",
    label: "Dashboard",
    icone: FiBarChart2,
    cor: "indigo",
    artigos: [
      {
        titulo: "Como ler o Dashboard Gerencial",
        tags: ["dashboard", "financeiro", "saldo", "resumo"],
        conteudo: [
          "O Dashboard é a primeira tela que você vê ao entrar no sistema. Ele mostra um resumo financeiro completo do seu negócio.",
          "**Saldo Atual** — mostra o saldo do seu caixa neste momento. Clique no card para ver o fluxo de caixa detalhado.",
          "**A Receber** — total de contas que seus clientes ainda devem pagar. Se aparecer ⚠️, há contas vencidas.",
          "**A Pagar** — suas despesas em aberto com fornecedores. Se aparecer ⚠️, há contas vencidas.",
          "**Lucro / Prejuízo** — resultado do período selecionado (7, 15, 30, 60 ou 90 dias). Clique para ver o DRE completo.",
          "**Vendas por Canal** — mostra quanto foi vendido em cada canal (Loja Física, Mercado Livre, Shopee, Amazon).",
          "**Ações Rápidas** — botões para as tarefas mais comuns: Nova Venda, Nova Conta a Receber, etc.",
        ],
      },
      {
        titulo: "Como mudar o período do Dashboard",
        tags: ["dashboard", "período", "dias", "filtro"],
        conteudo: [
          "No canto superior direito do Dashboard, você vê os botões: 7 dias, 15 dias, 30 dias, 60 dias, 90 dias.",
          "Clique em qualquer um deles para filtrar todos os dados pelo período desejado.",
          "O período selecionado fica destacado em azul e os valores atualizam automaticamente.",
        ],
      },
      {
        titulo: "Classificar DRE (Demonstrativo de Resultado)",
        tags: ["dre", "classificar", "lançamentos", "resultado"],
        conteudo: [
          "O botão 'Classificar DRE' abre um assistente para categorizar seus lançamentos financeiros.",
          "Isso permite que o sistema calcule corretamente receitas, custos e despesas no seu relatório.",
          "**Passo a passo:**",
          "1. Clique em 'Classificar DRE' no topo do Dashboard.",
          "2. O sistema mostra os lançamentos não classificados.",
          "3. Para cada um, escolha se é Receita, Custo ou Despesa.",
          "4. Salve. O DRE será recalculado com as novas classificações.",
        ],
      },
    ],
  },

  // ────────────── CADASTROS / PESSOAS ──────────────
  {
    modulo: "pessoas",
    label: "Pessoas (Clientes, Fornecedores, Veterinários)",
    icone: FiUsers,
    cor: "blue",
    artigos: [
      {
        titulo: "Como cadastrar um novo cliente",
        tags: ["cliente", "cadastro", "novo", "pessoas", "fornecedor"],
        conteudo: [
          "Acesse o menu **Pessoas** na barra lateral.",
          "Clique no botão **+ Novo Cadastro** (canto superior direito).",
          "Preencha os dados: nome, CPF/CNPJ, telefone, e-mail e endereço.",
          "No campo **Tipo**, escolha: Cliente, Fornecedor, Veterinário ou Funcionário.",
          "Clique em **Salvar**. O cadastro aparece na lista imediatamente.",
          "💡 Dica: O CPF/CNPJ não é obrigatório, mas facilita emissão de notas fiscais.",
        ],
      },
      {
        titulo: "Como pesquisar e filtrar pessoas",
        tags: ["pesquisar", "filtrar", "buscar", "cliente", "pessoas"],
        conteudo: [
          "Na página **Pessoas**, use a barra de pesquisa no topo da tabela.",
          "Você pode buscar por: nome, código, CPF/CNPJ, e-mail ou telefone.",
          "Use as abas para filtrar por tipo: Todos, Clientes, Fornecedores, Veterinários, Funcionários.",
          "Para alterar quantos resultados aparecem por página, use o seletor '20 por página' no canto.",
        ],
      },
      {
        titulo: "Como importar clientes em massa (planilha Excel)",
        tags: ["importar", "excel", "planilha", "clientes", "massa"],
        conteudo: [
          "**Atenção:** Prepare uma planilha Excel (.xlsx) com as colunas corretas antes de importar.",
          "**Colunas esperadas:** nome, cpf_cnpj, telefone, e-mail, tipo (Cliente/Fornecedor/etc).",
          "Clique no botão **Importar Excel** na página de Pessoas.",
          "Selecione o arquivo. O sistema valida os dados e mostra um prévia antes de confirmar.",
          "Erros são apontados linha a linha para você corrigir.",
          "Após confirmar, todos os registros válidos são importados de uma vez.",
        ],
      },
      {
        titulo: "Como ver o histórico completo de um cliente",
        tags: ["histórico", "timeline", "cliente", "compras", "pets"],
        conteudo: [
          "Clique no ícone de **editar** (lápis) ao lado do cliente na lista.",
          "Na ficha do cliente, você encontra:",
          "• **Dados pessoais** — nome, contato, endereço",
          "• **Pets** — lista de pets cadastrados vinculados a ele",
          "• **Histórico de compras** — todas as vendas feitas para este cliente",
          "• **Segmento** — tag de classificação (ex: Parceiro, VIP)",
          "💡 Clique em 'Ver Timeline Completa' para ver tudo em ordem cronológica.",
        ],
      },
    ],
  },

  // ────────────── PETS ──────────────
  {
    modulo: "pets",
    label: "Pets",
    icone: FiBookOpen,
    cor: "green",
    artigos: [
      {
        titulo: "Como cadastrar um pet",
        tags: ["pet", "animal", "cadastro", "espécie", "raça"],
        conteudo: [
          "Acesse **Pets** no menu lateral ou acesse a ficha do tutor e clique em '+ Adicionar Pet'.",
          "Preencha: nome do pet, espécie, raça, data de nascimento e sexo.",
          "Vincule o pet a um tutor (cliente já cadastrado).",
          "Você pode adicionar uma foto e informações de saúde (peso, vacinas, observações).",
          "Clique em **Salvar**.",
        ],
      },
      {
        titulo: "Espécies e Raças — como gerenciar",
        tags: ["espécie", "raça", "cadastro", "configurar"],
        conteudo: [
          "O sistema vem com espécies e raças pré-cadastradas (cão, gato, etc).",
          "Para adicionar novas: acesse **Configurações → Espécies e Raças**.",
          "Você pode criar novas espécies e associar raças a cada uma.",
          "Esses dados são usados na ficha do pet e nos relatórios.",
        ],
      },
    ],
  },

  // ────────────── PRODUTOS ──────────────
  {
    modulo: "produtos",
    label: "Produtos e Estoque",
    icone: FiPackage,
    cor: "orange",
    artigos: [
      {
        titulo: "Como cadastrar um produto",
        tags: ["produto", "cadastro", "estoque", "novo"],
        conteudo: [
          "Acesse **Produtos** no menu lateral.",
          "Clique em **+ Novo Produto**.",
          "Preencha: nome, categoria, preço de venda, custo, código de barras (opcional).",
          "Defina o **estoque inicial** — quantidade que você já tem em mãos.",
          "Configure o **estoque mínimo** para receber alertas quando acabar.",
          "Clique em **Salvar**.",
          "💡 O produto já aparece disponível no PDV após salvar.",
        ],
      },
      {
        titulo: "Como pesquisar e filtrar produtos",
        tags: ["buscar", "pesquisar", "filtrar", "produto", "categoria"],
        conteudo: [
          "Na página **Produtos**, use a barra de busca para pesquisar por nome ou código.",
          "Use os filtros de categoria para ver apenas rações, brinquedos, medicamentos, etc.",
          "O botão de filtro avançado permite filtrar por: faixa de preço, estoque baixo, fornecedor.",
          "A lista mostra: nome, código, preço, estoque atual e status.",
        ],
      },
      {
        titulo: "Alertas de estoque baixo",
        tags: ["estoque", "alerta", "mínimo", "reposição"],
        conteudo: [
          "Quando um produto atinge ou passa abaixo do **estoque mínimo**, ele aparece nos Alertas.",
          "Acesse **Produtos → Alertas de Estoque** para ver a lista completa.",
          "O Dashboard também exibe um resumo de produtos com estoque crítico.",
          "Para configurar o estoque mínimo de um produto: edite o produto e defina o campo 'Estoque Mínimo'.",
        ],
      },
      {
        titulo: "Como importar produtos em massa",
        tags: ["importar", "excel", "planilha", "produto", "massa"],
        conteudo: [
          "Clique em **Importar Excel** na página de Produtos.",
          "Use a planilha modelo disponível para download no mesmo botão.",
          "Colunas obrigatórias: nome, preco_venda, categoria.",
          "Colunas opcionais: custo, codigo_barras, estoque_inicial, estoque_minimo.",
          "Após importar, revise os produtos criados na lista.",
        ],
      },
      {
        titulo: "Como usar o relatório de produtos",
        tags: ["relatório", "produto", "vendas", "análise"],
        conteudo: [
          "Acesse **Produtos → Relatório** para ver análises detalhadas.",
          "Mostra: produtos mais vendidos, margem de lucro por produto, giro de estoque.",
          "Filtre por período para comparar desempenho.",
          "Exporte os dados para Excel clicando em 'Exportar'.",
        ],
      },
    ],
  },

  // ────────────── PDV / VENDAS ──────────────
  {
    modulo: "pdv",
    label: "PDV — Ponto de Venda",
    icone: FiShoppingCart,
    cor: "yellow",
    artigos: [
      {
        titulo: "Como fazer uma venda no PDV",
        tags: ["venda", "pdv", "caixa", "vender", "produto"],
        conteudo: [
          "Acesse **PDV (Vendas)** no menu lateral.",
          "**1. Selecione o cliente** — comece digitando o nome ou CPF do cliente. Se for venda sem cliente, deixe em branco.",
          "**2. Adicione produtos** — use a barra de busca para procurar pelo nome ou código de barras.",
          "Clique no produto ou pressione Enter para adicionar ao carrinho.",
          "**3. Ajuste quantidades** — clique nos botões + e - no carrinho ou digite direto.",
          "**4. Aplique desconto** — no resumo, clique em 'Desconto' e informe o valor ou percentual.",
          "**5. Escolha o pagamento** — dinheiro, cartão débito/crédito, Pix ou misto.",
          "**6. Finalize** — clique em 'Finalizar Venda'. O sistema gera o recibo e atualiza o estoque automaticamente.",
        ],
      },
      {
        titulo: "Como abrir e fechar o caixa",
        tags: ["caixa", "abrir", "fechar", "sangria", "suprimento"],
        conteudo: [
          "Acesse **PDV → Meus Caixas** no menu.",
          "**Abrir caixa:** clique em 'Abrir Caixa' e informe o valor de troco inicial.",
          "**Sangria:** retira dinheiro do caixa durante o dia. Registre o motivo.",
          "**Suprimento:** adiciona dinheiro ao caixa. Registre o motivo.",
          "**Fechar caixa:** conta o dinheiro físico, o sistema compara com o esperado e mostra a diferença.",
          "O relatório de fechamento fica salvo no histórico de caixas.",
        ],
      },
      {
        titulo: "Formas de pagamento disponíveis",
        tags: ["pagamento", "dinheiro", "cartão", "pix", "crédito", "débito"],
        conteudo: [
          "O PDV aceita as seguintes formas de pagamento:",
          "• **Dinheiro** — informe o valor recebido, o sistema calcula o troco.",
          "• **Cartão de Débito** — registre a operadora do cartão.",
          "• **Cartão de Crédito** — pode parcelar em até 12x.",
          "• **Pix** — registre o valor recebido via Pix.",
          "• **Pagamento Misto** — combine duas ou mais formas (ex: metade no cartão, metade em Pix).",
          "💡 O sistema registra cada forma separadamente para a conciliação financeira.",
        ],
      },
      {
        titulo: "Como ver e cancelar uma venda",
        tags: ["cancelar", "venda", "histórico", "estorno"],
        conteudo: [
          "No PDV, role a tela para baixo para ver o **Histórico de Vendas**.",
          "Ou acesse **Financeiro → Vendas** para ver todas as vendas.",
          "Para cancelar: clique na venda e depois em 'Cancelar Venda'.",
          "O sistema estorna os itens no estoque automaticamente.",
          "**Atenção:** vendas canceladas não são deletadas — ficam registradas como 'Cancelada' para auditoria.",
        ],
      },
    ],
  },

  // ────────────── FINANCEIRO ──────────────
  {
    modulo: "financeiro",
    label: "Financeiro",
    icone: FiDollarSign,
    cor: "green",
    artigos: [
      {
        titulo: "Como registrar uma conta a receber",
        tags: ["conta a receber", "receber", "receita", "cliente", "débito"],
        conteudo: [
          "Acesse **Financeiro → Contas a Receber**.",
          "Clique em **+ Nova Conta**.",
          "Preencha: cliente, valor, data de vencimento, descrição.",
          "Escolha a categoria (ex: Venda, Serviço, Outros).",
          "Salve. A conta aparece na lista com status 'Pendente'.",
          "**Registrar pagamento:** clique na conta e depois em 'Marcar como Pago'. Informe a data e forma de pagamento.",
        ],
      },
      {
        titulo: "Como registrar uma conta a pagar",
        tags: ["conta a pagar", "pagar", "despesa", "fornecedor", "custo"],
        conteudo: [
          "Acesse **Financeiro → Contas a Pagar**.",
          "Clique em **+ Nova Conta**.",
          "Preencha: fornecedor (opcional), valor, data de vencimento, descrição, categoria.",
          "Salve. A conta aparece na lista com status 'Pendente'.",
          "**Registrar pagamento:** clique na conta e depois em 'Marcar como Pago'.",
          "💡 Contas vencidas aparecem destacadas em vermelho no Dashboard e enviam alertas.",
        ],
      },
      {
        titulo: "Fluxo de Caixa — como usar",
        tags: ["fluxo de caixa", "entradas", "saídas", "financeiro"],
        conteudo: [
          "O Fluxo de Caixa mostra todas as movimentações financeiras: entradas e saídas.",
          "Acesse **Financeiro → Fluxo de Caixa** ou clique no card 'Saldo Atual' no Dashboard.",
          "O gráfico mostra a evolução diária do saldo.",
          "A tabela lista cada movimentação com data, descrição, tipo e valor.",
          "Use os filtros de data para ver períodos específicos.",
          "Exporte para Excel clicando em 'Exportar'.",
        ],
      },
      {
        titulo: "Conciliação Bancária — o que é e como fazer",
        tags: [
          "conciliação",
          "bancária",
          "banco",
          "extrato",
          "conferir",
          "cartão",
        ],
        conteudo: [
          "A conciliação bancária é o processo de **comparar os lançamentos do sistema com o extrato do seu banco**.",
          "Acesse **Financeiro → Conciliação Bancária**.",
          "Importe o extrato do banco (arquivo OFX ou CSV) ou lance manualmente.",
          "O sistema cruza automaticamente os lançamentos e marca os que batem.",
          "Os que não batem ficam pendentes para você revisar e confirmar.",
          "**Conciliação de Cartões:** mesma lógica, mas para os recebimentos de cartão de débito e crédito.",
        ],
      },
      {
        titulo: "DRE — Demonstrativo de Resultado",
        tags: ["dre", "resultado", "lucro", "despesa", "receita"],
        conteudo: [
          "O DRE mostra se o seu negócio teve **lucro ou prejuízo** no período.",
          "Acesse **Financeiro → DRE** ou clique no card 'Lucro' no Dashboard.",
          "**Receitas** — tudo que entrou (vendas, serviços).",
          "**Custos** — custo dos produtos vendidos (CMV).",
          "**Despesas Operacionais** — aluguel, salários, água, luz, etc.",
          "**Resultado** — Receitas menos Custos e Despesas.",
          "Para o DRE funcionar corretamente, classifique seus lançamentos usando o botão 'Classificar DRE' no Dashboard.",
        ],
      },
      {
        titulo: "Projeção de Caixa",
        tags: ["projeção", "caixa", "futuro", "previsão"],
        conteudo: [
          "A projeção mostra como estará seu caixa nos próximos dias com base em contas a receber e a pagar já lançadas.",
          "Acesse **Financeiro → Projeção de Caixa**.",
          "Mostra um gráfico dia a dia com o saldo esperado.",
          "Ajuda a identificar datas críticas onde o caixa pode ficar negativo.",
        ],
      },
      {
        titulo: "Categorias Financeiras — como personalizar",
        tags: ["categoria", "financeiro", "classificar", "personalizar"],
        conteudo: [
          "Acesse **Financeiro → Categorias** para criar, editar ou remover categorias.",
          "Exemplos de categorias: Aluguel, Energia, Compra de Estoque, Serviços Veterinários.",
          "Categorias bem definidas deixam o DRE e os relatórios muito mais claros.",
          "**Subcategorias:** você pode criar subcategorias para detalhamento ainda maior.",
        ],
      },
    ],
  },

  // ────────────── LEMBRETES ──────────────
  {
    modulo: "lembretes",
    label: "Lembretes e Agendamentos",
    icone: FiCalendar,
    cor: "purple",
    artigos: [
      {
        titulo: "Como criar um lembrete",
        tags: ["lembrete", "agendamento", "criar", "notificação"],
        conteudo: [
          "Acesse **Lembretes** no menu lateral.",
          "Clique em **+ Novo Lembrete**.",
          "Preencha: título, data, hora, cliente (opcional) e observações.",
          "Escolha o tipo: Consulta, Banho e Tosa, Vacina, Retorno, Outro.",
          "Salve. O lembrete aparece no calendário e na lista.",
          "💡 Lembretes com data chegando ficam destacados na lista.",
        ],
      },
      {
        titulo: "Como ver os lembretes do dia",
        tags: ["lembrete", "hoje", "dia", "agenda"],
        conteudo: [
          "Na página de Lembretes, o filtro padrão mostra os lembretes de hoje.",
          "Use os botões de filtro para ver: Hoje, Esta Semana, Este Mês ou Todos.",
          "Lembretes vencidos (data passada, não concluídos) aparecem marcados em vermelho.",
          "Clique em um lembrete para editar, marcar como concluído ou excluir.",
        ],
      },
    ],
  },

  // ────────────── CALCULADORA DE RAÇÃO ──────────────
  {
    modulo: "calculadora",
    label: "Calculadora de Ração",
    icone: FiCpu,
    cor: "teal",
    artigos: [
      {
        titulo: "Como usar a Calculadora de Ração",
        tags: ["ração", "calculadora", "nutrição", "pet", "quantidade"],
        conteudo: [
          "Acesse **Calculadora de Ração** no menu lateral.",
          "Informe os dados do pet: espécie, raça, peso atual, idade e nível de atividade.",
          "Selecione a ração disponível no estoque ou informe os dados manualmente.",
          "O sistema calcula: quantidade diária recomendada, custo por dia e quanto um pacote vai durar.",
          "Use os resultados para orientar os tutores na compra da quantidade correta.",
          "💡 Você pode salvar perfis de pets para calcular rapidamente no futuro.",
        ],
      },
    ],
  },

  // ────────────── NOTAS FISCAIS ──────────────
  {
    modulo: "nfe",
    label: "Notas Fiscais",
    icone: FiBookOpen,
    cor: "gray",
    artigos: [
      {
        titulo: "Como emitir uma nota fiscal",
        tags: ["nota fiscal", "nfe", "nfce", "emitir", "imposto"],
        conteudo: [
          "Acesse **Notas Fiscais** no menu lateral.",
          "Clique em **+ Nova Nota**.",
          "Selecione o cliente (com CPF/CNPJ cadastrado para emissão com destinatário).",
          "Adicione os produtos/serviços, quantidades e valores.",
          "Selecione a natureza de operação e o CFOP correto.",
          "Clique em **Emitir**. A nota é enviada para a SEFAZ e o XML/PDF ficam disponíveis.",
          "**Atenção:** configure os dados da empresa e o certificado digital em Configurações antes de emitir a primeira nota.",
        ],
      },
    ],
  },

  // ────────────── CONFIGURAÇÕES ──────────────
  {
    modulo: "configuracoes",
    label: "Configurações",
    icone: FiSettings,
    cor: "gray",
    artigos: [
      {
        titulo: "Como configurar os dados da empresa",
        tags: [
          "empresa",
          "cnpj",
          "dados",
          "razão social",
          "logo",
          "configuração",
        ],
        conteudo: [
          "Acesse **Configurações** no menu lateral.",
          "Na aba **Empresa**, preencha: razão social, CNPJ, endereço, telefone, e-mail.",
          "Faça upload do logotipo da empresa (aparece nos recibos e documentos).",
          "Salve as alterações. Os dados aparecem automaticamente nos documentos gerados.",
        ],
      },
      {
        titulo: "Como criar e gerenciar usuários",
        tags: ["usuário", "acesso", "permissão", "criar", "colaborador"],
        conteudo: [
          "Acesse **Configurações → Usuários**.",
          "Clique em **+ Novo Usuário**.",
          "Preencha: nome, e-mail, senha e perfil de acesso (Admin, Vendedor, Financeiro, etc).",
          "Cada perfil tem permissões diferentes:",
          "• **Admin** — acesso total ao sistema.",
          "• **Vendedor** — acesso ao PDV e Produtos.",
          "• **Financeiro** — acesso ao módulo financeiro.",
          "Após salvar, o usuário recebe os dados de acesso por e-mail.",
        ],
      },
      {
        titulo: "Como definir permissões por perfil",
        tags: ["permissão", "perfil", "cargo", "acesso", "roles"],
        conteudo: [
          "Acesse **Configurações → Perfis de Acesso**.",
          "Veja os perfis existentes ou crie um novo.",
          "Para cada perfil, marque ou desmarque as permissões por módulo.",
          "Exemplos de permissões: 'ver financeiro', 'emitir nota fiscal', 'cancelar venda'.",
          "Ao salvar, todos os usuários com aquele perfil são atualizados automaticamente.",
        ],
      },
      {
        titulo: "Operadoras de Cartão — como cadastrar",
        tags: ["operadora", "cartão", "cielo", "stone", "rede", "taxa"],
        conteudo: [
          "Acesse **Financeiro → Operadoras de Cartão**.",
          "Cadastre cada operadora com: nome, taxa de débito e taxa de crédito.",
          "Essas taxas são usadas nos relatórios de conciliação para calcular o valor líquido recebido.",
          "Você pode ter múltiplas operadoras cadastradas (Cielo, Stone, Rede, etc).",
        ],
      },
    ],
  },

  // ────────────── COMPRAS / PEDIDOS BLING ──────────────
  {
    modulo: "compras",
    label: "Compras e Pedidos",
    icone: FiTruck,
    cor: "blue",
    artigos: [
      {
        titulo: "Como registrar uma compra de estoque",
        tags: ["compra", "estoque", "fornecedor", "repor", "entrada"],
        conteudo: [
          "Acesse **Compras** no menu lateral.",
          "Clique em **+ Nova Compra**.",
          "Selecione o fornecedor e adicione os produtos comprados com as quantidades e custos.",
          "Salve. O estoque é atualizado automaticamente com as quantidades informadas.",
          "O custo registrado é usado para cálculo de margem e CMV no DRE.",
        ],
      },
      {
        titulo: "Integração com Bling (Pedidos)",
        tags: ["bling", "pedido", "integração", "erp"],
        conteudo: [
          "Acesse **Pedidos Bling** no menu lateral.",
          "Esta tela mostra os pedidos sincronizados com o sistema Bling.",
          "Use para acompanhar pedidos de fornecedores e integrações de marketplace.",
          "Configure a chave de API do Bling em **Configurações → Integrações**.",
        ],
      },
    ],
  },

  // ────────────── IA / ASSISTENTE ──────────────
  {
    modulo: "ia",
    label: "Inteligência Artificial",
    icone: FiCpu,
    cor: "purple",
    artigos: [
      {
        titulo: "Como usar o Chat com IA",
        tags: ["ia", "inteligência artificial", "chat", "assistente", "dúvida"],
        conteudo: [
          "Acesse **IA → Chat** no menu lateral.",
          "Digite sua pergunta ou descreva o que precisa de ajuda.",
          "A IA conhece os dados do seu sistema e pode responder perguntas como:",
          "• 'Quais produtos estão com estoque baixo?'",
          "• 'Qual foi minha venda total no último mês?'",
          "• 'Quais clientes têm contas vencidas?'",
          "As respostas são baseadas nos dados reais do seu sistema.",
        ],
      },
      {
        titulo: "IA de Fluxo de Caixa — previsões inteligentes",
        tags: ["ia", "fluxo de caixa", "previsão", "projeção", "inteligente"],
        conteudo: [
          "Acesse **IA → Fluxo de Caixa** no menu lateral.",
          "A IA analisa seu histórico financeiro e projeta tendências futuras.",
          "Mostra alertas inteligentes como: 'Com base no histórico, seu caixa pode ficar negativo em X dias'.",
          "Use para tomar decisões antecipadas sobre compras e investimentos.",
        ],
      },
    ],
  },

  // ────────────── MÓDULOS PREMIUM ──────────────
  {
    modulo: "premium",
    label: "Módulos Premium",
    icone: FiGlobe,
    cor: "indigo",
    artigos: [
      {
        titulo: "Módulo Campanhas — o que faz",
        tags: [
          "campanha",
          "marketing",
          "promoção",
          "desconto",
          "cliente",
          "premium",
        ],
        conteudo: [
          "O módulo Campanhas permite criar promoções e comunicações direcionadas para seus clientes.",
          "• Crie campanhas com desconto por produto, categoria ou valor mínimo de compra.",
          "• Segmente por perfil: clientes que não compram há X dias, aniversariantes, etc.",
          "• Envie comunicados via WhatsApp ou e-mail para a base segmentada.",
          "**Como contratar:** acesse Ajuda e Planos e clique em 'Contratar' no módulo Campanhas.",
        ],
      },
      {
        titulo: "Módulo Entregas — o que faz",
        tags: ["entrega", "delivery", "rota", "motorista", "premium"],
        conteudo: [
          "Gerencie entregas dos pedidos feitos no sistema.",
          "• Atribua pedidos a motoristas/entregadores.",
          "• Acompanhe o status de cada entrega (Pendente, Saiu para entrega, Entregue).",
          "• Gere rotas otimizadas para o entregador.",
          "• O cliente pode receber notificações automáticas sobre o status.",
        ],
      },
      {
        titulo: "Módulo WhatsApp — o que faz",
        tags: ["whatsapp", "mensagem", "bot", "atendimento", "premium"],
        conteudo: [
          "Integre o WhatsApp Business ao sistema para atendimento automatizado.",
          "• Responda perguntas comuns automaticamente (horário, preços, etc).",
          "• Envie notificações de pedidos, cobranças e promoções pelo WhatsApp.",
          "• Veja todo o histórico de conversas no sistema.",
          "• Configure fluxos de atendimento personalizados.",
        ],
      },
      {
        titulo: "Módulo E-commerce — o que faz",
        tags: ["e-commerce", "loja virtual", "site", "online", "premium"],
        conteudo: [
          "Crie uma loja virtual integrada diretamente ao seu estoque do sistema.",
          "• Os pedidos feitos online entram automaticamente no sistema.",
          "• Estoque sincronizado: quando vende online, baixa do estoque local.",
          "• Painel de gestão de pedidos online.",
          "• Integração com gateways de pagamento.",
        ],
      },
      {
        titulo: "App Mobile — o que faz",
        tags: [
          "app",
          "mobile",
          "celular",
          "aplicativo",
          "android",
          "ios",
          "premium",
        ],
        conteudo: [
          "Acesse o sistema pelo celular com o app dedicado.",
          "• Faça vendas pelo celular (PDV mobile).",
          "• Consulte estoque e clientes de qualquer lugar.",
          "• Receba notificações de alertas importantes.",
          "• Disponível para Android e iOS.",
        ],
      },
    ],
  },
];

/* ──────────────────────────────────────────────────────────────
   Utilitários
────────────────────────────────────────────────────────────── */
const COR_CLASSES = {
  indigo: {
    bg: "bg-indigo-50",
    text: "text-indigo-700",
    border: "border-indigo-200",
    icon: "text-indigo-500",
    tab: "bg-indigo-600 text-white",
  },
  blue: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    border: "border-blue-200",
    icon: "text-blue-500",
    tab: "bg-blue-600 text-white",
  },
  green: {
    bg: "bg-green-50",
    text: "text-green-700",
    border: "border-green-200",
    icon: "text-green-500",
    tab: "bg-green-600 text-white",
  },
  orange: {
    bg: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-200",
    icon: "text-orange-500",
    tab: "bg-orange-600 text-white",
  },
  yellow: {
    bg: "bg-yellow-50",
    text: "text-yellow-700",
    border: "border-yellow-200",
    icon: "text-yellow-500",
    tab: "bg-yellow-500 text-white",
  },
  purple: {
    bg: "bg-purple-50",
    text: "text-purple-700",
    border: "border-purple-200",
    icon: "text-purple-500",
    tab: "bg-purple-600 text-white",
  },
  teal: {
    bg: "bg-teal-50",
    text: "text-teal-700",
    border: "border-teal-200",
    icon: "text-teal-500",
    tab: "bg-teal-600 text-white",
  },
  gray: {
    bg: "bg-gray-50",
    text: "text-gray-700",
    border: "border-gray-200",
    icon: "text-gray-500",
    tab: "bg-gray-600 text-white",
  },
};

/* Renderiza parágrafo com **negrito** */
const Paragrafo = ({ texto }) => {
  const partes = texto.split(/\*\*(.*?)\*\*/g);
  return (
    <p className="text-sm text-gray-700 leading-relaxed">
      {partes.map((parte, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-semibold text-gray-900">
            {parte}
          </strong>
        ) : (
          parte
        ),
      )}
    </p>
  );
};

/* Card de artigo expansível */
const CardArtigo = ({ artigo, corClasses, destaqueTexto }) => {
  const [aberto, setAberto] = useState(!!destaqueTexto);

  const tituloDestacado = destaqueTexto
    ? artigo.titulo.replace(
        new RegExp(`(${destaqueTexto})`, "gi"),
        '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>',
      )
    : artigo.titulo;

  return (
    <div
      className={`border rounded-xl overflow-hidden transition-shadow ${aberto ? "shadow-md border-gray-300" : "border-gray-200 hover:border-gray-300"}`}
    >
      <button
        onClick={() => setAberto(!aberto)}
        className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <span
          className="text-sm font-semibold text-gray-800"
          dangerouslySetInnerHTML={{ __html: tituloDestacado }}
        />
        <span className="flex-shrink-0">
          {aberto ? (
            <FiChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <FiChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </span>
      </button>
      {aberto && (
        <div
          className={`px-5 pb-5 space-y-2 ${corClasses.bg} border-t border-gray-100`}
        >
          {artigo.conteudo.map((linha, i) => (
            <Paragrafo key={i} texto={linha} />
          ))}
        </div>
      )}
    </div>
  );
};

/* ──────────────────────────────────────────────────────────────
   Componente principal
────────────────────────────────────────────────────────────── */
const CentralAjuda = () => {
  const [busca, setBusca] = useState("");
  const [moduloAtivo, setModuloAtivo] = useState(null); // null = todos

  /* Filtra artigos pela busca */
  const resultados = useMemo(() => {
    const termo = busca.toLowerCase().trim();
    if (!termo && !moduloAtivo) return null; // sem filtro: mostra normal

    return BASE_CONHECIMENTO.flatMap((mod) => {
      if (moduloAtivo && mod.modulo !== moduloAtivo) return [];
      return mod.artigos
        .filter((a) => {
          if (!termo) return true;
          return (
            a.titulo.toLowerCase().includes(termo) ||
            a.tags.some((t) => t.includes(termo)) ||
            a.conteudo.some((c) => c.toLowerCase().includes(termo))
          );
        })
        .map((a) => ({ ...a, _modulo: mod }));
    });
  }, [busca, moduloAtivo]);

  const totalArtigos = BASE_CONHECIMENTO.reduce(
    (acc, m) => acc + m.artigos.length,
    0,
  );

  return (
    <div className="max-w-4xl mx-auto py-6 px-4">
      {/* Cabeçalho da central */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 px-4 py-1.5 rounded-full text-sm font-medium mb-3">
          <FiBookOpen className="w-4 h-4" />
          {totalArtigos} artigos de ajuda
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Como posso te ajudar?
        </h2>
        <p className="text-gray-500 text-sm">
          Pesquise por qualquer dúvida ou navegue pelos módulos abaixo.
        </p>
      </div>

      {/* Barra de busca */}
      <div className="relative mb-6">
        <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por dúvida, funcionalidade ou palavra-chave..."
          className="w-full pl-12 pr-4 py-3.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent shadow-sm"
        />
        {busca && (
          <button
            onClick={() => setBusca("")}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg"
          >
            ×
          </button>
        )}
      </div>

      {/* Filtro por módulo (chips) */}
      <div className="flex flex-wrap gap-2 mb-8">
        <button
          onClick={() => setModuloAtivo(null)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            !moduloAtivo
              ? "bg-gray-800 text-white border-gray-800"
              : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
          }`}
        >
          Todos
        </button>
        {BASE_CONHECIMENTO.map((mod) => {
          const cores = COR_CLASSES[mod.cor] || COR_CLASSES.gray;
          const ativo = moduloAtivo === mod.modulo;
          return (
            <button
              key={mod.modulo}
              onClick={() => setModuloAtivo(ativo ? null : mod.modulo)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                ativo
                  ? `${cores.tab} border-transparent`
                  : `bg-white text-gray-600 border-gray-300 hover:border-gray-400`
              }`}
            >
              {mod.label}
            </button>
          );
        })}
      </div>

      {/* Resultados de busca */}
      {resultados !== null ? (
        <div>
          {resultados.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <FiSearch className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-base font-medium">
                Nenhum resultado encontrado
              </p>
              <p className="text-sm mt-1">
                Tente palavras diferentes ou{" "}
                <button
                  onClick={() => {
                    setBusca("");
                    setModuloAtivo(null);
                  }}
                  className="text-indigo-600 underline"
                >
                  navegue por módulo
                </button>
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-gray-500 mb-4">
                {resultados.length} resultado
                {resultados.length !== 1 ? "s" : ""} encontrado
                {resultados.length !== 1 ? "s" : ""}
                {busca && (
                  <>
                    {" "}
                    para <strong className="text-gray-700">"{busca}"</strong>
                  </>
                )}
              </p>
              {resultados.map((artigo, i) => {
                const cors =
                  COR_CLASSES[artigo._modulo.cor] || COR_CLASSES.gray;
                return (
                  <div key={i}>
                    <div
                      className={`text-xs font-medium ${cors.text} mb-1 px-1`}
                    >
                      {artigo._modulo.label}
                    </div>
                    <CardArtigo
                      artigo={artigo}
                      corClasses={cors}
                      destaqueTexto={busca}
                    />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        /* Exibição normal por módulo */
        <div className="space-y-10">
          {BASE_CONHECIMENTO.map((mod) => {
            const cors = COR_CLASSES[mod.cor] || COR_CLASSES.gray;
            const Icone = mod.icone;
            return (
              <section key={mod.modulo}>
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className={`w-9 h-9 rounded-xl ${cors.bg} flex items-center justify-center flex-shrink-0`}
                  >
                    <Icone className={`w-5 h-5 ${cors.icon}`} />
                  </div>
                  <h3 className="text-base font-bold text-gray-900">
                    {mod.label}
                  </h3>
                  <span className="text-xs text-gray-400 font-normal">
                    {mod.artigos.length} artigo
                    {mod.artigos.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="space-y-2">
                  {mod.artigos.map((artigo, i) => (
                    <CardArtigo
                      key={i}
                      artigo={artigo}
                      corClasses={cors}
                      destaqueTexto={null}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CentralAjuda;
