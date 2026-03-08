/**
 * Definições dos tours guiados por página.
 *
 * Cada tour é um array de passos para o driver.js.
 * O elemento é referenciado pelo `element` (seletor CSS: ID, classe, etc).
 * Se o elemento não existir na tela, o driver.js mostra o popover centrado.
 */

// ─── DASHBOARD ───────────────────────────────────────────────────────────────
export const tourDashboard = [
  {
    popover: {
      title: "👋 Bem-vindo ao Sistema!",
      description:
        "Vou te mostrar os pontos principais desta tela. Use os botões abaixo para navegar.",
    },
  },
  {
    element: "#tour-stats",
    popover: {
      title: "📊 Resumo do Negócio",
      description:
        "Aqui ficam os números mais importantes: total de vendas, clientes ativos, produtos cadastrados e faturamento do período.",
      side: "bottom",
    },
  },
  {
    element: "#tour-financeiro",
    popover: {
      title: "💰 Resumo Financeiro",
      description:
        "Veja o faturamento bruto, as despesas e o lucro líquido. Os valores são atualizados conforme você registra vendas e lançamentos.",
      side: "top",
    },
  },
  {
    element: "#tour-composicao",
    popover: {
      title: "📈 Composição do Faturamento",
      description:
        "Esta barra mostra visualmente quanto do faturamento bruto virou lucro, quanto foi gasto em despesas e quanto foi para impostos.",
      side: "top",
    },
  },
  {
    element: "#tour-acoes-rapidas",
    popover: {
      title: "⚡ Ações Rápidas",
      description:
        "Atalhos para as tarefas mais comuns: iniciar uma venda, cadastrar um cliente ou adicionar um produto.",
      side: "left",
    },
  },
];

// ─── PESSOAS (CLIENTES) ───────────────────────────────────────────────────────
export const tourPessoas = [
  {
    popover: {
      title: "👥 Gestão de Pessoas",
      description:
        "Aqui você gerencia clientes, fornecedores e veterinários em um só lugar. Vamos ver como funciona!",
    },
  },
  {
    element: "#tour-pessoas-nova",
    popover: {
      title: "➕ Cadastrar Nova Pessoa",
      description:
        "Clique aqui para adicionar um novo cliente, fornecedor ou veterinário. Você vai preencher nome, CPF/CNPJ, contato e outras informações.",
      side: "left",
    },
  },
  {
    element: "#tour-pessoas-importar",
    popover: {
      title: "📥 Importação em Massa",
      description:
        "Tem uma lista de clientes numa planilha? Aqui você pode importar tudo de uma vez, sem precisar cadastrar um por um.",
      side: "left",
    },
  },
  {
    element: "#tour-pessoas-filtros",
    popover: {
      title: "🔍 Busca e Filtros",
      description:
        "Use a busca para encontrar alguém pelo nome, CPF ou CNPJ. O filtro do lado deixa você ver só clientes, só fornecedores, ou só veterinários.",
      side: "bottom",
    },
  },
  {
    element: "#tour-pessoas-tabela",
    popover: {
      title: "📋 Lista de Pessoas",
      description:
        'Aqui aparecem todas as pessoas cadastradas. Clique em "Editar" para ver o histórico completo de compras, endereço e outras informações.',
      side: "top",
    },
  },
];

// ─── PRODUTOS ─────────────────────────────────────────────────────────────────
export const tourProdutos = [
  {
    popover: {
      title: "📦 Catálogo de Produtos",
      description:
        "Nesta página você controla todos os produtos: preços, estoque, categorias e muito mais. Vamos dar uma olhada!",
    },
  },
  {
    element: "#tour-produtos-novo",
    popover: {
      title: "➕ Novo Produto",
      description:
        "Clique aqui para cadastrar um novo produto. Você define o nome, código de barras, preço de venda e preço de custo.",
      side: "left",
    },
  },
  {
    element: "#tour-produtos-importar",
    popover: {
      title: "📥 Importar do Excel",
      description:
        "Tem uma lista de produtos numa planilha? Importe todos de uma vez usando este botão.",
      side: "left",
    },
  },
  {
    element: "#tour-produtos-busca",
    popover: {
      title: "🔍 Busca Rápida",
      description:
        "Digite o nome, código ou referência do produto. A lista filtra em tempo real enquanto você digita.",
      side: "bottom",
    },
  },
  {
    element: "#tour-produtos-filtros",
    popover: {
      title: "🏷️ Filtros Avançados",
      description:
        "Filtre por categoria, marca ou status do estoque. Muito útil para ver quais produtos estão com estoque baixo.",
      side: "bottom",
    },
  },
  {
    element: "#tour-produtos-lista",
    popover: {
      title: "📋 Lista de Produtos",
      description:
        "Aqui aparecem todos os produtos. Você pode editar, ver o histórico de vendas e ajustar o estoque diretamente por aqui.",
      side: "top",
    },
  },
];

// ─── PDV (PONTO DE VENDA) ─────────────────────────────────────────────────────
export const tourPDV = [
  {
    popover: {
      title: "🛒 Ponto de Venda",
      description:
        "Esta é a tela onde você registra as vendas. Aqui fica tudo: busca de produtos, carrinho, cliente e pagamento. Vou te mostrar cada parte!",
    },
  },
  {
    element: "#tour-pdv-cliente",
    popover: {
      title: "👤 Cliente da Venda",
      description:
        "Associe um cliente à venda. Digite o nome ou parte do nome e selecione. Além de identificar o comprador, o sistema registra o histórico de compras dele automaticamente.",
      side: "bottom",
    },
  },
  {
    element: "#tour-pdv-busca",
    popover: {
      title: "🔍 Busca de Produtos",
      description:
        "Digite o nome, código de barras ou referência do produto aqui. A busca mostra o preço e o estoque disponível.",
      side: "bottom",
    },
  },
  {
    element: "#tour-pdv-carrinho",
    popover: {
      title: "🛍️ Carrinho da Venda",
      description:
        "Os produtos adicionados aparecem aqui. Você pode ajustar as quantidades, aplicar desconto por item e ver o subtotal em tempo real.",
      side: "right",
    },
  },
  {
    element: "#tour-pdv-resumo",
    popover: {
      title: "💳 Resumo e Pagamento",
      description:
        'Aqui fica o total da venda, espaço para desconto geral e o botão de pagamento. Ao clicar em "Finalizar Venda", você escolhe a forma de pagamento (dinheiro, cartão, crediário etc.).',
      side: "left",
    },
  },
];

// ─── LEMBRETES ────────────────────────────────────────────────────────────────
export const tourLembretes = [
  {
    popover: {
      title: "🔔 Lembretes do Sistema",
      description:
        "Os lembretes avisam você sobre consultas, vacinas, retornos de clientes e outras tarefas agendadas. Veja como usar!",
    },
  },
  {
    element: "#tour-lembretes-novo",
    popover: {
      title: "➕ Novo Lembrete",
      description:
        "Crie um lembrete para uma data específica: retorno de cliente, vacinação do pet, reunião, ou qualquer coisa que você queira ser avisado.",
      side: "left",
    },
  },
  {
    element: "#tour-lembretes-lista",
    popover: {
      title: "📋 Seus Lembretes",
      description:
        "Aqui aparecem todos os lembretes programados. Os atrasados ficam destacados em vermelho para você não perder nenhum.",
      side: "top",
    },
  },
];

// ─── FINANCEIRO / CAIXA ───────────────────────────────────────────────────────
export const tourMeusCaixas = [
  {
    popover: {
      title: "💰 Controle de Caixa",
      description:
        "Aqui você abre e fecha o caixa, registra entradas e saídas manuais e acompanha o saldo em tempo real.",
    },
  },
  {
    element: "#tour-caixa-abrir",
    popover: {
      title: "🔓 Abrir Caixa",
      description:
        "Antes de começar as vendas do dia, abra o caixa informando o valor inicial (troco). O sistema fecha o período e registra tudo automaticamente.",
      side: "bottom",
    },
  },
  {
    element: "#tour-caixa-historico",
    popover: {
      title: "📅 Histórico de Caixas",
      description:
        "Veja todos os caixas abertos e fechados, com o resumo de entradas, saídas e saldo final de cada período.",
      side: "top",
    },
  },
];
