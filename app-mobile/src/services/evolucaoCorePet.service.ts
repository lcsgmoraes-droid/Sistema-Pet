import AsyncStorage from '@react-native-async-storage/async-storage';
import api from './api';

export type EvolucaoStatus =
  | 'em_estudo'
  | 'planejado'
  | 'em_desenvolvimento'
  | 'em_testes'
  | 'disponivel';

export type EvolucaoCorePetItem = {
  id: string;
  titulo: string;
  resumo: string;
  status: EvolucaoStatus;
  tipo: 'novidade' | 'melhoria' | 'projeto';
  modulo: string;
  plataformas: string[];
  publicado_em?: string | null;
  atualizado_em: string;
  destaque?: boolean;
  caminho_ajuda?: string | null;
  fase_disponibilidade?: 'teste' | 'implantado' | null;
  status_label?: string | null;
  implantado_em?: string | null;
  novidade_ate?: string | null;
};

export type EvolucaoCorePetResponse = {
  itens: EvolucaoCorePetItem[];
  atualizado_em?: string | null;
  total_disponivel: number;
};

function storageKey(userId?: number | null): string {
  return `corepet.evolucao.itens-vistos.${userId ?? 'anonimo'}`;
}

async function lerIdsVistos(userId?: number | null): Promise<Set<string>> {
  try {
    const raw = await AsyncStorage.getItem(storageKey(userId));
    const value = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(value) ? value.filter(Boolean) : []);
  } catch {
    return new Set();
  }
}

export async function listarEvolucaoCorePetApp(): Promise<EvolucaoCorePetResponse> {
  const { data } = await api.get('/app/evolucao');
  const itens = Array.isArray(data?.itens) ? data.itens : [];
  return {
    itens,
    atualizado_em: data?.atualizado_em ?? null,
    total_disponivel: Number(data?.total_disponivel ?? 0),
  };
}

export async function contarNovidadesAppNaoVistas(
  itens: EvolucaoCorePetItem[],
  userId?: number | null,
): Promise<number> {
  const vistos = await lerIdsVistos(userId);
  return itens.filter(
    (item) => item.status === 'disponivel' && !vistos.has(item.id),
  ).length;
}

export async function marcarNovidadesAppComoVistas(
  itens: EvolucaoCorePetItem[],
  userId?: number | null,
): Promise<void> {
  const vistos = await lerIdsVistos(userId);
  itens
    .filter((item) => item.status === 'disponivel')
    .forEach((item) => vistos.add(item.id));
  await AsyncStorage.setItem(storageKey(userId), JSON.stringify([...vistos]));
}
