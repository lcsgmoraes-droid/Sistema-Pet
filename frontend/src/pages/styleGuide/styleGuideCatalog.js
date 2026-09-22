export const STYLEGUIDE_STATUS = {
  pronto: { label: "Pronto", intent: "success" },
  planejado: { label: "Planejado", intent: "neutral" },
};

export const styleGuideCatalog = [
  {
    categoria: "Campos de formulário",
    origem: "item 1.6 do roadmap",
    itens: [
      {
        nome: "InputTexto",
        status: "pronto",
        arquivo: "components/v2/InputTexto/InputTexto.jsx",
        descricao: "Base de todos os campos de texto",
      },
      {
        nome: "InputTextoLongo",
        status: "pronto",
        arquivo: "components/v2/InputTextoLongo/InputTextoLongo.jsx",
        descricao: "Textarea — mesma aparência do InputTexto, com `linhas` controlando a altura",
      },
      { nome: "InputSenha", status: "pronto", arquivo: "components/v2/InputSenha/InputSenha.jsx" },
      {
        nome: "InputData / InputDataHora",
        status: "pronto",
        arquivo: "components/v2/InputData/",
        descricao: "Máscara dd/mm/aaaa + seletor visual (CalendarioPainel), valor em ISO",
      },
      {
        nome: "InputPeriodo",
        status: "pronto",
        arquivo: "components/v2/InputPeriodo/InputPeriodo.jsx",
        descricao: "Um único campo (somente leitura) + calendário duplo para início/fim",
      },
      {
        nome: "CalendarioPainel / CalendarioIntervaloPainel",
        status: "pronto",
        arquivo: "components/v2/CalendarioPainel/, components/v2/CalendarioIntervaloPainel/",
        descricao: "Grade de mês reaproveitada pelos campos de data — não usar direto numa tela",
      },
      {
        nome: "InputCheck / InputRadio",
        status: "pronto",
        arquivo: "components/v2/InputCheck/, components/v2/InputRadio/",
        descricao: "Aparência de botão, label centralizada",
      },
      {
        nome: "InputCheckTexto",
        status: "pronto",
        arquivo: "components/v2/InputCheckTexto/InputCheckTexto.jsx",
        descricao:
          "Checkbox tradicional (não é pill) com rótulo rico — aceita texto com link no meio, ex.: aceite de termos",
      },
      {
        nome: "InputMoeda / InputQuantidade / InputPercentual",
        status: "pronto",
        arquivo: "components/v2/InputMoeda/, .../InputQuantidade/, .../InputPercentual/",
      },
      {
        nome: "InputTelefone / InputCpfCnpj",
        status: "pronto",
        arquivo: "components/v2/InputTelefone/, .../InputCpfCnpj/",
        descricao:
          "InputTelefone serve celular e fixo via prop tipo (celular/fixo/ambos) e já traz o toggle de WhatsApp embutido; CNPJ já aceita o formato alfanumérico da Receita Federal (2026)",
      },
      {
        nome: "InputCombobox",
        status: "pronto",
        arquivo: "components/v2/InputCombobox/InputCombobox.jsx",
        descricao: "Busca, teclado, limpar seleção, ghost selection (Tab confirma)",
      },
      {
        nome: "InputComboboxMultiplo",
        status: "pronto",
        arquivo: "components/v2/InputComboboxMultiplo/InputComboboxMultiplo.jsx",
        descricao:
          "Mesma busca, seleção em chips removíveis, ghost selection com Tab mantendo foco",
      },
    ],
  },
  {
    categoria: "Botões",
    origem: "item 1.7 do roadmap",
    itens: [
      {
        nome: "BotaoBase",
        status: "pronto",
        arquivo: "components/v2/BotaoBase/BotaoBase.jsx",
        descricao:
          "Casca interna (não usar direto numa tela) — define os 3 tamanhos (pequeno/normal/grande) e a prop larguraTotal, herdados por todo Botao*",
      },
      { nome: "BotaoSalva", status: "pronto", arquivo: "components/v2/BotaoSalva/BotaoSalva.jsx" },
      {
        nome: "BotaoCancelar",
        status: "pronto",
        arquivo: "components/v2/BotaoCancelar/BotaoCancelar.jsx",
      },
      {
        nome: "BotaoExcluir",
        status: "pronto",
        arquivo: "components/v2/BotaoExcluir/BotaoExcluir.jsx",
        descricao: "Já confirma via corepetDialog antes de agir",
      },
      {
        nome: "BotaoAjuda",
        status: "pronto",
        arquivo: "components/v2/BotaoAjuda/BotaoAjuda.jsx",
        descricao:
          "Sempre só ícone — texto/aria-label obrigatório por design (prop com valor padrão, nunca fica sem)",
      },
      {
        nome: "BotaoInteracao",
        status: "pronto",
        arquivo: "components/v2/BotaoInteracao/BotaoInteracao.jsx",
        descricao:
          'Ação genérica com ícone livre — usado também para ações primárias fora do padrão salvar/cancelar/excluir (ex.: "Entrar" no login)',
      },
      {
        nome: "BotaoLink",
        status: "pronto",
        arquivo: "components/v2/BotaoLink/BotaoLink.jsx",
        descricao: 'Link de navegação secundário dentro de um painel (ex.: "Ver produtos")',
      },
      {
        nome: "LinkPadrao",
        status: "pronto",
        arquivo: "components/v2/LinkPadrao/LinkPadrao.jsx",
        descricao:
          "Link de navegação real (rota interna via `to` ou URL via `href`) — cor, peso e ícone padronizados; só o tamanho da fonte é livre. `novaJanela` abre em outra aba com ícone de link externo",
      },
    ],
  },
  {
    categoria: "Cartões e navegação",
    origem: "limpeza da tela /dashboard (RefatoracaoV2)",
    itens: [
      {
        nome: "CartaoIndicador",
        status: "pronto",
        arquivo: "components/v2/CartaoIndicador/CartaoIndicador.jsx",
        descricao:
          'Substitui MetricCard/CompactMetricCard/PriorityCard do dashboard financeiro — tom (mesmo vocabulário de BotaoBase.variante) colore o ícone, "aoClicar" decide se vira botão ou div estática',
      },
      {
        nome: "EstadoVazio",
        status: "pronto",
        arquivo: "components/v2/EstadoVazio/EstadoVazio.jsx",
        descricao: "Placeholder para painéis sem dado no período (gráfico vazio, lista vazia etc.)",
      },
      {
        nome: "SeletorOpcoes",
        status: "pronto",
        arquivo: "components/v2/SeletorOpcoes/SeletorOpcoes.jsx",
        descricao:
          "Grupo de opções únicas em formato de pill para barra de ferramentas (filtro de período, alternância de visão) — não é campo de formulário",
      },
      {
        nome: "AbasNavegacao",
        status: "pronto",
        arquivo: "components/v2/AbasNavegacao/AbasNavegacao.jsx",
        descricao:
          "Abas horizontais com ícone (estilo GitHub) — cada aba aceita `descricao` (vira dica ao passar o mouse) e `invalida` (mostra ícone de alerta ao lado do rótulo, para sinalizar campo obrigatório pendente naquela aba)",
      },
    ],
  },
  {
    categoria: "Tipografia",
    origem: "item 1.7 do roadmap",
    itens: [
      {
        nome: "v2-titulo-pagina",
        status: "pronto",
        arquivo: "styles/v2-tipografia.css",
        descricao: "Título de página (era planejado como componente Title — virou classe)",
      },
      {
        nome: "v2-titulo-secao",
        status: "pronto",
        arquivo: "styles/v2-tipografia.css",
        descricao: "Título de bloco/seção (era planejado como componente SectionTitle)",
      },
      {
        nome: "v2-subtitulo",
        status: "pronto",
        arquivo: "styles/v2-tipografia.css",
        descricao: "Linha de apoio abaixo de um título (era planejado como componente Subtitle)",
      },
      {
        nome: "v2-texto",
        status: "pronto",
        arquivo: "styles/v2-tipografia.css",
        descricao: "Parágrafo padrão (era planejado como componente Text)",
      },
      {
        nome: "v2-texto-ajuda",
        status: "pronto",
        arquivo: "styles/v2-tipografia.css",
        descricao: "Texto de ajuda pequeno (era planejado como componente HelpText)",
      },
      {
        nome: "v2-rotulo",
        status: "pronto",
        arquivo: "styles/v2-tipografia.css",
        descricao:
          "Rótulo pequeno em caixa alta — não estava no plano original, apareceu duplicado em CartaoIndicador/SeletorOpcoes e virou classe por isso",
      },
      {
        nome: "v2-menu-secao",
        status: "pronto",
        arquivo: "styles/v2-tipografia.css",
        descricao: "Divisor de seção do menu lateral (SidebarMenu)",
      },
      {
        nome: "v2-menu-item",
        status: "pronto",
        arquivo: "styles/v2-tipografia.css",
        descricao:
          "Label de item do menu lateral (SidebarMenu, menu do usuário) — sem cor própria, o container decide a cor conforme ativo/inativo",
      },
    ],
  },
  {
    categoria: "Modal",
    origem: "item 1.7 do roadmap",
    itens: [
      {
        nome: "ModalPadrao",
        status: "pronto",
        arquivo: "components/v2/ModalPadrao/ModalPadrao.jsx",
        descricao:
          "Casca padrão de modal — título, corpo (children) e rodapé de ações (prop rodape); fechar sempre pelo X no mesmo lugar, nunca clicando fora.",
      },
    ],
  },
];

export function contarPorStatus() {
  const contagem = { pronto: 0, planejado: 0 };
  styleGuideCatalog.forEach((grupo) => {
    grupo.itens.forEach((item) => {
      contagem[item.status] = (contagem[item.status] || 0) + 1;
    });
  });
  return contagem;
}

export function totalDeItens() {
  return styleGuideCatalog.reduce((total, grupo) => total + grupo.itens.length, 0);
}
