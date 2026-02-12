/**
 * SPRINT 7 - PASSO 2 & 3: Formulário de Produto (Criação e Edição)
 * Sistema ERP Pet Shop - Apenas Produtos SIMPLES
 * 
 * Features:
 * - Criação de produto simples
 * - Edição de produto simples
 * - Validações de campo
 * - Feedback visual
 * - Preparado para variação/kit (futuro)
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../../api';
import toast from 'react-hot-toast';
import { ProductType, ProductStatus, Product } from '../types';
import type { ProductFormData, CreateProductPayload } from '../types';
import '../styles/ProdutoForm.css';

interface ProdutoFormProps {
  mode?: 'create' | 'edit';
  productId?: number;
  initialData?: Product;
}

export const ProdutoForm: React.FC<ProdutoFormProps> = ({
  mode = 'create',
  productId,
  initialData
}) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loadingProduct, setLoadingProduct] = useState(mode === 'edit');
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Estado do formulário
  const [formData, setFormData] = useState<ProductFormData>({
    nome: '',
    sku: '',
    tipo: ProductType.SIMPLE,
    preco_custo: '',
    markup: '',
    preco: '',
    preco_promocional: '',
    estoque: '0',
    status: ProductStatus.ACTIVE,
    marca: '',
    categoria: '',
    descricao: '',
    e_produto_fisico: true
  });

  // Carregar dados do produto em modo de edição
  useEffect(() => {
    if (mode === 'edit') {
      if (initialData) {
        // Se initialData foi passado, usar diretamente
        loadProductData(initialData);
        setLoadingProduct(false);
      } else if (productId) {
        // Senão, buscar da API
        fetchProduct(productId);
      }
    }
  }, [mode, productId, initialData]);

  // Buscar produto da API
  const fetchProduct = async (id: number) => {
    try {
      setLoadingProduct(true);
      const response = await api.get(`/produtos/${id}`);
      loadProductData(response.data);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Erro ao carregar produto';
      toast.error(errorMessage);
      navigate('/produtos');
    } finally {
      setLoadingProduct(false);
    }
  };

  // Carregar dados do produto no formulário
  const loadProductData = (product: Product) => {
    setFormData({
      nome: product.nome,
      sku: product.sku,
      tipo: product.tipo,
      preco: product.preco.toString().replace('.', ','),
      estoque: product.estoque.toString(),
      status: product.status,
      marca: product.marca || '',
      categoria: product.categoria || '',
      descricao: '',  // Backend pode não ter esse campo
      e_produto_fisico: product.estoque > 0 || true  // Inferir do estoque
    });
  };

  // Atualizar campo
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({ ...prev, [name]: checked }));
    } else {
      setFormData(prev => {
        const newData = { ...prev, [name]: value };
        
        // Calcular markup automaticamente quando alterar preço de custo ou preço de venda
        if (name === 'preco_custo' || name === 'preco') {
          const custo = parseFloat((name === 'preco_custo' ? value : prev.preco_custo).replace(',', '.'));
          const venda = parseFloat((name === 'preco' ? value : prev.preco).replace(',', '.'));
          
          if (custo > 0 && venda > 0) {
            const markupCalc = ((venda - custo) / custo * 100).toFixed(2);
            newData.markup = markupCalc.replace('.', ',');
          }
        }
        
        // Calcular preço de venda quando alterar markup
        if (name === 'markup' && prev.preco_custo) {
          const custo = parseFloat(prev.preco_custo.replace(',', '.'));
          const markupNum = parseFloat(value.replace(',', '.'));
          
          if (custo > 0 && !isNaN(markupNum)) {
            const vendaCalc = (custo * (1 + markupNum / 100)).toFixed(2);
            newData.preco = vendaCalc.replace('.', ',');
          }
        }
        
        return newData;
      });
    }

    // Limpar erro do campo ao editar
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  // Validações
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Nome obrigatório
    if (!formData.nome.trim()) {
      newErrors.nome = 'Nome é obrigatório';
    }

    // SKU obrigatório
    if (!formData.sku.trim()) {
      newErrors.sku = 'SKU é obrigatório';
    }

    // Preço obrigatório e válido
    if (!formData.preco.trim()) {
      newErrors.preco = 'Preço é obrigatório';
    } else {
      const precoNum = parseFloat(formData.preco.replace(',', '.'));
      if (isNaN(precoNum) || precoNum < 0) {
        newErrors.preco = 'Preço deve ser um número válido';
      }
    }

    // Estoque obrigatório se produto físico
    if (formData.e_produto_fisico) {
      if (!formData.estoque.trim()) {
        newErrors.estoque = 'Estoque é obrigatório para produtos físicos';
      } else {
        const estoqueNum = parseInt(formData.estoque, 10);
        if (isNaN(estoqueNum) || estoqueNum < 0) {
          newErrors.estoque = 'Estoque deve ser um número válido';
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Submeter formulário
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validar
    if (!validate()) {
      toast.error('Preencha todos os campos obrigatórios');
      return;
    }

    // Preparar payload
    const payload: CreateProductPayload = {
      nome: formData.nome.trim(),
      sku: formData.sku.trim().toUpperCase(),
      tipo: formData.tipo,
      preco_custo: parseFloat(formData.preco_custo.replace(',', '.')),
      preco: parseFloat(formData.preco.replace(',', '.')),
      estoque: formData.tipo === ProductType.SIMPLE ? parseInt(formData.estoque, 10) : 
                formData.e_produto_fisico ? parseInt(formData.estoque, 10) : 0,
      status: formData.status,
      e_produto_fisico: formData.tipo === ProductType.SIMPLE ? true : formData.e_produto_fisico,
      ...(formData.preco_promocional && { preco_promocional: parseFloat(formData.preco_promocional.replace(',', '.')) }),
      ...(formData.marca && { marca: formData.marca.trim() }),
      ...(formData.categoria && { categoria: formData.categoria.trim() }),
      ...(formData.descricao && { descricao: formData.descricao.trim() })
    };

    try {
      setLoading(true);

      if (mode === 'edit' && productId) {
        // Modo de edição: PATCH
        await api.patch(`/produtos/${productId}`, payload);
        toast.success('Produto atualizado com sucesso!');
      } else {
        // Modo de criação: POST
        await api.post('/produtos', payload);
        toast.success('Produto criado com sucesso!');
      }

      navigate('/produtos');
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 
        (mode === 'edit' ? 'Erro ao atualizar produto' : 'Erro ao criar produto');
      toast.error(errorMessage);
      console.error(`Erro ao ${mode === 'edit' ? 'atualizar' : 'criar'} produto:`, err);
    } finally {
      setLoading(false);
    }
  };

  // Cancelar
  const handleCancel = () => {
    navigate('/produtos');
  };

  // Verificar se tipo não é simples
  const isNotSimpleType = formData.tipo !== ProductType.SIMPLE;

  // Loading inicial (carregando produto)
  if (loadingProduct) {
    return (
      <div className="produto-form-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Carregando produto...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="produto-form-page">
      {/* Header */}
      <div className="form-header">
        <div className="header-title-section">
          <h1 className="form-title">
            {mode === 'edit' ? 'Editar Produto' : 'Novo Produto'}
          </h1>
          <p className="form-subtitle">
            {mode === 'edit'
              ? 'Atualize as informações do produto'
              : 'Preencha as informações abaixo para cadastrar um novo produto'}
          </p>
        </div>
      </div>

      {/* Formulário */}
      <form className="produto-form" onSubmit={handleSubmit}>
        {/* Card Principal */}
        <div className="form-card">
          <div className="form-section">
            <h2 className="section-title">Informações Básicas</h2>

            <div className="form-row">
              {/* Nome */}
              <div className="form-group">
                <label htmlFor="nome" className="form-label required">
                  Nome do Produto
                </label>
                <input
                  type="text"
                  id="nome"
                  name="nome"
                  className={`form-input ${errors.nome ? 'input-error' : ''}`}
                  value={formData.nome}
                  onChange={handleChange}
                  placeholder="Ex: Ração Premium para Cães"
                  disabled={loading}
                />
                {errors.nome && <span className="error-message">{errors.nome}</span>}
              </div>

              {/* SKU */}
              <div className="form-group">
                <label htmlFor="sku" className="form-label required">
                  SKU
                </label>
                <input
                  type="text"
                  id="sku"
                  name="sku"
                  className={`form-input ${errors.sku ? 'input-error' : ''}`}
                  value={formData.sku}
                  onChange={handleChange}
                  placeholder="Ex: RAC-001"
                  disabled={loading}
                  style={{ textTransform: 'uppercase' }}
                />
                {errors.sku && <span className="error-message">{errors.sku}</span>}
              </div>
            </div>

            <div className="form-row">
              {/* Tipo */}
              <div className="form-group">
                <label htmlFor="tipo" className="form-label required">
                  Tipo do Produto
                </label>
                <select
                  id="tipo"
                  name="tipo"
                  className="form-select"
                  value={formData.tipo}
                  onChange={handleChange}
                  disabled={loading}
                >
                  <option value={ProductType.SIMPLE}>Simples</option>
                  <option value={ProductType.VARIATION} disabled>
                    Com Variação (em breve)
                  </option>
                  <option value={ProductType.KIT} disabled>
                    Kit (em breve)
                  </option>
                </select>
                {isNotSimpleType && (
                  <span className="info-message">
                    Produtos com variação e kits serão implementados em breve
                  </span>
                )}
              </div>

              {/* Status */}
              <div className="form-group">
                <label htmlFor="status" className="form-label required">
                  Status
                </label>
                <select
                  id="status"
                  name="status"
                  className="form-select"
                  value={formData.status}
                  onChange={handleChange}
                  disabled={loading}
                >
                  <option value={ProductStatus.ACTIVE}>Ativo</option>
                  <option value={ProductStatus.INACTIVE}>Inativo</option>
                </select>
              </div>
            </div>

            {/* Checkbox Produto Físico - APENAS PARA KIT */}
            {formData.tipo === ProductType.KIT && (
              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="e_produto_fisico"
                    checked={formData.e_produto_fisico}
                    onChange={handleChange}
                    disabled={loading}
                    className="form-checkbox"
                  />
                  <span className="checkbox-text">
                    Este kit possui estoque físico
                  </span>
                </label>
                <p className="field-hint">
                  {formData.e_produto_fisico
                    ? 'Estoque do kit será controlado (não depende dos componentes)'
                    : 'Estoque virtual (depende do estoque dos componentes)'}
                </p>
              </div>
            )}

            {/* Produto simples sempre tem estoque físico */}
            {formData.tipo === ProductType.SIMPLE && (
              <div className="form-group">
                <p className="field-hint" style={{ marginTop: '8px', color: '#6b7280' }}>
                  ℹ️ Produtos simples sempre possuem estoque físico controlado
                </p>
              </div>
            )}
          </div>

          <div className="form-divider"></div>

          <div className="form-section">
            <h2 className="section-title">Precificação e Estoque</h2>

            <div className="form-row">
              {/* Preço de Custo */}
              <div className="form-group">
                <label htmlFor="preco_custo" className="form-label">
                  Preço de Custo
                </label>
                <div className="input-with-prefix">
                  <span className="input-prefix">R$</span>
                  <input
                    type="text"
                    id="preco_custo"
                    name="preco_custo"
                    className="form-input input-with-prefix-field"
                    value={formData.preco_custo}
                    onChange={handleChange}
                    placeholder="0,00"
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Markup */}
              <div className="form-group">
                <label htmlFor="markup" className="form-label">
                  Markup (%)
                </label>
                <div className="input-with-prefix">
                  <input
                    type="text"
                    id="markup"
                    name="markup"
                    className="form-input"
                    value={formData.markup}
                    onChange={handleChange}
                    placeholder="0,00"
                    disabled={loading}
                  />
                  <span className="input-suffix">%</span>
                </div>
              </div>
            </div>

            <div className="form-row">
              {/* Preço de Venda */}
              <div className="form-group">
                <label htmlFor="preco" className="form-label required">
                  Preço de Venda
                </label>
                <div className="input-with-prefix">
                  <span className="input-prefix">R$</span>
                  <input
                    type="text"
                    id="preco"
                    name="preco"
                    className={`form-input input-with-prefix-field ${
                      errors.preco ? 'input-error' : ''
                    }`}
                    value={formData.preco}
                    onChange={handleChange}
                    placeholder="0,00"
                    disabled={loading}
                  />
                </div>
                {errors.preco && <span className="error-message">{errors.preco}</span>}
              </div>

              {/* Preço Promocional */}
              <div className="form-group">
                <label htmlFor="preco_promocional" className="form-label">
                  Preço Promocional
                </label>
                <div className="input-with-prefix">
                  <span className="input-prefix">R$</span>
                  <input
                    type="text"
                    id="preco_promocional"
                    name="preco_promocional"
                    className="form-input input-with-prefix-field"
                    value={formData.preco_promocional}
                    onChange={handleChange}
                    placeholder="0,00"
                    disabled={loading}
                  />
                </div>
              </div>
            </div>

            <div className="form-row">
              {/* Estoque - Mostrar apenas se for produto simples OU kit físico */}
              {(formData.tipo === ProductType.SIMPLE || 
                (formData.tipo === ProductType.KIT && formData.e_produto_fisico)) && (
                <div className="form-group">
                  <label htmlFor="estoque" className="form-label required">
                    Estoque Inicial
                  </label>
                  <input
                    type="number"
                    id="estoque"
                    name="estoque"
                    className={`form-input ${errors.estoque ? 'input-error' : ''}`}
                    value={formData.estoque}
                    onChange={handleChange}
                    placeholder="0"
                    min="0"
                    disabled={loading}
                  />
                  {errors.estoque && (
                    <span className="error-message">{errors.estoque}</span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="form-divider"></div>

          <div className="form-section">
            <h2 className="section-title">Informações Adicionais (Opcional)</h2>

            <div className="form-row">
              {/* Marca */}
              <div className="form-group">
                <label htmlFor="marca" className="form-label">
                  Marca
                </label>
                <input
                  type="text"
                  id="marca"
                  name="marca"
                  className="form-input"
                  value={formData.marca}
                  onChange={handleChange}
                  placeholder="Ex: Royal Canin"
                  disabled={loading}
                />
              </div>

              {/* Categoria */}
              <div className="form-group">
                <label htmlFor="categoria" className="form-label">
                  Categoria
                </label>
                <input
                  type="text"
                  id="categoria"
                  name="categoria"
                  className="form-input"
                  value={formData.categoria}
                  onChange={handleChange}
                  placeholder="Ex: Alimentação"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Descrição */}
            <div className="form-group">
              <label htmlFor="descricao" className="form-label">
                Descrição
              </label>
              <textarea
                id="descricao"
                name="descricao"
                className="form-textarea"
                value={formData.descricao}
                onChange={handleChange}
                placeholder="Descreva as características do produto..."
                rows={4}
                disabled={loading}
              />
            </div>
          </div>
        </div>

        {/* Footer com Botões */}
        <div className="form-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleCancel}
            disabled={loading}
          >
            Cancelar
          </button>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner-small"></span>
                {mode === 'edit' ? 'Salvando...' : 'Salvando...'}
              </>
            ) : (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path
                    d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <polyline
                    points="17 21 17 13 7 13 7 21"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <polyline
                    points="7 3 7 8 15 8"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                {mode === 'edit' ? 'Salvar Alterações' : 'Salvar Produto'}
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ProdutoForm;
