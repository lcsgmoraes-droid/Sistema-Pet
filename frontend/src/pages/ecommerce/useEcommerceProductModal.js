import { useEffect, useState } from "react";
import { trackViewItem } from "../../services/analytics";
import ecommerceApi from "../../services/ecommerceApi";
import { useEscapeToClose } from "../../utils/modalEscape";
import { extractApiErrorMessage, getProductImages } from "./ecommerceMvpUtils";

export default function useEcommerceProductModal({ location, navigate, tenantRef }) {
  const productId = new URLSearchParams(location.search).get("produto") || "";
  const selectionKey = `${tenantRef || ""}:${productId}`;
  const [productState, setProductState] = useState({ key: "", product: null, loading: false });
  const [activeProductImage, setActiveProductImage] = useState("");
  const selectedProduct = productState.key === selectionKey ? productState.product : null;
  const productError = productState.key === selectionKey ? productState.error || "" : "";
  const productLoading =
    Boolean(productId && tenantRef) && (productState.key !== selectionKey || productState.loading);

  function navigateToProduct(nextProductId) {
    const searchParams = new URLSearchParams(location.search);
    if (nextProductId) searchParams.set("produto", String(nextProductId));
    else searchParams.delete("produto");
    navigate(
      {
        pathname: location.pathname,
        search: searchParams.toString() ? `?${searchParams}` : "",
        hash: location.hash,
      },
      { replace: true },
    );
  }

  function openProductDetails(product) {
    navigateToProduct(product.id);
  }

  function closeProductModal() {
    navigateToProduct(null);
  }

  useEscapeToClose({ isOpen: Boolean(productId), onClose: closeProductModal });

  useEffect(() => {
    let active = true;

    if (!productId || !tenantRef) {
      setProductState({ key: selectionKey, product: null, loading: false });
      setActiveProductImage("");
      return undefined;
    }

    if (!/^[1-9]\d*$/.test(productId)) {
      setProductState({
        key: selectionKey,
        product: null,
        loading: false,
        error: "O link deste produto é inválido.",
      });
      return undefined;
    }

    function selectProduct(product) {
      if (!active) return;
      setActiveProductImage(getProductImages(product)[0] || "");
      trackViewItem(product);
      setProductState({ key: selectionKey, product, loading: false });
    }

    setProductState({ key: selectionKey, product: null, loading: true });
    ecommerceApi
      .get(`/api/ecommerce/products/${productId}`, {
        params: { tenant: tenantRef, canal: "ecommerce" },
      })
      .then((response) => selectProduct(response.data))
      .catch((error) => {
        if (!active) return;
        setProductState({
          key: selectionKey,
          product: null,
          loading: false,
          error:
            error?.response?.status === 404
              ? "Este produto não está mais disponível nesta loja."
              : extractApiErrorMessage(error, "Não foi possível abrir este produto."),
        });
      });

    return () => {
      active = false;
    };
  }, [productId, selectionKey, tenantRef]);

  return {
    selectedProduct,
    productLoading,
    productError,
    activeProductImage,
    setActiveProductImage,
    openProductDetails,
    closeProductModal,
  };
}
