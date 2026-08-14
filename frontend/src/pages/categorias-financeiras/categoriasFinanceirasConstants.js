export const ICON_FALLBACK = "•";

export const DEFAULT_CATEGORIA_FORM = Object.freeze({
  nome: "",
  tipo: "despesa",
  cor: "#6366f1",
  icone: ICON_FALLBACK,
  descricao: "",
  ativo: true,
  tipo_custo: null,
  novasSubcategorias: [],
});

export const DEFAULT_SUBCATEGORIA_FORM = Object.freeze({
  categoria_id: null,
  nome: "",
  descricao: "",
  ativo: true,
});

export const CATEGORY_ICONS = [ICON_FALLBACK, "$", "#", "@", "+", "*"];

export const CATEGORY_COLORS = [
  "#ef4444",
  "#f97316",
  "#f59e0b",
  "#84cc16",
  "#10b981",
  "#14b8a6",
  "#06b6d4",
  "#0ea5e9",
  "#3b82f6",
  "#6366f1",
  "#8b5cf6",
  "#a855f7",
  "#d946ef",
  "#ec4899",
];

export const COST_CLASSIFICATION_OPTIONS = [
  {
    value: "fixo",
    label: "🔒 Fixo",
    desc: "Valor fixo todo mês",
    activeClass: "bg-orange-500 text-white border-orange-500",
  },
  {
    value: "variavel",
    label: "📈 Variável",
    desc: "Varia com as vendas",
    activeClass: "bg-blue-500 text-white border-blue-500",
  },
  {
    value: "ambos",
    label: "↕ Ambos",
    desc: "Cada subcategoria define",
    activeClass: "bg-purple-500 text-white border-purple-500",
  },
];

export const MOJIBAKE_REPLACEMENTS = {
  "Ã¡": "á",
  "Ã¢": "â",
  "Ã£": "ã",
  Ãª: "ê",
  "Ã©": "é",
  "Ã­": "í",
  "Ã³": "ó",
  "Ã´": "ô",
  Ãµ: "õ",
  Ãº: "ú",
  "Ã§": "ç",
  "Ã": "Á",
  "Ã‰": "É",
  "Ã“": "Ó",
  Ãš: "Ú",
  "Ã‡": "Ç",
  "â€“": "-",
  "â€”": "-",
  "â€˜": "'",
  "â€™": "'",
  "â€œ": '"',
  "â€": '"',
};

export const QUESTION_MARK_WORD_FIXES = [
  [/sal\?+rio/gi, "salário"],
  [/r\?+gua/gi, "régua"],
  [/\?+gua/gi, "água"],
  [/veterin\?+rias/gi, "veterinárias"],
  [/consultas\s+veterin\?+rias/gi, "Consultas Veterinárias"],
  [/f\?+rias/gi, "férias"],
  [/manuten\?+o/gi, "manutenção"],
  [/escrit\?+rio/gi, "escritório"],
  [/el\?+trica/gi, "elétrica"],
  [/servi\?+os/gi, "serviços"],
  [/ter\?+o/gi, "terço"],
  [/13\?+/gi, "13º"],
  [/alimenta\?+o/gi, "alimentação"],
  [/provis\?+o/gi, "provisão"],
  [/descri\?+o/gi, "descrição"],
  [/n\?mero/gi, "número"],
  [/F\?+sica/g, "Física"],
  [/f\?+sica/gi, "física"],
  [/Padr\?+o/g, "Padrão"],
  [/padr\?+o/gi, "padrão"],
  [/Espa\?+o/g, "Espaço"],
  [/espa\?+o/gi, "espaço"],
  [/Di\?+rias/g, "Diárias"],
  [/Di\?+ria/g, "Diária"],
  [/di\?+ria/gi, "diária"],
  [/Vacina\?+o/g, "Vacinação"],
  [/vacina\?+o/gi, "vacinação"],
  [/Participa\?+o/g, "Participação"],
  [/participa\?+o/gi, "participação"],
  [/Ra\?+es/g, "Rações"],
  [/ra\?+es/gi, "rações"],
  [/Redu\?+o/g, "Redução"],
  [/redu\?+o/gi, "redução"],
  [/Cr\?+dito/g, "Crédito"],
  [/cr\?+dito/gi, "crédito"],
];
