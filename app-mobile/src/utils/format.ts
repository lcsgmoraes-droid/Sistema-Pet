export function formatarMoeda(valor: number | null | undefined): string {
  if (valor == null) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(valor);
}

export function formatarData(data: string | null | undefined): string {
  if (!data) return '—';
  const d = new Date(data);
  return d.toLocaleDateString('pt-BR');
}

export function formatarDataHora(data: string | null | undefined): string {
  if (!data) return '—';
  const d = new Date(data);
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

export function calcularIdade(dataNascimento: string | null | undefined): string {
  if (!dataNascimento) return '';
  const nascimento = new Date(dataNascimento);
  const agora = new Date();
  const diffMs = agora.getTime() - nascimento.getTime();
  const meses = Math.floor(diffMs / (1000 * 60 * 60 * 24 * 30.44));
  if (meses < 12) return `${meses} ${meses === 1 ? 'mês' : 'meses'}`;
  const anos = Math.floor(meses / 12);
  const mesesRest = meses % 12;
  if (mesesRest === 0) return `${anos} ${anos === 1 ? 'ano' : 'anos'}`;
  return `${anos}a ${mesesRest}m`;
}

/** Retorna a idade em meses calculada a partir de data_nascimento */
export function calcularIdadeMeses(dataNascimento: string | null | undefined): number | null {
  if (!dataNascimento) return null;
  const nascimento = new Date(dataNascimento);
  const agora = new Date();
  const diffMs = agora.getTime() - nascimento.getTime();
  const meses = Math.floor(diffMs / (1000 * 60 * 60 * 24 * 30.44));
  return meses > 0 ? meses : null;
}
