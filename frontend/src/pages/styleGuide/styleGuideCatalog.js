export const STYLEGUIDE_STATUS = {
  pronto: { label: "Pronto", intent: "success" },
  legado: { label: "Existe (legado)", intent: "warning" },
  planejado: { label: "Planejado", intent: "neutral" },
};

export const styleGuideCatalog = [
  {
    categoria: "Componentes v2 (fonte única, em components/v2/)",
    origem: "itens 1.6/1.7 do roadmap — sem prop de cor/tamanho, base + especialização",
    itens: [
      {
        nome: "InputTexto",
        status: "pronto",
        arquivo: "components/v2/InputTexto/InputTexto.jsx",
        descricao: "Base de todos os campos de texto",
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
        descricao: "Compõe dois InputData (cada lado com seu próprio calendário)",
      },
      {
        nome: "CalendarioPainel",
        status: "pronto",
        arquivo: "components/v2/CalendarioPainel/CalendarioPainel.jsx",
        descricao:
          "Grade de mês reaproveitada por InputData/InputDataHora — não usar direto numa tela",
      },
      {
        nome: "InputCheck / InputRadio",
        status: "pronto",
        arquivo: "components/v2/InputCheck/, components/v2/InputRadio/",
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
        descricao: "CNPJ já aceita o formato alfanumérico da Receita Federal (2026)",
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
        descricao: "Mesma busca, seleção em chips removíveis",
      },
      {
        nome: "BotaoBase",
        status: "pronto",
        arquivo: "components/v2/BotaoBase/BotaoBase.jsx",
        descricao: "Casca interna — não usar direto numa tela",
      },
      {
        nome: "BotaoSalva / BotaoCancelar / BotaoExcluir",
        status: "pronto",
        arquivo: "components/v2/BotaoSalva/, .../BotaoCancelar/, .../BotaoExcluir/",
        descricao: "BotaoExcluir já confirma via corepetDialog antes de agir",
      },
      {
        nome: "BotaoAjuda",
        status: "pronto",
        arquivo: "components/v2/BotaoAjuda/BotaoAjuda.jsx",
        descricao: "Sempre só ícone",
      },
      {
        nome: "BotaoInteracao",
        status: "pronto",
        arquivo: "components/v2/BotaoInteracao/BotaoInteracao.jsx",
        descricao: "Ação secundária genérica (avançar/voltar/ver detalhes)",
      },
    ],
  },
  {
    categoria: "Tipografia",
    origem: "item 1.7 do roadmap",
    itens: [
      {
        nome: "Title",
        status: "planejado",
        descricao: "Título de página (o que hoje é o <h1> solto em PageHeader.jsx)",
      },
      {
        nome: "SectionTitle",
        status: "planejado",
        descricao: "Título de bloco/card (o que hoje é o <h2> solto em Panel.jsx)",
      },
      {
        nome: "Subtitle",
        status: "planejado",
        descricao: "Linha de apoio abaixo do título (o <p> solto em PageHeader.jsx)",
      },
      { nome: "Text", status: "planejado", descricao: "Parágrafo padrão, com variação de tom" },
      {
        nome: "HelpText",
        status: "legado",
        arquivo: "components/ui/FormField.jsx",
        descricao: "Hoje só existe embutido no FormField, só para campos",
      },
    ],
  },
  {
    categoria: "Botões",
    origem: "item 1.7 do roadmap",
    itens: [
      {
        nome: "ActionButton",
        status: "pronto",
        arquivo: "components/ui/ActionButton.jsx",
        descricao: "Base: ícone + texto",
      },
      {
        nome: "IconActionButton",
        status: "pronto",
        arquivo: "components/ui/IconActionButton.jsx",
        descricao: "Base: só ícone",
      },
      { nome: "SaveButton", status: "planejado", descricao: "Catálogo por ação — salvar/gravar" },
      { nome: "CancelButton", status: "planejado", descricao: "Catálogo por ação — cancelar" },
      { nome: "DeleteButton", status: "planejado", descricao: "Catálogo por ação — excluir" },
      {
        nome: "HelpButton",
        status: "planejado",
        descricao: "Catálogo por ação — ajuda (hoje remontado à mão em PageHeader.jsx)",
      },
      {
        nome: "SubmenuToggleButton",
        status: "planejado",
        descricao: "Catálogo por ação — abrir/fechar submenu",
      },
    ],
  },
  {
    categoria: "Campos de formulário",
    origem: "item 1.6 do roadmap",
    itens: [
      {
        nome: "TextField / SelectField / CheckboxField",
        status: "legado",
        arquivo: "components/ui/FormField.jsx",
        descricao: "Já tem label/erro/help, ainda não é base de nada mais específico",
      },
      {
        nome: "MoneyField",
        status: "legado",
        arquivo: "components/CurrencyInput.jsx",
        descricao: "Existe como CurrencyInput, isolado, sem label/erro padronizado",
      },
      {
        nome: "QuantityField",
        status: "legado",
        arquivo: "components/QuantidadeInput.jsx",
        descricao: "Existe como QuantidadeInput, mesma limitação",
      },
      {
        nome: "ComboboxField",
        status: "legado",
        arquivo: "components/ui/AutocompleteSelect.jsx",
        descricao: "O mais completo dos existentes, fora da família FormField",
      },
      {
        nome: "DateField",
        status: "legado",
        arquivo: "pages/veterinario/agenda/AgendaDateInputField.jsx",
        descricao: "Só funciona local, na agenda do veterinário",
      },
      {
        nome: "PercentField",
        status: "planejado",
        descricao: "Percentual — telas de margem/comissão",
      },
      { nome: "CpfCnpjField", status: "planejado", descricao: "Detecta CPF vs CNPJ pelo tamanho" },
      { nome: "PhoneField", status: "planejado" },
      { nome: "RadioGroupField", status: "planejado" },
      { nome: "PasswordField", status: "planejado", descricao: "Com alternância mostrar/ocultar" },
    ],
  },
  {
    categoria: "Modais",
    origem: "item 1.7 do roadmap",
    itens: [
      {
        nome: "CorePetDialogHost (confirmar / perguntar)",
        status: "pronto",
        arquivo: "components/ui/CorePetDialogHost.jsx",
        descricao: "Substitui window.confirm/window.prompt, já com role=dialog e Escape",
      },
      {
        nome: "Modal / Modal.Header / Modal.Body / Modal.Footer",
        status: "planejado",
        descricao: "Casca genérica para conteúdo arbitrário (formulário, wizard)",
      },
    ],
  },
  {
    categoria: "Estados de tela",
    origem: "já existiam, sem regra escrita até o item 1.8",
    itens: [
      { nome: "EmptyState", status: "pronto", arquivo: "components/ui/EmptyState.jsx" },
      { nome: "LoadingState", status: "pronto", arquivo: "components/ui/LoadingState.jsx" },
      { nome: "ErrorState", status: "pronto", arquivo: "components/ui/ErrorState.jsx" },
      { nome: "TextSkeleton e afins", status: "pronto", arquivo: "components/Skeletons.jsx" },
    ],
  },
  {
    categoria: "Blocos de layout",
    origem: "já existiam, sem regra escrita até o item 1.8",
    itens: [
      { nome: "Panel", status: "pronto", arquivo: "components/ui/Panel.jsx" },
      { nome: "PageHeader", status: "pronto", arquivo: "components/ui/PageHeader.jsx" },
      {
        nome: "MetricCard / MetricGrid",
        status: "pronto",
        arquivo: "components/ui/MetricCard.jsx",
      },
      { nome: "StatusBadge", status: "pronto", arquivo: "components/ui/StatusBadge.jsx" },
      { nome: "SegmentedControl", status: "pronto", arquivo: "components/ui/SegmentedControl.jsx" },
    ],
  },
];

export function contarPorStatus() {
  const contagem = { pronto: 0, legado: 0, planejado: 0 };
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
