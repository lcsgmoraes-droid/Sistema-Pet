/**
 * SPRINT 7 - Exportações do Módulo Produtos
 * Atualizado: Passo 1 (Listagem) + Passo 2 (Formulário) + Passo 3 (Edição)
 */

// Páginas
export { default as ProdutosPage } from './ProdutosPage';
export { default as ProdutoEditPage } from './ProdutoEditPage';

// Componentes
export { ProductFiltersComponent } from './components/ProductFilters';
export { ProductTableComponent } from './components/ProductTable';
export { default as ProdutoForm } from './components/ProdutoForm';

// Hooks
export { useProducts } from './hooks/useProducts';

// Tipos
export type { 
  Product, 
  ProductFilters, 
  ProductListResponse,
  ProductFormData,
  CreateProductPayload
} from './types';
export { ProductType, ProductStatus } from './types';
