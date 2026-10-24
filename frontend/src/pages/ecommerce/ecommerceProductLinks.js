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

// O HTML deste endereço já contém a foto e o nome antes de executar JavaScript.
// A URL normal continua sendo usada pela navegação da loja.
export function buildProductShareUrl(productUrl) {
  try {
    const product = new URL(productUrl);
    const productId = product.searchParams.get("produto");
    const pathTenant = product.pathname.match(/^\/([^/]+)\/?$/)?.[1];
    const tenant = product.searchParams.get("tenant") ||
      (pathTenant !== "ecommerce" ? decodeURIComponent(pathTenant || "") : "");
    if (!/^[1-9]\d*$/.test(productId || "") || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/i.test(tenant)) {
      return productUrl;
    }
    const share = new URL(`/api/ecommerce/compartilhar/produtos/${productId}`, product.origin);
    share.searchParams.set("tenant", tenant);
    return share.href;
  } catch {
    return productUrl;
  }
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
