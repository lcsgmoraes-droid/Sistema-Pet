type ProductAvailabilityLike = {
  anunciar_app?: boolean | null;
  disponivel_app?: boolean | null;
  anunciar_ecommerce?: boolean | null;
  disponivel_ecommerce?: boolean | null;
  estoque?: number | null;
  estoque_atual?: number | null;
};

export function isProductAvailableInApp(product?: ProductAvailabilityLike | null): boolean {
  if (!product) return false;
  return product.anunciar_app !== false && product.disponivel_app !== false;
}

export function isProductAvailableInEcommerce(product?: ProductAvailabilityLike | null): boolean {
  if (!product) return false;
  const estoque = Number(product.estoque_atual ?? product.estoque ?? 0);
  return product.anunciar_ecommerce !== false && product.disponivel_ecommerce !== false && estoque > 0;
}

export function buildEcommerceSearchUrl(params: {
  apiBaseUrl: string;
  tenantSlug?: string | null;
  query?: string | null;
}): string | null {
  const tenantSlug = params.tenantSlug?.trim();
  const query = params.query?.trim();
  if (!tenantSlug || !query) return null;

  const baseUrl = params.apiBaseUrl.trim().replace(/\/api\/?$/, '').replace(/\/$/, '');
  return `${baseUrl}/${encodeURIComponent(tenantSlug)}?busca=${encodeURIComponent(query)}`;
}
