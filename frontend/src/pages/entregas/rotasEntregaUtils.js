export function calcularTempoEstimado(rota) {
  if (!rota.paradas || rota.paradas.length === 0) return null;
  const ultimaParada = rota.paradas[rota.paradas.length - 1];
  if (ultimaParada.tempo_acumulado) {
    return ultimaParada.tempo_acumulado;
  }
  return null;
}

export function formatarTempo(segundos) {
  if (!segundos) return "N/A";
  const minutos = Math.floor(segundos / 60);
  const horas = Math.floor(minutos / 60);
  const mins = minutos % 60;
  if (horas > 0) {
    return `${horas}h${mins}min`;
  }
  return `${mins}min`;
}

export function getStatusColor(status) {
  switch (status) {
    case "pendente":
      return "#FFA500";
    case "em_andamento":
      return "#007BFF";
    case "em_rota":
      return "#007BFF";
    case "concluida":
      return "#28A745";
    case "cancelada":
      return "#DC3545";
    default:
      return "#6C757D";
  }
}

export function getStatusLabel(status) {
  switch (status) {
    case "pendente":
      return "🟠 Pendente";
    case "em_andamento":
      return "🔵 Em Andamento";
    case "em_rota":
      return "🔵 Em Rota";
    case "concluida":
      return "✅ Concluída";
    case "cancelada":
      return "❌ Cancelada";
    default:
      return status;
  }
}

export function filtrarRotasEmAndamento(rotas = []) {
  if (!Array.isArray(rotas)) return [];
  return rotas.filter((rota) => rota.status === "em_rota" || rota.status === "em_andamento");
}

export function agruparRotasPorEntregador(rotas = []) {
  return (rotas || []).reduce((acc, rota) => {
    const chave = rota?.entregador?.id || `sem-id-${rota.id}`;
    if (!acc[chave]) {
      acc[chave] = {
        entregadorNome: rota?.entregador?.nome || "Entregador não informado",
        rotas: [],
      };
    }
    acc[chave].rotas.push(rota);
    return acc;
  }, {});
}

export function formatarHorarioLocalizacao(dataIso) {
  if (!dataIso) return "Sem atualização";
  const data = new Date(dataIso);
  if (Number.isNaN(data.getTime())) return "Sem atualização";
  return data.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function getUltimaParadaPendente(rota) {
  if (!Array.isArray(rota?.paradas)) return null;
  return (
    rota.paradas.find((parada) => parada.status !== "entregue") ||
    rota.paradas[rota.paradas.length - 1] ||
    null
  );
}

export function montarDestinoMapaRota(rota) {
  if (rota?.token_rastreio) {
    return {
      url: `/rastreio/${encodeURIComponent(rota.token_rastreio)}`,
      tipo: "rastreio",
    };
  }

  const lat = rota?.lat_atual;
  const lon = rota?.lon_atual;
  if (lat && lon) {
    return {
      url: `https://www.google.com/maps?q=${lat},${lon}`,
      tipo: "coordenadas",
    };
  }

  const ultimaParada = getUltimaParadaPendente(rota);
  const endereco = ultimaParada?.endereco || rota?.endereco_destino;
  if (endereco) {
    return {
      url: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(endereco)}`,
      tipo: "endereco",
    };
  }

  return null;
}
