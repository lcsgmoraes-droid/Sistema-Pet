const removeAccents = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

export const PRAZOS = [
  { id: "todos", label: "Todos" },
  { id: "atrasados", label: "Atrasados" },
  { id: "hoje", label: "Hoje" },
  { id: "1-2", label: "1–2 dias" },
  { id: "3-7", label: "3–7 dias" },
  { id: "8-30", label: "8–30 dias" },
  { id: "+30", label: "+30 dias" },
];

export const TIPOS_LEMBRETE = {
  protocolo: "Protocolo",
  proxima_dose: "Próxima dose",
  reinicio_protocolo: "Novo protocolo",
  racao: "Ração",
  recorrencia: "Recorrência cadastrada",
  ciclo_aprendido: "Ciclo aprendido",
};

export function pertenceAoPrazo(dias, prazo) {
  const value = Number(dias);
  if (prazo === "atrasados") return value < 0;
  if (prazo === "hoje") return value === 0;
  if (prazo === "1-2") return value >= 1 && value <= 2;
  if (prazo === "3-7") return value >= 3 && value <= 7;
  if (prazo === "8-30") return value >= 8 && value <= 30;
  if (prazo === "+30") return value > 30;
  return true;
}

export function filtrarLembretes(lembretes, { busca = "", prazo = "todos", tipo = "todos" }) {
  const search = removeAccents(busca).trim();
  return lembretes.filter((lembrete) => {
    const matchesDeadline = pertenceAoPrazo(lembrete.dias_restantes, prazo);
    const matchesType = tipo === "todos" || lembrete.tipo_lembrete === tipo;
    const searchable = removeAccents(
      `${lembrete.cliente_nome} ${lembrete.pet_nome} ${lembrete.produto_nome}`,
    );
    const matchesSearch = !search || search.split(/\s+/).every((term) => searchable.includes(term));
    return matchesDeadline && matchesType && matchesSearch;
  });
}

export function contarPorPrazo(lembretes) {
  return Object.fromEntries(
    PRAZOS.map(({ id }) => [
      id,
      lembretes.filter((item) => pertenceAoPrazo(item.dias_restantes, id)).length,
    ]),
  );
}

export function whatsappUrl(telefone, mensagem) {
  let digits = String(telefone || "").replace(/\D/g, "");
  if (!digits) return null;
  if (digits.length === 10 || digits.length === 11) digits = `55${digits}`;
  return `https://wa.me/${digits}?text=${encodeURIComponent(String(mensagem || ""))}`;
}
