import { useEffect, useState } from "react";
import { trackViewItem } from "../../services/analytics";
import { useEscapeToClose } from "../../utils/modalEscape";
import { getProductImages } from "./ecommerceMvpUtils";

export default function useEcommerceProductModal({ products, location, navigate }) {
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [activeProductImage, setActiveProductImage] = useState("");

  function openProductDetails(product) {
    const images = getProductImages(product);
    setSelectedProduct(product);
    setActiveProductImage(images[0] || "");
    navigate(`${location.pathname}?produto=${product.id}`, { replace: true });
    trackViewItem(product);
  }

  function closeProductModal() {
    setSelectedProduct(null);
    navigate(location.pathname, { replace: true });
  }

  useEscapeToClose({ isOpen: Boolean(selectedProduct), onClose: closeProductModal });

  useEffect(() => {
    if (!products.length) return;
    const searchParams = new URLSearchParams(location.search);
    const prodIdFromUrl = searchParams.get("produto");
    if (!prodIdFromUrl || selectedProduct) return;
    const found = products.find((product) => String(product.id) === String(prodIdFromUrl));
    if (found) openProductDetails(found);
  }, [products.length, location.search]);

  return {
    selectedProduct,
    activeProductImage,
    setActiveProductImage,
    openProductDetails,
    closeProductModal,
  };
}
