import { useEffect } from "react";
import { buildProductShareUrl } from "./ecommerceProductLinks";
import { getProductImages, resolveMediaUrl } from "./ecommerceMvpUtils";

function updateHeadElement(selector, attributes) {
  let element = document.head.querySelector(selector);
  const previous = element?.cloneNode(true);
  if (!attributes) {
    element?.remove();
  } else {
    if (!element) {
      element = document.createElement(attributes.tag || "meta");
      document.head.appendChild(element);
    }
    Object.entries(attributes).forEach(([key, value]) => {
      if (key !== "tag") element.setAttribute(key, value);
    });
  }
  return () => {
    if (previous) {
      if (element?.isConnected) element.replaceWith(previous);
      else document.head.appendChild(previous);
    } else element?.remove();
  };
}

export default function useEcommerceSeo({
  tenantContext,
  storeDisplayName,
  selectedProduct,
  canonicalUrl,
}) {
  useEffect(() => {
    if (!tenantContext) return undefined;

    const previousTitle = document.title;
    const restore = [];
    const ensureMeta = (selector, attributes) => {
      restore.push(updateHeadElement(selector, attributes));
    };
    const title = selectedProduct?.nome
      ? `${selectedProduct.nome} | ${storeDisplayName}`
      : `${storeDisplayName} | Loja online`;
    const description = String(
      selectedProduct?.descricao ||
        tenantContext.ecommerce_descricao ||
        `Compre online na ${storeDisplayName}.`,
    )
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 160);
    const image = getProductImages(selectedProduct)[0] || resolveMediaUrl(tenantContext.logo_url);
    const shareUrl = selectedProduct ? buildProductShareUrl(canonicalUrl) : canonicalUrl;
    document.title = title;
    ensureMeta('meta[name="description"]', { name: "description", content: description });
    ensureMeta('meta[property="og:title"]', { property: "og:title", content: title });
    ensureMeta('meta[property="og:description"]', {
      property: "og:description",
      content: description,
    });
    ensureMeta('meta[property="og:type"]', { property: "og:type", content: "website" });
    ensureMeta('meta[property="og:url"]', { property: "og:url", content: shareUrl });
    ensureMeta('meta[property="og:image"]', image ? { property: "og:image", content: image } : null);
    ensureMeta('meta[property="og:image:alt"]', image ? {
      property: "og:image:alt", content: selectedProduct?.nome || storeDisplayName,
    } : null);
    ensureMeta('meta[name="twitter:card"]', {
      name: "twitter:card", content: image ? "summary_large_image" : "summary",
    });
    ensureMeta('meta[name="twitter:title"]', { name: "twitter:title", content: title });
    ensureMeta('meta[name="twitter:description"]', { name: "twitter:description", content: description });
    ensureMeta('meta[name="twitter:image"]', image ? { name: "twitter:image", content: image } : null);
    ensureMeta('link[rel="canonical"]', {
      tag: "link",
      rel: "canonical",
      href: canonicalUrl,
    });

    return () => {
      document.title = previousTitle;
      restore.reverse().forEach((cleanup) => cleanup());
    };
  }, [canonicalUrl, selectedProduct, storeDisplayName, tenantContext]);
}
