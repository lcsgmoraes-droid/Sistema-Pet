// Links públicos levam apenas a identificação da loja e do produto.
// Busca, checkout e outros parâmetros da sessão não entram no compartilhamento.
export function buildProductUrl({ origin, pathname, search = "" }, productId, tenantRef = "") {
  const url = new URL(pathname, origin);
  const tenant = new URLSearchParams(search).get("tenant");
  if (tenant || (pathname === "/ecommerce" && tenantRef)) {
    url.searchParams.set("tenant", tenant || tenantRef);
  }
  if (productId) url.searchParams.set("produto", String(productId));
  return url.href;
}

export function buildProductWhatsappUrl(product, url) {
  return `https://wa.me/?text=${encodeURIComponent(`${product.nome}\n${url}`)}`;
}

export async function copyProductUrl(url, browserNavigator = navigator) {
  try {
    if (!browserNavigator.clipboard?.writeText) return false;
    await browserNavigator.clipboard.writeText(url);
    return true;
  } catch {
    return false;
  }
}

export async function shareProductUrl(product, url, browserNavigator = navigator) {
  if (!browserNavigator.share) return "fallback";
  try {
    await browserNavigator.share({ title: product.nome, text: product.nome, url });
    return "shared";
  } catch (error) {
    return error.name === "AbortError" ? "cancelled" : "fallback";
  }
}
