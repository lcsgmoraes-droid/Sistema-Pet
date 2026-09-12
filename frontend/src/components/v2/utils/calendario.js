export const NOMES_MES = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];

export const DIAS_SEMANA_ABREV = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

export function dataParaISO(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function isoParaData(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
  if (!match) return null;
  const [, ano, mes, dia] = match;
  return new Date(Number(ano), Number(mes) - 1, Number(dia));
}

export function isoHoje() {
  return dataParaISO(new Date());
}

export function adicionarMeses(data, quantidade) {
  return new Date(data.getFullYear(), data.getMonth() + quantidade, 1);
}

export function obterGradeMes(mesVisivel) {
  const ano = mesVisivel.getFullYear();
  const mes = mesVisivel.getMonth();
  const primeiroDia = new Date(ano, mes, 1);
  const inicioGrade = new Date(ano, mes, 1 - primeiroDia.getDay());

  return Array.from({ length: 42 }, (_, indice) => {
    const data = new Date(inicioGrade);
    data.setDate(inicioGrade.getDate() + indice);
    return { data, iso: dataParaISO(data), noMesAtual: data.getMonth() === mes };
  });
}

export function isoEntre(iso, inicio, fim) {
  if (!iso || !inicio || !fim) return false;
  return iso >= inicio && iso <= fim;
}
