export function coordenadasDaRota(rota) {
  if (
    rota?.lat_atual === null ||
    rota?.lat_atual === undefined ||
    rota?.lat_atual === "" ||
    rota?.lon_atual === null ||
    rota?.lon_atual === undefined ||
    rota?.lon_atual === ""
  ) {
    return null;
  }
  const latitude = Number(rota?.lat_atual);
  const longitude = Number(rota?.lon_atual);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) return null;
  return { latitude, longitude };
}

export function obterEstadoSinal(rota, agoraMs = Date.now()) {
  if (!coordenadasDaRota(rota) || !rota?.localizacao_atualizada_em) {
    return { key: "sem_sinal", label: "Sem sinal", cor: "#64748b", idadeSegundos: null };
  }

  const atualizadoEm = new Date(rota.localizacao_atualizada_em).getTime();
  if (!Number.isFinite(atualizadoEm)) {
    return { key: "sem_sinal", label: "Sem sinal", cor: "#64748b", idadeSegundos: null };
  }

  const idadeSegundos = Math.max(0, Math.floor((agoraMs - atualizadoEm) / 1000));
  if (idadeSegundos <= 30) {
    return { key: "ao_vivo", label: "Ao vivo", cor: "#16a34a", idadeSegundos };
  }
  if (idadeSegundos <= 120) {
    return { key: "atrasado", label: "Sinal atrasado", cor: "#d97706", idadeSegundos };
  }
  return { key: "offline", label: "Offline", cor: "#dc2626", idadeSegundos };
}

export function formatarIdadeSinal(estado) {
  if (estado.idadeSegundos == null) return "Nenhuma posição recebida";
  if (estado.idadeSegundos < 60) return `há ${estado.idadeSegundos}s`;
  const minutos = Math.floor(estado.idadeSegundos / 60);
  return `há ${minutos} min`;
}

export function adicionarPontoTrilha(trilhaAtual = [], coordenadas, limite = 80) {
  if (!coordenadas) return trilhaAtual;
  const ultimo = trilhaAtual[trilhaAtual.length - 1];
  if (
    ultimo &&
    ultimo.latitude === coordenadas.latitude &&
    ultimo.longitude === coordenadas.longitude
  ) {
    return trilhaAtual;
  }
  return [...trilhaAtual, coordenadas].slice(-limite);
}

export function gerarPontosSimulacao(origem) {
  const latitude = Number(origem?.latitude);
  const longitude = Number(origem?.longitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return [];

  const deslocamentos = [
    [0, 0],
    [0.00018, 0.00012],
    [0.00035, 0.00032],
    [0.00048, 0.00058],
    [0.00042, 0.00088],
    [0.0002, 0.00112],
    [-0.00005, 0.00128],
    [-0.0003, 0.00118],
    [-0.00052, 0.00092],
    [-0.0006, 0.00058],
    [-0.00048, 0.00025],
    [-0.00025, 0.00005],
  ];

  return deslocamentos.map(([deltaLat, deltaLon]) => ({
    latitude: Number((latitude + deltaLat).toFixed(6)),
    longitude: Number((longitude + deltaLon).toFixed(6)),
  }));
}

export function simuladorRastreioHabilitado(env = {}) {
  const ambiente = String(env.VITE_APP_ENV || env.MODE || "").toLowerCase();
  if (["production", "producao", "prod"].includes(ambiente)) return false;
  return env.DEV === true || env.VITE_ENABLE_DELIVERY_SIMULATOR === "true";
}
