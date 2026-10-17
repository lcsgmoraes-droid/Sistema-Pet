export const deveMostrarParcelaNaDescricao = (conta) => {
  if (!conta?.eh_parcelado || !conta.numero_parcela || !conta.total_parcelas) return false;

  const numero = Number(conta.numero_parcela);
  const total = Number(conta.total_parcelas);
  if (!Number.isInteger(numero) || !Number.isInteger(total)) return false;

  const parcelaNaDescricao = new RegExp(`\\bparcela\\s*${numero}\\s*/\\s*${total}\\b`, "i");
  return !parcelaNaDescricao.test(conta.descricao || "");
};
