export const FORM_VACINA_INICIAL = {
  pessoa_id: "",
  pet_id: "",
  nome_vacina: "",
  fabricante: "",
  lote: "",
  data_aplicacao: "",
  proxima_dose: "",
  veterinario_responsavel: "",
  observacoes: "",
};

export function criarFormVacinaInicial(overrides = {}) {
  return {
    ...FORM_VACINA_INICIAL,
    ...overrides,
  };
}

export function normalizarVacinas(data) {
  const itens = Array.isArray(data) ? data : data?.items ?? [];

  return itens.map((vacina) => ({
    ...vacina,
    proxima_dose: vacina.proxima_dose ?? vacina.data_proxima_dose ?? null,
  }));
}

export function adicionarDias(dataIso, dias) {
  if (!dataIso || !dias) return "";
  const data = new Date(`${dataIso}T12:00:00`);
  data.setDate(data.getDate() + Number(dias));
  return data.toISOString().slice(0, 10);
}

export function sugerirProximaDose(protocolos, pets, form) {
  if (!form.pet_id || !form.nome_vacina || !form.data_aplicacao) return null;

  const pet = pets.find((item) => String(item.id) === String(form.pet_id));
  const especiePet = (pet?.especie || "").toLowerCase();
  const nomeVacina = form.nome_vacina.toLowerCase();

  const protocolo = protocolos.find((item) => {
    const nome = (item?.nome || "").toLowerCase();
    const especie = (item?.especie || "").toLowerCase();
    const especieCompativel =
      !especie ||
      !especiePet ||
      especiePet.includes(especie) ||
      especie.includes(especiePet);
    return especieCompativel && (nomeVacina.includes(nome) || nome.includes(nomeVacina));
  });

  if (!protocolo) return null;

  const dias = protocolo.intervalo_doses_dias || (protocolo.reforco_anual ? 365 : null);
  if (!dias) return { protocolo, proximaDose: "" };

  return {
    protocolo,
    proximaDose: adicionarDias(form.data_aplicacao, dias),
  };
}

export function formatData(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function diasRestantes(iso) {
  if (!iso) return null;
  return Math.ceil((new Date(iso) - Date.now()) / 86400000);
}

export function badgeProxDose(iso) {
  if (!iso) return null;
  const dias = diasRestantes(iso);

  if (dias < 0) {
    return { label: `Vencida há ${Math.abs(dias)}d`, cls: "bg-red-100 text-red-700" };
  }

  if (dias <= 7) {
    return { label: dias === 0 ? "Hoje" : `em ${dias}d`, cls: "bg-red-100 text-red-700" };
  }

  if (dias <= 30) {
    return { label: `em ${dias}d`, cls: "bg-yellow-100 text-yellow-700" };
  }

  return { label: `em ${dias}d`, cls: "bg-green-100 text-green-700" };
}

export function classeFaseCalendario(fase) {
  if (fase === "filhote") return "bg-blue-100 text-blue-700";
  if (fase === "adulto") return "bg-green-100 text-green-700";
  return "bg-gray-100 text-gray-600";
}
