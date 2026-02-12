import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

/**
 * Hook para gerenciar listagem paginada de produtos
 * 
 * Funcionalidades:
 * - Paginação backend
 * - Filtros persistentes
 * - Loading states
 * - Auto-refresh em mudança de página/filtros
 * 
 * @param {object} filters - Filtros da listagem
 * @param {number} pageSize - Tamanho da página (padrão: 50)
 * @returns {object} { produtos, total, page, pages, loading, error, setPage, refresh }
 */
export const usePaginatedProducts = (filters = {}, pageSize = 50) => {
  const [produtos, setProdutos] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Busca produtos da API com paginação
   */
  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get('/produtos', {
        params: {
          ...filters,
          page,
          page_size: pageSize,
        },
      });

      // Espera formato: { items, total, page, page_size, pages }
      setProdutos(response.data.items || []);
      setTotal(response.data.total || 0);
      setPages(response.data.pages || 0);

    } catch (err) {
      console.error('Erro ao buscar produtos:', err);
      setError(err.response?.data?.detail || 'Erro ao carregar produtos');
      setProdutos([]);
      setTotal(0);
      setPages(0);
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize]);

  // Buscar produtos quando dependências mudarem
  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Reset página ao mudar filtros
  useEffect(() => {
    setPage(1);
  }, [JSON.stringify(filters)]);

  /**
   * Força refresh manual
   */
  const refresh = useCallback(() => {
    fetchProducts();
  }, [fetchProducts]);

  /**
   * Vai para página específica
   */
  const goToPage = useCallback((newPage) => {
    if (newPage >= 1 && newPage <= pages) {
      setPage(newPage);
    }
  }, [pages]);

  /**
   * Próxima página
   */
  const nextPage = useCallback(() => {
    if (page < pages) {
      setPage(page + 1);
    }
  }, [page, pages]);

  /**
   * Página anterior
   */
  const previousPage = useCallback(() => {
    if (page > 1) {
      setPage(page - 1);
    }
  }, [page]);

  return {
    produtos,
    total,
    page,
    pages,
    pageSize,
    loading,
    error,
    setPage: goToPage,
    nextPage,
    previousPage,
    refresh,
  };
};
