/**
 * SPRINT 7 - PASSO 1: Componente de Filtros de Produtos
 * Sistema ERP Pet Shop
 */

import React from 'react';
import type { ProductFilters } from '../types';
import '../styles/ProductFilters.css';

interface ProductFiltersProps {
  filters: ProductFilters;
  onFiltersChange: (filters: ProductFilters) => void;
  totalProducts: number;
}

export const ProductFiltersComponent: React.FC<ProductFiltersProps> = ({
  filters,
  onFiltersChange,
  totalProducts
}) => {
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({
      ...filters,
      busca: e.target.value
    });
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFiltersChange({
      ...filters,
      status: e.target.value as any
    });
  };

  const handleClearFilters = () => {
    onFiltersChange({
      busca: '',
      status: ''
    });
  };

  const hasActiveFilters = filters.busca || filters.status;

  return (
    <div className="product-filters">
      <div className="filter-row">
        <div className="search-input-wrapper">
          <svg 
            className="search-icon" 
            width="16" 
            height="16" 
            viewBox="0 0 16 16" 
            fill="none"
          >
            <path 
              d="M7 12.5C10.0376 12.5 12.5 10.0376 12.5 7C12.5 3.96243 10.0376 1.5 7 1.5C3.96243 1.5 1.5 3.96243 1.5 7C1.5 10.0376 3.96243 12.5 7 12.5Z" 
              stroke="currentColor" 
              strokeWidth="1.5" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            />
            <path 
              d="M14.5 14.5L11 11" 
              stroke="currentColor" 
              strokeWidth="1.5" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            />
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder="Buscar por nome ou SKU..."
            value={filters.busca}
            onChange={handleSearchChange}
          />
        </div>

        <div className="filter-controls">
          <select
            className="status-select"
            value={filters.status}
            onChange={handleStatusChange}
          >
            <option value="">Todos os status</option>
            <option value="ativo">Ativo</option>
            <option value="inativo">Inativo</option>
          </select>

          {hasActiveFilters && (
            <button 
              className="clear-filters-btn"
              onClick={handleClearFilters}
              type="button"
            >
              Limpar filtros
            </button>
          )}
        </div>
      </div>

      <div className="filter-info">
        <span className="product-count">
          {totalProducts} {totalProducts === 1 ? 'produto' : 'produtos'}
          {hasActiveFilters && ' encontrado(s)'}
        </span>
      </div>
    </div>
  );
};
