import { formatNumber } from "../estoqueBlingUtils";
import { EMPTY_COBERTURA, EMPTY_FALTANTES_META, EMPTY_VINCULOS_META } from "./estoqueBlingConfig";

export function normalizarResumoBling(data = {}) {
  return {
    ...EMPTY_COBERTURA,
    ...data,
    snapshot_disponivel: Boolean(data.snapshot_disponivel),
    precisa_atualizar: Boolean(data.precisa_atualizar),
  };
}

export function normalizarFaltantesBling(data = {}) {
  return {
    items: data.items || [],
    meta: {
      ...EMPTY_FALTANTES_META,
      total: Number(data.total || 0),
      snapshotDisponivel: Boolean(data.snapshot_disponivel),
      coletaCompleta: Boolean(data.coleta_bling_completa ?? true),
      atualizadoEm: data.atualizado_em || null,
      cacheIdadeSegundos: Number(data.cache_idade_segundos || 0),
      precisaAtualizar: Boolean(data.precisa_atualizar),
    },
  };
}

export function normalizarVinculosBling(data = {}) {
  return {
    items: data.items || [],
    meta: {
      ...EMPTY_VINCULOS_META,
      total: Number(data.total || 0),
      snapshotDisponivel: Boolean(data.snapshot_disponivel),
      atualizadoEm: data.atualizado_em || null,
      cacheIdadeSegundos: Number(data.cache_idade_segundos || 0),
      coletaCompleta: Boolean(data.coleta_bling_completa ?? true),
      precisaAtualizar: Boolean(data.precisa_atualizar),
    },
  };
}

export function normalizarProdutosLocaisSemBling(data = {}) {
  return {
    items: data.items || [],
    meta: {
      total: Number(data.total || 0),
      loaded: true,
      atualizadoEm: new Date().toISOString(),
    },
  };
}

export function montarResumoSaudeBling({
  hasAnySnapshot,
  faltantesMeta,
  vinculosMeta,
  syncLoaded,
  cobertura,
  syncProblemCount,
}) {
  const knownPendingCount = hasAnySnapshot
    ? Number(faltantesMeta.snapshotDisponivel ? faltantesMeta.total || 0 : 0) +
      Number(vinculosMeta.snapshotDisponivel ? vinculosMeta.total || 0 : 0) +
      Number(syncLoaded || cobertura.snapshot_disponivel ? syncProblemCount : 0)
    : null;
  const healthBaseTotal = Math.max(
    Number(cobertura.total_bling || 0),
    Number(knownPendingCount || 0),
    1,
  );
  const healthPercent =
    knownPendingCount === null
      ? 0
      : knownPendingCount <= 0
        ? 100
        : Math.max(
            0,
            Math.min(
              100,
              Math.round(((healthBaseTotal - knownPendingCount) / healthBaseTotal) * 100),
            ),
          );
  const healthTone =
    knownPendingCount === null
      ? "slate"
      : knownPendingCount === 0
        ? "emerald"
        : knownPendingCount <= 20
          ? "amber"
          : "red";
  const healthDetail =
    knownPendingCount === null
      ? "Sem leitura valida ainda. Ao atualizar, a central deve mostrar o termometro e as pendencias abertas."
      : knownPendingCount === 0
        ? "Sem pendencias nesta leitura. O catalogo atual ficou coberto e sem fila aberta."
        : `${formatNumber(knownPendingCount)} pendencia(s) aberta(s) nesta leitura. A central ja mostra o recorte que pede acao.`;

  return { healthPercent, healthTone, healthDetail, knownPendingCount };
}
