export const FORM_VACINA_INICIAL = {
  pessoa_id: "",
  pet_id: "",
  nome_vacina: "",
  fabricante: "",
  lote: "",
  data_aplicacao: "",
  proxima_dose: "",
  veterinario_id: "",
  observacoes: "",
};

export function criarFormVacinaInicial(overrides = {}) {
  return {
    ...FORM_VACINA_INICIAL,
    ...overrides,
  };
}

export function normalizarVacinas(data) {
  const itens = Array.isArray(data) ? data : (data?.items ?? []);

  return itens.map((vacina) => ({
    ...vacina,
    proxima_dose: vacina.proxima_dose ?? vacina.data_proxima_dose ?? null,
  }));
}

export function adicionarDias(dataIso, dias) {
  if (!dataIso || !dias) return "";
  const data = dataLocal(dataIso);
  if (!data) return "";
  data.setDate(data.getDate() + Number(dias));
  return [
    data.getFullYear(),
    String(data.getMonth() + 1).padStart(2, "0"),
    String(data.getDate()).padStart(2, "0"),
  ].join("-");
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
      !especie || !especiePet || especiePet.includes(especie) || especie.includes(especiePet);
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
  const data = dataLocal(iso);
  if (!data) return "-";
  return data.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function diasRestantes(iso) {
  if (!iso) return null;
  const data = dataLocal(iso);
  if (!data) return null;
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  return Math.round((data - hoje) / 86400000);
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

function dataLocal(iso) {
  const dataIso = String(iso).slice(0, 10);
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dataIso);
  if (!match) return null;
  const data = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(data.getTime()) ? null : data;
}
