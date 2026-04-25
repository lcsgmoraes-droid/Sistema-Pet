export const STATUS_CORES = {
  internado: "bg-blue-100 text-blue-700",
  ativa: "bg-blue-100 text-blue-700",
  alta: "bg-green-100 text-green-700",
  transferida: "bg-yellow-100 text-yellow-700",
  obito: "bg-red-100 text-red-700",
};

export function formatData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function parseQuantity(value) {
  if (value == null || value === "") return null;
  const parsed = Number(String(value).replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatQuantity(value, unidade = "") {
  if (value == null || value === "" || Number.isNaN(Number(value))) return "—";
  const numero = Number(value);
  const texto = Number.isInteger(numero)
    ? numero.toLocaleString("pt-BR")
    : numero.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  return unidade ? `${texto} ${unidade}` : texto;
}

export function montarSerieEvolucao(registros = []) {
  return registros
    .filter((item) => item?.data_hora)
    .map((item) => ({
      horario: new Date(item.data_hora).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }),
      temperatura: item.temperatura ?? null,
      fc: item.freq_cardiaca ?? null,
      fr: item.freq_respiratoria ?? null,
      peso: item.peso ?? null,
    }));
}
