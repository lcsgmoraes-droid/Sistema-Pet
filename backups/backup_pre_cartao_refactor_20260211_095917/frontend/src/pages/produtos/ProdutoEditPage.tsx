/**
 * SPRINT 7 - PASSO 3: Página de Edição de Produto
 * Sistema ERP Pet Shop
 * 
 * Wrapper para ProdutoForm em modo de edição
 * Busca o produto por ID e passa para o formulário
 */

import React from 'react';
import { useParams } from 'react-router-dom';
import { ProdutoForm } from './components/ProdutoForm';

export const ProdutoEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const productId = id ? parseInt(id, 10) : undefined;

  if (!productId || isNaN(productId)) {
    return (
      <div className="produto-form-page">
        <div className="error-container">
          <h2>Produto não encontrado</h2>
          <p>ID de produto inválido</p>
        </div>
      </div>
    );
  }

  return <ProdutoForm mode="edit" productId={productId} />;
};

export default ProdutoEditPage;
