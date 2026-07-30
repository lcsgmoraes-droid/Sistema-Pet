import { useMemo, useState } from "react";
import {
  DEFAULT_CATALOG_LIMIT,
  DEFAULT_CATALOG_ORDER,
  buildCatalogCategoryOptions,
  buildProductMap,
} from "./ecommerceMvpUtils";

export default function useEcommerceCatalog() {
  const [products, setProducts] = useState([]);
  const [productCache, setProductCache] = useState({});
  const [catalogMeta, setCatalogMeta] = useState({
    total: 0,
    offset: 0,
    limit: DEFAULT_CATALOG_LIMIT,
    categories: [],
    brands: [],
  });
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [categoria, setCategoria] = useState("todas");
  const [ordenacaoCatalogo, setOrdenacaoCatalogo] = useState(DEFAULT_CATALOG_ORDER);
  const [marca, setMarca] = useState("");
  const [apenasComEstoque, setApenasComEstoque] = useState(false);
  const [apenasComImagem, setApenasComImagem] = useState(false);
  const [precoMinimo, setPrecoMinimo] = useState("");
  const [precoMaximo, setPrecoMaximo] = useState("");

  const categorias = useMemo(() => {
    return buildCatalogCategoryOptions({
      categories: catalogMeta.categories,
      products,
    });
  }, [catalogMeta.categories, products]);

  const productMap = useMemo(
    () => ({
      ...productCache,
      ...buildProductMap(products),
    }),
    [productCache, products],
  );

  function setCatalogProducts(nextProducts) {
    const normalizedProducts = Array.isArray(nextProducts) ? nextProducts : [];
    setProducts(normalizedProducts);
    setProductCache((current) => ({
      ...current,
      ...buildProductMap(normalizedProducts),
    }));
  }

  function clearCatalogFilters() {
    setSearch("");
    setCategoria("todas");
    setOrdenacaoCatalogo(DEFAULT_CATALOG_ORDER);
    setMarca("");
    setApenasComEstoque(false);
    setApenasComImagem(false);
    setPrecoMinimo("");
    setPrecoMaximo("");
    setPage(1);
  }

  return {
    products,
    setProducts: setCatalogProducts,
    catalogMeta,
    setCatalogMeta,
    page,
    setPage,
    search,
    setSearch,
    categoria,
    setCategoria,
    ordenacaoCatalogo,
    setOrdenacaoCatalogo,
    marca,
    setMarca,
    apenasComEstoque,
    setApenasComEstoque,
    apenasComImagem,
    setApenasComImagem,
    precoMinimo,
    setPrecoMinimo,
    precoMaximo,
    setPrecoMaximo,
    categorias,
    filteredProducts: products,
    productMap,
    clearCatalogFilters,
  };
}
