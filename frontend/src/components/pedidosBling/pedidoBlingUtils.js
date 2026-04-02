export const STATUS_CONFIG = {
  aberto: { label: 'Aberto', cor: 'bg-blue-100 text-blue-800', dot: 'bg-blue-500' },
  confirmado: { label: 'Confirmado', cor: 'bg-green-100 text-green-800', dot: 'bg-green-500' },
  expirado: { label: 'Expirado', cor: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' },
  cancelado: { label: 'Cancelado', cor: 'bg-red-100 text-red-800', dot: 'bg-red-500' },
};

export const PEDIDOS_BLING_ABAS = [
  { valor: '', label: 'Todos' },
  { valor: 'aberto', label: 'Abertos' },
  { valor: 'confirmado', label: 'Confirmados' },
  { valor: 'expirado', label: 'Expirados' },
  { valor: 'cancelado', label: 'Cancelados' },
];

export function formatarDataHora(iso) {
  if (!iso) return '-';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '-';
  return data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

export function formatarMoeda(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return '-';
  return Number(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
