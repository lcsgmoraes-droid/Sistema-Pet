export const CONSULTAS_POR_PAGINA = 20;

export const STATUS_LABEL = {
  aberta: "Aberta",
  finalizada: "Finalizada",
  cancelada: "Cancelada",
};

export const STATUS_COLOR = {
  aberta: "bg-blue-100 text-blue-800",
  finalizada: "bg-green-100 text-green-800",
  cancelada: "bg-gray-100 text-gray-500",
};

export function formatDataConsulta(iso) {
  if (!iso) return "-";
  const data = new Date(iso);
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function formatHoraConsulta(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function filtrarConsultas(consultas, busca) {
  if (!busca) return consultas;

  const texto = busca.toLowerCase();
  return consultas.filter((consulta) => (
    String(consulta.id ?? "").includes(texto) ||
    (consulta.pet_nome ?? "").toLowerCase().includes(texto) ||
    (consulta.veterinario_nome ?? "").toLowerCase().includes(texto) ||
    (consulta.motivo_consulta ?? "").toLowerCase().includes(texto) ||
    (consulta.diagnostico ?? "").toLowerCase().includes(texto)
  ));
}
