const UM_DIA_MS = 24 * 60 * 60 * 1000;

function dataLocal(valor = new Date()) {
  return new Date(valor.getFullYear(), valor.getMonth(), valor.getDate());
}

export function adicionarDiasDataLocal(dias, referencia = new Date()) {
  const data = dataLocal(referencia);
  data.setDate(data.getDate() + Number(dias || 0));
  return data;
}

export function dataLocalParaISO(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function isoParaDataLocal(valor) {
  const match = String(valor || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  const data = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(data.getTime()) ? null : data;
}

export function formatarDataFimRacao(valor) {
  const data = isoParaDataLocal(valor);
  return data ? data.toLocaleDateString("pt-BR") : "";
}

export function calcularDataFimPorPrazo(prazoDias, referencia = new Date()) {
  const prazo = Number.parseInt(prazoDias, 10);
  if (!Number.isInteger(prazo) || prazo < 1 || prazo > 365) return "";
  return dataLocalParaISO(adicionarDiasDataLocal(prazo, referencia));
}

export function validarDataFimRacao(valor, referencia = new Date()) {
  const data = isoParaDataLocal(valor);
  if (!data) return false;
  return data.getTime() >= dataLocal(referencia).getTime() + UM_DIA_MS;
}

export function resumirPrevisaoFimRacao(item) {
  if (item?.racao_data_prevista_fim) {
    const data = formatarDataFimRacao(item.racao_data_prevista_fim);
    return data ? `Acaba em ${data}` : "Aviso programado";
  }
  const prazo = Number.parseInt(item?.racao_prazo_estimado_dias, 10);
  return Number.isInteger(prazo) && prazo > 0
    ? `Acaba em cerca de ${prazo} dia${prazo === 1 ? "" : "s"}`
    : "Avisar quando acabar";
}
