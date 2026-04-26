import { parseListaTexto, parseNumero } from "./shared";

export const FORM_MEDICAMENTO_INICIAL = {
  nome: "",
  nome_comercial: "",
  principio_ativo: "",
  fabricante: "",
  forma_farmaceutica: "",
  concentracao: "",
  especies_indicadas: "",
  indicacoes: "",
  posologia_referencia: "",
  dose_min_mgkg: "",
  dose_max_mgkg: "",
  contraindicacoes: "",
  interacoes: "",
  observacoes: "",
  eh_antibiotico: false,
  eh_controlado: false,
};

export function mapMedicamentoParaForm(item) {
  return {
    nome: item?.nome || "",
    nome_comercial: item?.nome_comercial || "",
    principio_ativo: item?.principio_ativo || "",
    fabricante: item?.fabricante || "",
    forma_farmaceutica: item?.forma_farmaceutica || "",
    concentracao: item?.concentracao || "",
    especies_indicadas: Array.isArray(item?.especies_indicadas) ? item.especies_indicadas.join(", ") : "",
    indicacoes: item?.indicacoes || "",
    posologia_referencia: item?.posologia_referencia || "",
    dose_min_mgkg: item?.dose_min_mgkg ?? "",
    dose_max_mgkg: item?.dose_max_mgkg ?? "",
    contraindicacoes: item?.contraindicacoes || "",
    interacoes: item?.interacoes || "",
    observacoes: item?.observacoes || "",
    eh_antibiotico: Boolean(item?.eh_antibiotico),
    eh_controlado: Boolean(item?.eh_controlado),
  };
}

export function buildMedicamentoPayload(form) {
  return {
    nome: form.nome.trim(),
    nome_comercial: form.nome_comercial.trim() || undefined,
    principio_ativo: form.principio_ativo.trim() || undefined,
    fabricante: form.fabricante.trim() || undefined,
    forma_farmaceutica: form.forma_farmaceutica.trim() || undefined,
    concentracao: form.concentracao.trim() || undefined,
    especies_indicadas: parseListaTexto(form.especies_indicadas),
    indicacoes: form.indicacoes.trim() || undefined,
    posologia_referencia: form.posologia_referencia.trim() || undefined,
    dose_min_mgkg: parseNumero(form.dose_min_mgkg),
    dose_max_mgkg: parseNumero(form.dose_max_mgkg),
    contraindicacoes: form.contraindicacoes.trim() || undefined,
    interacoes: form.interacoes.trim() || undefined,
    observacoes: form.observacoes.trim() || undefined,
    eh_antibiotico: Boolean(form.eh_antibiotico),
    eh_controlado: Boolean(form.eh_controlado),
  };
}
