export const HEAVY_REQUEST_TIMEOUT_MS = 60000;
export const SNAPSHOT_LIMIT = 200;
export const MASS_LINK_BATCH_SIZE = 20;
export const MASS_LINK_MAX_BATCHES = 5;
export const SYNC_PROBLEMS_LIMIT = 300;

export const EMPTY_COBERTURA = {
  total_bling: 0,
  bling_com_match_no_sistema: 0,
  bling_sem_match_no_sistema: 0,
  bling_sync_ok: 0,
  bling_com_problema: 0,
  atualizado_em: null,
  cache_idade_segundos: 0,
  snapshot_disponivel: false,
  precisa_atualizar: true,
};

export const EMPTY_FALTANTES_META = {
  total: 0,
  snapshotDisponivel: false,
  coletaCompleta: true,
  atualizadoEm: null,
  cacheIdadeSegundos: 0,
  precisaAtualizar: true,
};

export const EMPTY_VINCULOS_META = {
  total: 0,
  snapshotDisponivel: false,
  atualizadoEm: null,
  cacheIdadeSegundos: 0,
  coletaCompleta: true,
  precisaAtualizar: true,
};

export const EMPTY_LOCAL_META = {
  total: 0,
  loaded: false,
  atualizadoEm: null,
};

export const EMPTY_BLING_CONNECTION = {
  checked: false,
  connected: null,
  message: "",
  detail: "",
};

export const TAB_CONFIG = {
  criar: {
    label: "Bling sem CorePet",
    emptyTitle: "Nenhum item do Bling sem cadastro local",
    emptyDescription:
      "Todo produto do Bling encontrado nesta leitura ja tem cadastro correspondente no CorePet.",
  },
  vincular: {
    label: "SKU igual",
    emptyTitle: "Nenhuma sugestao por SKU igual",
    emptyDescription:
      "Quando o mesmo SKU existir no CorePet e no Bling sem vinculo salvo, ele aparece aqui.",
  },
  local: {
    label: "Local sem Bling",
    emptyTitle: "Nenhum produto local sem vinculo",
    emptyDescription:
      "Produtos vendidos apenas na loja fisica podem ficar fora do Bling sem virar pendencia.",
  },
  corrigir: {
    label: "Falhas de sync",
    emptyTitle: "Nenhuma falha de sincronizacao aberta",
    emptyDescription:
      "Produtos vinculados com divergencia, fila travada ou erro aparecem nesta fila.",
  },
};

export const ISSUE_TONES = {
  red: {
    panel: "border-red-200 bg-red-50 text-red-700",
    badge: "bg-red-100 text-red-700",
    button: "bg-red-600 text-white hover:bg-red-700",
  },
  amber: {
    panel: "border-amber-200 bg-amber-50 text-amber-800",
    badge: "bg-amber-100 text-amber-700",
    button: "bg-amber-500 text-white hover:bg-amber-600",
  },
  sky: {
    panel: "border-sky-200 bg-sky-50 text-sky-800",
    badge: "bg-sky-100 text-sky-700",
    button: "bg-sky-600 text-white hover:bg-sky-700",
  },
  slate: {
    panel: "border-slate-200 bg-slate-50 text-slate-700",
    badge: "bg-slate-100 text-slate-700",
    button: "bg-slate-700 text-white hover:bg-slate-800",
  },
  emerald: {
    panel: "border-emerald-200 bg-emerald-50 text-emerald-700",
    badge: "bg-emerald-100 text-emerald-700",
    button: "bg-emerald-600 text-white hover:bg-emerald-700",
  },
};
