import api from './api';
import { Pet, PetFormData, CalculadoraInput, CalculadoraResultado } from '../types';
import { API_BASE_URL } from '../config';

function resolveUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  const base = API_BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
  return `${base}${url.startsWith('/') ? url : '/' + url}`;
}

function mapPet(raw: any): Pet {
  return { ...raw, foto_url: resolveUrl(raw.foto_url) };
}

// ─────────────────────────────────────────────────────────────
// Endpoints de pets da conta logada no e-commerce
// Rota base: /app/pets/...
// ─────────────────────────────────────────────────────────────

export async function listarPets(): Promise<Pet[]> {
  const { data } = await api.get('/app/pets');
  const arr: any[] = Array.isArray(data) ? data : (data?.pets ?? data?.items ?? []);
  return arr.map(mapPet);
}

export async function criarPet(form: PetFormData): Promise<Pet> {
  const { data } = await api.post<Pet>('/app/pets', form);
  return mapPet(data);
}

export async function atualizarPet(id: number, form: Partial<PetFormData>): Promise<Pet> {
  const { data } = await api.put<Pet>(`/app/pets/${id}`, form);
  return mapPet(data);
}

export async function deletarPet(id: number): Promise<void> {
  await api.delete(`/app/pets/${id}`);
}

export async function uploadFotoPet(petId: number, localUri: string): Promise<Pet> {
  const filename = localUri.split('/').pop() ?? 'foto.jpg';
  const ext = filename.split('.').pop()?.toLowerCase() ?? 'jpg';
  const mimeMap: Record<string, string> = { jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp' };
  const type = mimeMap[ext] ?? 'image/jpeg';

  const formData = new FormData();
  formData.append('file', { uri: localUri, name: filename, type } as any);

  const { data } = await api.post<Pet>(`/app/pets/${petId}/foto`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return mapPet(data);
}

// ─────────────────────────────────────────────────────────────
// Calculadora de ração
// Usa o endpoint existente: /produtos/calculadora-racao
// ─────────────────────────────────────────────────────────────

export async function calcularRacao(
  input: CalculadoraInput
): Promise<CalculadoraResultado> {
  const params: Record<string, string> = {
    peso_pet_kg: String(input.peso_pet_kg),
    nivel_atividade: input.nivel_atividade,
  };
  if (input.produto_id) params.produto_id = String(input.produto_id);
  if (input.idade_meses) params.idade_meses = String(input.idade_meses);
  if (input.peso_embalagem_kg) params.peso_embalagem_kg = String(input.peso_embalagem_kg);
  if (input.preco) params.preco = String(input.preco);

  const { data } = await api.get<CalculadoraResultado>('/produtos/calculadora-racao', { params });
  return data;
}
