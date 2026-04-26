export function hojeIso() {
  return new Date().toISOString().slice(0, 10);
}

export function formatarData(iso) {
  if (!iso) return "-";
  const data = new Date(`${iso}T12:00:00`);
  return data.toLocaleDateString("pt-BR");
}

export const FORM_EXAME_ANEXADO_INICIAL = {
  pet_id: "",
  tipo: "laboratorial",
  nome: "",
  data_solicitacao: hojeIso(),
  laboratorio: "",
  observacoes: "",
};
