import api from './api';
import { Produto, Pedido } from '../types';
import { API_BASE_URL } from '../config';
import * as SecureStore from 'expo-secure-store';

/** Retorna o tenant_id salvo, ou string vazia se não vinculado */
async function getTenantId(): Promise<string> {
  try {
    const raw = await SecureStore.getItemAsync('tenant_info');
    if (raw) return JSON.parse(raw)?.id ?? '';
  } catch (_) {}
  return '';
}

// Resolve URL de mídia: se relativa, usa a base da API
function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  const base = API_BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
  return `${base}${url.startsWith('/') ? url : '/' + url}`;
}

// ─────────────────────────────────────────────────────────────
// AVISE-ME — notificação de estoque
// ─────────────────────────────────────────────────────────────

export async function registrarAviseme(
  email: string,
  product_id: number,
  product_name: string,
): Promise<{ ok: boolean; message: string }> {
  const tenant_id = await getTenantId();
  const { data } = await api.post('/ecommerce-notify/registrar', {
    email,
    product_id,
    product_name,
    tenant_id,
  });
  return data;
}

// ─────────────────────────────────────────────────────────────
// PRODUTOS - endpoints públicos do e-commerce
// ─────────────────────────────────────────────────────────────

export async function listarProdutos(params?: {
  pagina?: number;
  busca?: string;
  categoria_id?: number;
}): Promise<{ produtos: Produto[]; total: number }> {
  const { data } = await api.get('/ecommerce/produtos', {
    params: {
      busca: params?.busca,
      limit: 100,
    },
  });
  // Backend retorna { items: [...] } — adaptar para o formato do app
  const items = data.items ?? data.produtos ?? [];
  const produtos: Produto[] = items.map((p: any) => ({
    id: p.id,
    nome: p.nome,
    preco: p.preco_venda ?? p.preco ?? 0,
    preco_promocional: p.preco_promocional ?? null,
    promocao_ativa: p.promocao_ativa ?? false,
    foto_url: resolveMediaUrl(p.imagem_principal ?? p.foto_url),
    estoque: p.estoque_ecommerce ?? p.estoque_atual ?? p.estoque ?? 0,
    estoque_ecommerce: p.estoque_ecommerce ?? null,
    categoria_nome: p.categoria_nome ?? null,
    marca_nome: p.marca_nome ?? null,
    codigo: p.codigo ?? p.codigo_barras ?? null,
    codigo_barras: p.codigo_barras ?? null,
    descricao: p.descricao ?? null,
    peso_embalagem_kg: p.peso_embalagem ?? null,
  }));
  return { produtos, total: produtos.length };
}

export async function buscarProdutoPorBarcode(barcode: string): Promise<Produto | null> {
  try {
    const { data } = await api.get<Produto>(`/app/produto-barcode/${barcode}`);
    return data;
  } catch (err: any) {
    if (err?.response?.status === 404) return null;
    throw err;
  }
}

export async function buscarProdutoPorId(id: number): Promise<Produto> {
  const { data } = await api.get<Produto>(`/ecommerce/products/${id}`);
  return data;
}

// ─────────────────────────────────────────────────────────────
// CARRINHO - mesmo endpoint do e-commerce
// ─────────────────────────────────────────────────────────────

export async function obterCarrinho(): Promise<{
  pedido_id: string | null;
  itens: any[];
  subtotal: number;
}> {
  const { data } = await api.get('/carrinho');
  return data;
}

export async function adicionarAoCarrinho(produto_id: number, quantidade = 1): Promise<void> {
  await api.post('/carrinho/adicionar', { produto_id, quantidade });
}

export async function atualizarCarrinho(produto_id: number, quantidade: number): Promise<void> {
  await api.put('/carrinho/atualizar', { produto_id, quantidade });
}

export async function removerDoCarrinho(produto_id: number): Promise<void> {
  await api.delete(`/carrinho/remover/${produto_id}`);
}

export async function limparCarrinho(): Promise<void> {
  await api.delete('/carrinho/limpar');
}

// Repetir um pedido anterior: limpa o carrinho e re-adiciona os itens
export async function repetirPedido(pedido: { itens: { produto_id: number; quantidade: number }[] }): Promise<number> {
  await limparCarrinho();
  let adicionados = 0;
  for (const item of pedido.itens) {
    try {
      await adicionarAoCarrinho(item.produto_id, item.quantidade);
      adicionados++;
    } catch {
      // Produto pode ter saído de linha ou sem estoque — ignora silenciosamente
    }
  }
  return adicionados;
}

// ─────────────────────────────────────────────────────────────
// CHECKOUT - com tipo_retirada "app_loja" para compra in-store
// ─────────────────────────────────────────────────────────────

export async function resumoCheckout(cidade: string): Promise<{
  subtotal: number;
  total: number;
  frete: any;
}> {
  const { data } = await api.get('/checkout/resumo', {
    params: { cidade_destino: cidade },
  });
  return data;
}

export interface FormaPagamentoItem {
  id: number;
  nome: string;
  tipo: string;
}

export async function getFormasPagamento(): Promise<FormaPagamentoItem[]> {
  const { data } = await api.get<{ formas_pagamento: FormaPagamentoItem[] }>('/checkout/formas-pagamento');
  return data.formas_pagamento;
}

export interface CheckoutOptions {
  cidade: string;
  modo: 'retirada' | 'entrega'; // retirada na loja ou entrega
  tipoRetirada?: 'proprio' | 'terceiro'; // quem vai retirar
  endereco?: string; // usado quando modo === 'entrega'
  formaPagamentoNome?: string; // forma de pagamento selecionada pelo cliente
}

export async function finalizarCheckoutAppLoja(opcoes: CheckoutOptions | string): Promise<Pedido> {
  // Compatibilidade: aceita string (legado) ou objeto com opções
  const cidade = typeof opcoes === 'string' ? opcoes : opcoes.cidade;
  const modo = typeof opcoes === 'object' ? opcoes.modo : 'retirada';
  const tipoRetirada = typeof opcoes === 'object' ? (opcoes.tipoRetirada ?? 'proprio') : 'proprio';
  const endereco = typeof opcoes === 'object' && opcoes.modo === 'entrega' ? opcoes.endereco : undefined;

  const idempotencyKey = `app-loja-${Date.now()}`;
  const formaPagamentoNome = typeof opcoes === 'object' ? opcoes.formaPagamentoNome : undefined;

  const { data } = await api.post<Pedido>(
    '/checkout/finalizar',
    {
      cidade_destino: cidade,
      tipo_retirada: modo === 'entrega' ? 'entrega' : (tipoRetirada === 'terceiro' ? 'terceiro' : 'app_loja'),
      endereco_entrega: modo === 'entrega' ? (endereco || 'A INFORMAR') : (modo === 'retirada' ? 'RETIRADA NA LOJA' : null),
      forma_pagamento_nome: formaPagamentoNome || null,
      origem: 'app',
    },
    {
      headers: { 'Idempotency-Key': idempotencyKey },
    }
  );
  return data;
}

// ─────────────────────────────────────────────────────────────
// CALCULADORA DE RAÇÃO — busca products com peso de embalagem
// ─────────────────────────────────────────────────────────────

export interface RacaoCadastrada {
  id: number;
  nome: string;
  peso_embalagem: number;    // kg
  preco: number;
  classificacao_racao?: string | null; // filhote, adulto, senior
  categoria_racao?: string | null;
  foto_url?: string | null;
}

export async function listarRacoesCadastradas(): Promise<RacaoCadastrada[]> {
  try {
    const { data } = await api.get('/ecommerce/produtos', {
      params: { limit: 500 },
    });
    const items: any[] = Array.isArray(data) ? data : (data.items ?? data.produtos ?? []);
    return items
      .filter((p: any) => p.peso_embalagem && Number(p.peso_embalagem) > 0)
      .map((p: any) => ({
        id: p.id,
        nome: p.nome,
        peso_embalagem: Number(p.peso_embalagem),
        preco: p.preco_venda ?? p.preco ?? 0,
        classificacao_racao: p.classificacao_racao ?? null,
        categoria_racao: p.categoria_racao ?? null,
        foto_url: resolveMediaUrl(p.imagem_principal ?? p.foto_url),
      }));
  } catch {
    return [];
  }
}

export async function calcularRacaoComProduto(params: {
  produto_id?: number | null;
  peso_pet_kg: number;
  idade_meses?: number | null;
  nivel_atividade: 'baixo' | 'normal' | 'alto';
}): Promise<any> {
  const { data } = await api.post('/api/produtos/calculadora-racao', params);
  return data;
}

export interface ComparativoRacoes {
  racoes: any[];
  melhor_custo_beneficio: number | null;
  maior_duracao: number | null;
  menor_custo_diario: number | null;
}

export async function compararRacoesCategoria(params: {
  peso_pet_kg: number;
  idade_meses?: number | null;
  nivel_atividade: string;
  classificacao?: string | null;
}): Promise<ComparativoRacoes> {
  const query: any = {
    peso_pet_kg: params.peso_pet_kg,
    nivel_atividade: params.nivel_atividade,
  };
  if (params.idade_meses) query.idade_meses = params.idade_meses;
  if (params.classificacao) query.classificacao = params.classificacao;
  // Backend aceita POST com params na query string
  const { data } = await api.post('/api/produtos/comparar-racoes', null, { params: query });
  return data;
}

// ─────────────────────────────────────────────────────────────
// LISTA DE DESEJOS — persistida no AsyncStorage
// ─────────────────────────────────────────────────────────────
// Implementado via wishlist.store.ts

// ─────────────────────────────────────────────────────────────
// PEDIDOS - histórico de pedidos do cliente
// ─────────────────────────────────────────────────────────────

export async function listarPedidos(): Promise<Pedido[]> {
  const { data } = await api.get<{ pedidos: Pedido[] }>('/checkout/pedidos');
  return data.pedidos;
}

export async function consultarStatusPedido(pedidoId: string): Promise<Pedido> {
  const { data } = await api.get<Pedido>(`/checkout/pedido/${pedidoId}/status`);
  return data;
}
