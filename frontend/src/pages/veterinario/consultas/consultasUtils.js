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
  return consultas.filter(
    (consulta) =>
      String(consulta.id ?? "").includes(texto) ||
      (consulta.pet_nome ?? "").toLowerCase().includes(texto) ||
      (consulta.veterinario_nome ?? "").toLowerCase().includes(texto) ||
      (consulta.motivo_consulta ?? "").toLowerCase().includes(texto) ||
      (consulta.diagnostico ?? "").toLowerCase().includes(texto),
  );
}

export function toggleConsultaSelecionada(selecionadas, consultaId) {
  const id = Number(consultaId);
  if (!Number.isFinite(id)) return selecionadas;

  if (selecionadas.includes(id)) {
    return selecionadas.filter((selecionadaId) => selecionadaId !== id);
  }
  return [...selecionadas, id];
}

export function idsConsultasVisiveis(consultas) {
  return (consultas ?? [])
    .map((consulta) => Number(consulta?.id))
    .filter((id) => Number.isFinite(id));
}

export function toggleTodasConsultasSelecionadas(selecionadas, consultas) {
  const idsVisiveis = idsConsultasVisiveis(consultas);
  if (idsVisiveis.length === 0) return selecionadas;

  const visiveisSet = new Set(idsVisiveis);
  const todasVisiveisSelecionadas = idsVisiveis.every((id) => selecionadas.includes(id));

  if (todasVisiveisSelecionadas) {
    return selecionadas.filter((id) => !visiveisSet.has(id));
  }

  return Array.from(new Set([...selecionadas, ...idsVisiveis]));
}

export function removerConsultasSelecionadas(consultas, selecionadas) {
  const selecionadasSet = new Set((selecionadas ?? []).map((id) => Number(id)));
  return (consultas ?? []).filter((consulta) => !selecionadasSet.has(Number(consulta?.id)));
}

export function todasConsultasVisiveisSelecionadas(selecionadas, consultas) {
  const idsVisiveis = idsConsultasVisiveis(consultas);
  return idsVisiveis.length > 0 && idsVisiveis.every((id) => selecionadas.includes(id));
}
