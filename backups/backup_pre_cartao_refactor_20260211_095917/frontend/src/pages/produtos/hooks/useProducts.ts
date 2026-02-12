/**
 * SPRINT 7 - PASSO 1: Hook para gerenciamento de produtos
 * Sistema ERP Pet Shop
 */

import { useState, useEffect, useCallback } from 'react';
import api from '../../../api';
import toast from 'react-hot-toast';
import type { Product, ProductFilters, ProductListResponse } from '../types';

interface UseProductsReturn {
  products: Product[];
  loading: boolean;
  error: string | null;
  currentPage: number;
  totalPages: number;
  total: number;
  filters: ProductFilters;
  setFilters: (filters: ProductFilters) => void;
  setCurrentPage: (page: number) => void;
  refetch: () => void;
  deleteProduct: (id: number) => Promise<void>;
  toggleProductStatus: (id: number, currentStatus: string) => Promise<void>;
}

export const useProducts = (): UseProductsReturn => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<ProductFilters>({
    busca: '',
    status: ''
  });

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Construir query params
      const params: any = {
        pagina: currentPage,
        limite: 20
      };
      
      if (filters.busca) {
        params.busca = filters.busca;
      }
      
      if (filters.status) {
        params.status = filters.status;
      }

      const response = await api.get<ProductListResponse>('/produtos', { params });

      // Normalizar resposta da API
      let productData: Product[] = [];
      let totalItems = 0;
      let totalPgs = 1;

      if (Array.isArray(response.data)) {
        productData = response.data;
        totalItems = response.data.length;
      } else if (response.data.produtos) {
        productData = response.data.produtos;
        totalItems = response.data.total || 0;
        totalPgs = response.data.total_paginas || 1;
      } else if (response.data.itens) {
        productData = (response.data as any).itens;
        totalItems = (response.data as any).total || 0;
        totalPgs = (response.data as any).total_paginas || 1;
      }

      setProducts(productData);
      setTotal(totalItems);
      setTotalPages(totalPgs);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Erro ao carregar produtos';
      setError(errorMessage);
      toast.error(errorMessage);
      console.error('Erro ao carregar produtos:', err);
    } finally {
      setLoading(false);
    }
  }, [currentPage, filters]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const deleteProduct = async (id: number) => {
    try {
      await api.delete(`/produtos/${id}`);
      
      toast.success('Produto excluído com sucesso');
      fetchProducts();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Erro ao excluir produto';
      toast.error(errorMessage);
      throw err;
    }
  };

  const toggleProductStatus = async (id: number, currentStatus: string) => {
    try {
      const newStatus = currentStatus === 'ativo' ? 'inativo' : 'ativo';
      
      await api.patch(`/produtos/${id}`, { status: newStatus });
      
      toast.success(`Produto ${newStatus === 'ativo' ? 'ativado' : 'inativado'} com sucesso`);
      fetchProducts();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Erro ao atualizar status';
      toast.error(errorMessage);
      throw err;
    }
  };

  return {
    products,
    loading,
    error,
    currentPage,
    totalPages,
    total,
    filters,
    setFilters,
    setCurrentPage,
    refetch: fetchProducts,
    deleteProduct,
    toggleProductStatus
  };
};
