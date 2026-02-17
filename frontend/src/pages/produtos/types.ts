/**
 * SPRINT 7 - PASSO 1: Tipos TypeScript para Módulo de Produtos
 * Sistema ERP Pet Shop - Aba Produtos
 */

export enum ProductType {
  SIMPLE = 'simples',
  VARIATION = 'variacao',
  KIT = 'kit'
}

export enum ProductStatus {
  ACTIVE = 'ativo',
  INACTIVE = 'inativo'
}

export interface Product {
  id: number;
  nome: string;
  sku: string;
  tipo: ProductType;
  preco_custo?: number;
  markup?: number;
  preco: number;
  preco_promocional?: number;
  estoque: number;
  status: ProductStatus;
  marca?: string;
  categoria?: string;
  descricao_completa?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProductFilters {
  busca: string;
  status: ProductStatus | '';
}

export interface ProductListResponse {
  produtos: Product[];
  total: number;
  pagina: number;
  total_paginas: number;
}

export interface ApiError {
  message: string;
  detail?: string;
}

/**
 * SPRINT 7 - PASSO 2: Tipos para Formulário de Criação
 */

export interface ProductFormData {
  nome: string;
  sku: string;
  tipo: ProductType;
  preco_custo: string;  // String para controlar formatação no input
  markup: string;       // String para cálculo automático
  preco: string;        // Preço de venda
  preco_promocional: string;
  estoque: string;
  status: ProductStatus;
  marca?: string;
  categoria?: string;
  descricao_completa?: string;
  e_produto_fisico: boolean;
}

export interface CreateProductPayload {
  nome: string;
  sku: string;
  tipo: ProductType;
  preco_custo: number;
  preco: number;        // Preço de venda
  preco_promocional?: number;
  estoque: number;
  status: ProductStatus;
  marca?: string;
  categoria?: string;
  descricao_completa?: string;
  e_produto_fisico: boolean;
}
