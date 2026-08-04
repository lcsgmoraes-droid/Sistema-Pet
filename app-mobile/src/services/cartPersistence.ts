import AsyncStorage from "@react-native-async-storage/async-storage";
import { ItemCarrinho } from "../types";

const CART_CACHE_PREFIX = "corepet_cart_v1";

export interface CartPersistenceContext {
  tenantId: string;
  userId: number;
}

export interface CartSnapshot {
  itens: ItemCarrinho[];
  subtotal: number;
  updatedAt: string;
}

function storageKey(context: CartPersistenceContext): string {
  return `${CART_CACHE_PREFIX}:${context.tenantId}:${context.userId}`;
}

function normalizeItem(value: unknown): ItemCarrinho | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Partial<ItemCarrinho>;
  const produtoId = Number(item.produto_id);
  const quantidade = Number(item.quantidade);
  const precoUnitario = Number(item.preco_unitario);

  if (
    !Number.isInteger(produtoId) ||
    produtoId <= 0 ||
    !Number.isFinite(quantidade) ||
    quantidade <= 0 ||
    !Number.isFinite(precoUnitario) ||
    precoUnitario < 0
  ) {
    return null;
  }

  return {
    produto_id: produtoId,
    nome: String(item.nome || "Produto"),
    preco_unitario: precoUnitario,
    quantidade,
    subtotal: Number.isFinite(Number(item.subtotal))
      ? Number(item.subtotal)
      : precoUnitario * quantidade,
    foto_url: item.foto_url || null,
  };
}

function calculateSubtotal(itens: ItemCarrinho[]): number {
  return itens.reduce((total, item) => total + item.subtotal, 0);
}

export async function loadCartSnapshot(
  context: CartPersistenceContext,
): Promise<CartSnapshot | null> {
  const raw = await AsyncStorage.getItem(storageKey(context));
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<CartSnapshot>;
    const itens = Array.isArray(parsed.itens)
      ? parsed.itens
          .map(normalizeItem)
          .filter((item): item is ItemCarrinho => Boolean(item))
      : [];
    return {
      itens,
      subtotal: calculateSubtotal(itens),
      updatedAt: String(parsed.updatedAt || ""),
    };
  } catch {
    await AsyncStorage.removeItem(storageKey(context));
    return null;
  }
}

export async function saveCartSnapshot(
  context: CartPersistenceContext,
  itens: ItemCarrinho[],
): Promise<void> {
  const snapshot: CartSnapshot = {
    itens,
    subtotal: calculateSubtotal(itens),
    updatedAt: new Date().toISOString(),
  };
  await AsyncStorage.setItem(storageKey(context), JSON.stringify(snapshot));
}

export function clearCartSnapshot(
  context: CartPersistenceContext,
): Promise<void> {
  return AsyncStorage.removeItem(storageKey(context));
}
