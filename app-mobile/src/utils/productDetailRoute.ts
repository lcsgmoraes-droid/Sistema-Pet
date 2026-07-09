type ProductRouteParams = Record<string, unknown> | null | undefined;

type ProductLike = {
  id?: unknown;
};

function toPositiveInteger(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isInteger(value) && value > 0 ? value : null;
  }
  if (typeof value !== "string") return null;

  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) return null;

  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function asProduct(value: unknown): ProductLike | undefined {
  return value && typeof value === "object" ? (value as ProductLike) : undefined;
}

export function resolveProductDetailParams<TProduct extends ProductLike>(
  params: ProductRouteParams,
): { produtoId: number; produtoParam?: TProduct } {
  const produtoParam = asProduct(params?.produto) as TProduct | undefined;
  const explicitProductId = toPositiveInteger(params?.produtoId);
  const produtoParamId = toPositiveInteger(produtoParam?.id);
  const produtoId = explicitProductId ?? produtoParamId ?? 0;

  return {
    produtoId,
    produtoParam:
      produtoParam && (!explicitProductId || produtoParamId === explicitProductId)
        ? produtoParam
        : undefined,
  };
}
