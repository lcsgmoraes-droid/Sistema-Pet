import { CORES } from "../../../theme";
import type { Pet } from "../../../types";
import { calcularIdade } from "../../../utils/format";

export function formatarIdadePet(pet: Pet): string {
  if (pet.data_nascimento) return calcularIdade(pet.data_nascimento);
  if (typeof pet.idade_aproximada === 'number' && pet.idade_aproximada >= 0) {
    return formatarIdadeMeses(pet.idade_aproximada);
  }
  return 'Idade nao informada';
}

export function formatarIdadeMeses(meses: number): string {
  if (meses < 12) return `${meses} ${meses === 1 ? 'mes' : 'meses'}`;
  const anos = Math.floor(meses / 12);
  const mesesRestantes = meses % 12;
  if (!mesesRestantes) return `${anos} ${anos === 1 ? 'ano' : 'anos'}`;
  return `${anos}a ${mesesRestantes}m`;
}

export function labelStatusVacina(status?: string | null): string {
  const mapa: Record<string, string> = {
    em_dia: 'Em dia',
    vence_breve: 'Vence breve',
    atrasada: 'Atrasada',
  };
  return status ? mapa[status] ?? status : 'Registrada';
}

export function corStatusVacina(status?: string | null): string {
  if (status === 'atrasada') return CORES.erro;
  if (status === 'vence_breve') return '#B7791F';
  return '#047857';
}

export function resumirHash(hash?: string | null): string {
  if (!hash) return 'Sem codigo';
  return `${hash.slice(0, 8).toUpperCase()}...${hash.slice(-6).toUpperCase()}`;
}

