/**
 * SPRINT 7 - PASSO 1: Página Principal de Produtos
 * Sistema ERP Pet Shop - Aba Produtos
 * 
 * Features:
 * - Listagem de produtos
 * - Busca por nome/SKU
 * - Filtro por status
 * - Paginação
 * - Estados visuais (loading, empty, error)
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useProducts } from './hooks/useProducts';
import { ProductFiltersComponent } from './components/ProductFilters';
import { ProductTableComponent } from './components/ProductTable';
import './styles/ProdutosPage.css';

export const ProdutosPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    products,
    loading,
    error,
    currentPage,
    totalPages,
    total,
    filters,
    setFilters,
    setCurrentPage,
    deleteProduct,
    toggleProductStatus
  } = useProducts();

  const handleNewProduct = () => {
    navigate('/produtos/novo');
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="produtos-page">
      {/* Header */}
      <div className="page-header">
        <div className="header-content">
          <div className="header-title-section">
            <h1 className="page-title">Produtos</h1>
            <p className="page-subtitle">
              Gerencie o catálogo de produtos da sua loja
            </p>
          </div>
          <button 
            className="btn-primary"
            onClick={handleNewProduct}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <line x1="12" y1="5" x2="12" y2="19" strokeWidth="2" strokeLinecap="round"/>
              <line x1="5" y1="12" x2="19" y2="12" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Novo Produto
          </button>
        </div>
      </div>

      {/* Filtros */}
      <ProductFiltersComponent
        filters={filters}
        onFiltersChange={setFilters}
        totalProducts={total}
      />

      {/* Tabela */}
      <ProductTableComponent
        products={products}
        loading={loading}
        error={error}
        onDelete={deleteProduct}
        onToggleStatus={toggleProductStatus}
      />

      {/* Paginação */}
      {!loading && !error && products.length > 0 && totalPages > 1 && (
        <div className="pagination-container">
          <div className="pagination">
            <button
              className="pagination-btn"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polyline points="15 18 9 12 15 6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Anterior
            </button>

            <div className="pagination-info">
              <span className="current-page">Página {currentPage}</span>
              <span className="page-separator">de</span>
              <span className="total-pages">{totalPages}</span>
            </div>

            <button
              className="pagination-btn"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              Próxima
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polyline points="9 18 15 12 9 6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProdutosPage;
