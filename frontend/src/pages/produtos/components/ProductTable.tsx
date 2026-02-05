/**
 * SPRINT 7 - PASSO 1: Componente de Tabela de Produtos
 * Sistema ERP Pet Shop
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import type { Product } from '../types';
import '../styles/ProductTable.css';

interface ProductTableProps {
  products: Product[];
  loading: boolean;
  error: string | null;
  onDelete: (id: number) => Promise<void>;
  onToggleStatus: (id: number, currentStatus: string) => Promise<void>;
}

export const ProductTableComponent: React.FC<ProductTableProps> = ({
  products,
  loading,
  error,
  onDelete,
  onToggleStatus
}) => {
  const navigate = useNavigate();

  const formatPrice = (price: number): string => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(price);
  };

  const getProductTypeBadge = (tipo: string) => {
    const badges = {
      simples: { label: 'Simples', className: 'badge-simple' },
      variacao: { label: 'Variação', className: 'badge-variation' },
      kit: { label: 'Kit', className: 'badge-kit' }
    };
    
    const badge = badges[tipo as keyof typeof badges] || { label: tipo, className: 'badge-default' };
    
    return (
      <span className={`product-type-badge ${badge.className}`}>
        {badge.label}
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    return (
      <span className={`status-badge ${status === 'ativo' ? 'status-active' : 'status-inactive'}`}>
        {status === 'ativo' ? 'Ativo' : 'Inativo'}
      </span>
    );
  };

  const handleEdit = (id: number) => {
    navigate(`/produtos/${id}/editar`);
  };

  const handleToggleStatus = async (product: Product) => {
    if (confirm(`Deseja ${product.status === 'ativo' ? 'inativar' : 'ativar'} o produto "${product.nome}"?`)) {
      await onToggleStatus(product.id, product.status);
    }
  };

  const handleDelete = async (product: Product) => {
    if (confirm(`Deseja realmente excluir o produto "${product.nome}"? Esta ação não pode ser desfeita.`)) {
      await onDelete(product.id);
    }
  };

  // Estado: Carregando
  if (loading) {
    return (
      <div className="table-state-container">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Carregando produtos...</p>
        </div>
      </div>
    );
  }

  // Estado: Erro
  if (error) {
    return (
      <div className="table-state-container">
        <div className="error-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" strokeWidth="2"/>
            <line x1="12" y1="8" x2="12" y2="12" strokeWidth="2" strokeLinecap="round"/>
            <line x1="12" y1="16" x2="12.01" y2="16" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          <h3>Erro ao carregar produtos</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  // Estado: Lista vazia
  if (!products || products.length === 0) {
    return (
      <div className="table-state-container">
        <div className="empty-state">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" strokeWidth="2"/>
            <line x1="9" y1="9" x2="15" y2="15" strokeWidth="2" strokeLinecap="round"/>
            <line x1="15" y1="9" x2="9" y2="15" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          <h3>Nenhum produto encontrado</h3>
          <p>Comece cadastrando seu primeiro produto</p>
        </div>
      </div>
    );
  }

  // Estado: Tabela com dados
  return (
    <div className="table-container">
      <table className="product-table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>SKU</th>
            <th>Tipo</th>
            <th className="text-right">Preço</th>
            <th className="text-right">Estoque</th>
            <th>Status</th>
            <th className="text-center">Ações</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.id}>
              <td className="product-name-cell">
                <div className="product-name-wrapper">
                  <span className="product-name">{product.nome}</span>
                  {product.marca && (
                    <span className="product-brand">{product.marca}</span>
                  )}
                </div>
              </td>
              <td className="sku-cell">
                <code className="sku-code">{product.sku}</code>
              </td>
              <td>{getProductTypeBadge(product.tipo)}</td>
              <td className="text-right price-cell">
                {formatPrice(product.preco)}
              </td>
              <td className="text-right stock-cell">
                <span className={`stock-value ${product.estoque <= 5 ? 'stock-low' : ''}`}>
                  {product.estoque}
                </span>
              </td>
              <td>{getStatusBadge(product.status)}</td>
              <td className="text-center">
                <div className="action-buttons">
                  <button
                    className="action-btn action-btn-edit"
                    onClick={() => handleEdit(product.id)}
                    title="Editar produto"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                  <button
                    className={`action-btn ${product.status === 'ativo' ? 'action-btn-inactive' : 'action-btn-active'}`}
                    onClick={() => handleToggleStatus(product)}
                    title={product.status === 'ativo' ? 'Inativar' : 'Ativar'}
                  >
                    {product.status === 'ativo' ? (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                        <line x1="15" y1="9" x2="9" y2="15" strokeWidth="2" strokeLinecap="round"/>
                        <line x1="9" y1="9" x2="15" y2="15" strokeWidth="2" strokeLinecap="round"/>
                      </svg>
                    ) : (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        <polyline points="22 4 12 14.01 9 11.01" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
