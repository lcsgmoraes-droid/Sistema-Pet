import { useMemo, useState } from 'react';
import {
  buildCatalogCategories,
  buildProductMap,
  calculateCatalogMetrics,
  filterCatalogProducts,
} from './ecommerceMvpUtils';

export default function useEcommerceCatalog() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');
  const [categoria, setCategoria] = useState('todas');
  const [somenteComEstoque, setSomenteComEstoque] = useState(false);
  const [somenteComImagem, setSomenteComImagem] = useState(false);
  const [ordenacaoCatalogo, setOrdenacaoCatalogo] = useState('prontos');

  const categorias = useMemo(() => {
    return buildCatalogCategories(products);
  }, [products]);

  const catalogMetrics = useMemo(() => {
    return calculateCatalogMetrics(products);
  }, [products]);

  const filteredProducts = useMemo(() => {
    return filterCatalogProducts(products, {
      search,
      categoria,
      somenteComEstoque,
      somenteComImagem,
      ordenacaoCatalogo,
    });
  }, [products, search, categoria, somenteComEstoque, somenteComImagem, ordenacaoCatalogo]);

  const productMap = useMemo(() => buildProductMap(products), [products]);

  function clearCatalogFilters() {
    setSearch('');
    setCategoria('todas');
    setSomenteComEstoque(false);
    setSomenteComImagem(false);
    setOrdenacaoCatalogo('prontos');
  }

  return {
    products,
    setProducts,
    search,
    setSearch,
    categoria,
    setCategoria,
    somenteComEstoque,
    setSomenteComEstoque,
    somenteComImagem,
    setSomenteComImagem,
    ordenacaoCatalogo,
    setOrdenacaoCatalogo,
    categorias,
    catalogMetrics,
    filteredProducts,
    productMap,
    clearCatalogFilters,
  };
}
