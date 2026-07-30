import { useEffect } from "react";

function ensureMeta(selector, attributes) {
  let element = document.head.querySelector(selector);
  if (!element) {
    element = document.createElement(attributes.tag || "meta");
    document.head.appendChild(element);
  }
  Object.entries(attributes).forEach(([key, value]) => {
    if (key !== "tag" && value) element.setAttribute(key, value);
  });
  return element;
}

export default function useEcommerceSeo({ tenantContext, storeDisplayName, selectedProduct }) {
  useEffect(() => {
    if (!tenantContext) return undefined;

    const previousTitle = document.title;
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
    const canonicalUrl = `${window.location.origin}${window.location.pathname}`;

    document.title = title;
    ensureMeta('meta[name="description"]', { name: "description", content: description });
    ensureMeta('meta[property="og:title"]', { property: "og:title", content: title });
    ensureMeta('meta[property="og:description"]', {
      property: "og:description",
      content: description,
    });
    ensureMeta('meta[property="og:type"]', { property: "og:type", content: "website" });
    ensureMeta('meta[property="og:url"]', { property: "og:url", content: canonicalUrl });
    ensureMeta('link[rel="canonical"]', {
      tag: "link",
      rel: "canonical",
      href: canonicalUrl,
    });

    return () => {
      document.title = previousTitle;
    };
  }, [selectedProduct, storeDisplayName, tenantContext]);
}
