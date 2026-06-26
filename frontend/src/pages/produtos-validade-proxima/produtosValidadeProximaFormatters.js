export const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(valor || 0));

export function getStatusBadge(status) {
  const mapa = {
    vencido: {
      label: "Vencido",
      className: "bg-rose-100 text-rose-700 border border-rose-200",
    },
    urgente: {
      label: "Janela 7 dias",
      className: "bg-orange-100 text-orange-700 border border-orange-200",
    },
    alerta_30: {
      label: "Janela 30 dias",
      className: "bg-amber-100 text-amber-700 border border-amber-200",
    },
    alerta_60: {
      label: "Janela 60 dias",
      className: "bg-blue-100 text-blue-700 border border-blue-200",
    },
    monitorar: {
      label: "Monitorar",
      className: "bg-slate-100 text-slate-700 border border-slate-200",
    },
  };

  return (
    mapa[status] || {
      label: "Sem regra",
      className: "bg-slate-100 text-slate-700 border border-slate-200",
    }
  );
}

export function getDiasRestantesVisual(diasParaVencer) {
  const dias = Number(diasParaVencer ?? 0);

  if (dias < 0) {
    const total = Math.abs(dias);
    return {
      destaque: `${total} dia${total === 1 ? "" : "s"}`,
      apoio: "em atraso",
      className: "text-rose-700",
      surfaceClassName: "border-rose-200 bg-rose-50",
    };
  }

  if (dias === 0) {
    return {
      destaque: "Hoje",
      apoio: "vence hoje",
      className: "text-orange-700",
      surfaceClassName: "border-orange-200 bg-orange-50",
    };
  }

  return {
    destaque: `${dias} dia${dias === 1 ? "" : "s"}`,
    apoio: "para vencer",
    className: dias <= 7 ? "text-orange-700" : dias <= 30 ? "text-amber-700" : "text-blue-700",
    surfaceClassName:
      dias <= 7
        ? "border-orange-200 bg-orange-50"
        : dias <= 30
          ? "border-amber-200 bg-amber-50"
          : "border-blue-200 bg-blue-50",
  };
}

export function getFaixaCampanhaBadge(faixa) {
  const mapa = {
    vencido: {
      label: "Acao imediata",
      className: "bg-rose-100 text-rose-700 border border-rose-200",
    },
    "7_dias": {
      label: "Campanha 7 dias",
      className: "bg-orange-100 text-orange-700 border border-orange-200",
    },
    "30_dias": {
      label: "Campanha 30 dias",
      className: "bg-amber-100 text-amber-700 border border-amber-200",
    },
    "60_dias": {
      label: "Campanha 60 dias",
      className: "bg-emerald-100 text-emerald-700 border border-emerald-200",
    },
  };

  return (
    mapa[faixa] || {
      label: "Sem campanha sugerida",
      className: "bg-slate-100 text-slate-600 border border-slate-200",
    }
  );
}

export function normalizarValorCsv(valor) {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "number") return String(valor).replace(".", ",");
  return String(valor).replaceAll('"', '""');
}
