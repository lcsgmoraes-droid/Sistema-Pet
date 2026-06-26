export const ICON_FALLBACK = "â€¢";

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
    label: "ðŸ”’ Fixo",
    desc: "Valor fixo todo mÃªs",
    activeClass: "bg-orange-500 text-white border-orange-500",
  },
  {
    value: "variavel",
    label: "ðŸ“ˆ VariÃ¡vel",
    desc: "Varia com as vendas",
    activeClass: "bg-blue-500 text-white border-blue-500",
  },
  {
    value: "ambos",
    label: "â†• Ambos",
    desc: "Cada subcategoria define",
    activeClass: "bg-purple-500 text-white border-purple-500",
  },
];

export const MOJIBAKE_REPLACEMENTS = {
  "ÃƒÂ¡": "Ã¡",
  "ÃƒÂ¢": "Ã¢",
  "ÃƒÂ£": "Ã£",
  ÃƒÂª: "Ãª",
  "ÃƒÂ©": "Ã©",
  "ÃƒÂ­": "Ã­",
  "ÃƒÂ³": "Ã³",
  "ÃƒÂ´": "Ã´",
  ÃƒÂµ: "Ãµ",
  ÃƒÂº: "Ãº",
  "ÃƒÂ§": "Ã§",
  "ÃƒÂ": "Ã",
  "Ãƒâ€°": "Ã‰",
  "Ãƒâ€œ": "Ã“",
  "ÃƒÅ¡": "Ãš",
  "Ãƒâ€¡": "Ã‡",
  "Ã¢â‚¬â€œ": "-",
  "Ã¢â‚¬â€": "-",
  "Ã¢â‚¬Ëœ": "'",
  "Ã¢â‚¬â„¢": "'",
  "Ã¢â‚¬Å“": '"',
  "Ã¢â‚¬Â": '"',
};

export const QUESTION_MARK_WORD_FIXES = [
  [/sal\?+rio/gi, "salÃ¡rio"],
  [/r\?+gua/gi, "rÃ©gua"],
  [/\?+gua/gi, "Ã¡gua"],
  [/veterin\?+rias/gi, "veterinÃ¡rias"],
  [/consultas\s+veterin\?+rias/gi, "Consultas VeterinÃ¡rias"],
  [/f\?+rias/gi, "fÃ©rias"],
  [/manuten\?+o/gi, "manutenÃ§Ã£o"],
  [/escrit\?+rio/gi, "escritÃ³rio"],
  [/el\?+trica/gi, "elÃ©trica"],
  [/servi\?+os/gi, "serviÃ§os"],
  [/ter\?+o/gi, "terÃ§o"],
  [/13\?+/gi, "13Âº"],
  [/alimenta\?+o/gi, "alimentaÃ§Ã£o"],
  [/provis\?+o/gi, "provisÃ£o"],
  [/descri\?+o/gi, "descriÃ§Ã£o"],
  [/n\?mero/gi, "nÃºmero"],
  [/F\?+sica/g, "FÃ­sica"],
  [/f\?+sica/gi, "fÃ­sica"],
  [/Padr\?+o/g, "PadrÃ£o"],
  [/padr\?+o/gi, "padrÃ£o"],
  [/Espa\?+o/g, "EspaÃ§o"],
  [/espa\?+o/gi, "espaÃ§o"],
  [/Di\?+rias/g, "DiÃ¡rias"],
  [/Di\?+ria/g, "DiÃ¡ria"],
  [/di\?+ria/gi, "diÃ¡ria"],
  [/Vacina\?+o/g, "VacinaÃ§Ã£o"],
  [/vacina\?+o/gi, "vacinaÃ§Ã£o"],
  [/Participa\?+o/g, "ParticipaÃ§Ã£o"],
  [/participa\?+o/gi, "participaÃ§Ã£o"],
  [/Ra\?+es/g, "RaÃ§Ãµes"],
  [/ra\?+es/gi, "raÃ§Ãµes"],
  [/Redu\?+o/g, "ReduÃ§Ã£o"],
  [/redu\?+o/gi, "reduÃ§Ã£o"],
  [/Cr\?+dito/g, "CrÃ©dito"],
  [/cr\?+dito/gi, "crÃ©dito"],
];
