/**
 * FormulÃ¡rio de Cadastro/EdiÃ§Ã£o de Produtos - Layout em Abas
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import ProdutosNovoFooterActions from '../components/produto/ProdutosNovoFooterActions';
import ProdutosNovoFornecedorModal from '../components/produto/ProdutosNovoFornecedorModal';
import ProdutosNovoHeader from '../components/produto/ProdutosNovoHeader';
import ProdutosNovoEntradaModal from '../components/produto/ProdutosNovoEntradaModal';
import ProdutosNovoLoteModal from '../components/produto/ProdutosNovoLoteModal';
import ProdutosNovoComposicaoTab from '../components/produto/ProdutosNovoComposicaoTab';
import ProdutosNovoRacaoTab from '../components/produto/ProdutosNovoRacaoTab';
import ProdutosNovoRecorrenciaTab from '../components/produto/ProdutosNovoRecorrenciaTab';
import ProdutosNovoTabs from '../components/produto/ProdutosNovoTabs';
import ProdutosNovoTributacaoTab from '../components/produto/ProdutosNovoTributacaoTab';
import ProdutosNovoVariacoesTab from '../components/produto/ProdutosNovoVariacoesTab';
import useProdutosNovoCarregamento from '../hooks/useProdutosNovoCarregamento';
import useProdutosNovoCodigos from '../hooks/useProdutosNovoCodigos';
import useProdutosNovoFornecedores from '../hooks/useProdutosNovoFornecedores';
import useProdutosNovoImagens from '../hooks/useProdutosNovoImagens';
import useProdutosNovoKit from '../hooks/useProdutosNovoKit';
import useProdutosNovoLotes from '../hooks/useProdutosNovoLotes';
import useProdutosNovoPredecessor from '../hooks/useProdutosNovoPredecessor';
import useProdutosNovoRacao from '../hooks/useProdutosNovoRacao';
import useProdutosNovoRecorrencia from '../hooks/useProdutosNovoRecorrencia';
import useProdutosNovoSubmit from '../hooks/useProdutosNovoSubmit';
import useProdutosNovoTributacao from '../hooks/useProdutosNovoTributacao';
import useProdutosNovoVariacoes from '../hooks/useProdutosNovoVariacoes';
import {
  calcularPrecoVenda,
  calcularMarkup,
  formatarMoeda,
  formatarData,
} from '../api/produtos';

// Função auxiliar para converter valores sem retornar NaN
const parseNumber = (valor) => {
  if (valor === '' || valor === null || valor === undefined) return 0;
  // Permite tanto vírgula quanto ponto como separador decimal
  const limpo = valor.toString().replace(/[^\d.,]/g, '');
  // Normaliza vírgula para ponto
  const normalizado = limpo.replace(',', '.');
  const numero = parseFloat(normalizado);
  return isNaN(numero) ? 0 : numero;
};

export default function ProdutosNovo() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const isEdicao = !!id;

  // Estado das abas
  const [abaAtiva, setAbaAtiva] = useState(1);

  // Estado do formulÃ¡rio
  const [formData, setFormData] = useState({
    // Aba 1: Características
    codigo: '',
    sku: '',
    nome: '',
    codigo_barras: '',
    categoria_id: '',
    marca_id: '',
    departamento_id: '',
    tipo: 'produto',
    unidade: 'UN',
    descricao: '',
    preco_custo: '',
    preco_venda: '',
    preco_promocional: '',
    data_inicio_promocao: '',
    data_fim_promocao: '',
    preco_ecommerce: '',
    preco_ecommerce_promo: '',
    preco_ecommerce_promo_inicio: '',
    preco_ecommerce_promo_fim: '',
    preco_app: '',
    preco_app_promo: '',
    preco_app_promo_inicio: '',
    preco_app_promo_fim: '',
    markup: '',
    
    // Sprint 2: Produtos com variação
    tipo_produto: 'SIMPLES', // SIMPLES, PAI (variação), KIT (composição), VARIACAO
    produto_pai_id: null,
    
    // Composição do Kit (VARIACAO também pode ser KIT)
    tipo_kit: null, // 'VIRTUAL' ou 'FISICO' (quando é kit)
    e_kit_fisico: false, // Se false, estoque é virtual (calculado)
    composicao_kit: [], // Array de {produto_id, produto_nome, quantidade}
    
    // Sistema Predecessor/Sucessor
    produto_predecessor_id: null,
    motivo_descontinuacao: '',
    
    // Aba 3: Estoque
    controle_lote: true,
    estoque_minimo: '',
    estoque_maximo: '',
    
    // Aba 5: Tributação (Fiscal V2)
    tributacao: {
      origem: null, // 'empresa_legado', 'produto_legado', 'produto_fiscal_v2', 'kit_fiscal_v2'
      herdado_da_empresa: false,
      origem_mercadoria: '0',
      ncm: '',
      cest: '',
      cfop: '',
      cst_icms: '',
      icms_aliquota: '',
      icms_st: false,
      pis_aliquota: '',
      cofins_aliquota: '',
    },
    // Campos legados (mantidos para fallback)
    origem: '0',
    ncm: '',
    cest: '',
    cfop: '',
    aliquota_icms: '',
    aliquota_pis: '',
    aliquota_cofins: '',
    
    // Aba 6: Recorrência (Fase 1)
    tem_recorrencia: false,
    tipo_recorrencia: 'monthly',
    intervalo_dias: '',
    numero_doses: '',
    observacoes_recorrencia: '',
    especie_compativel: 'both',
    
    // Aba 7: Ração - Calculadora (Fase 2)
    classificacao_racao: '',
    peso_embalagem: '',
    tabela_nutricional: '',
    tabela_consumo: '',
    categoria_racao: '',
    especies_indicadas: 'both',
    
    // Opções de Ração - Sistema Dinâmico
    linha_racao_id: '',
    porte_animal_id: '',
    fase_publico_id: '',
    tipo_tratamento_id: '',
    sabor_proteina_id: '',
    apresentacao_peso_id: '',
  });

  // Dados auxiliares
  const [categorias, setCategorias] = useState([]);
  const [categoriasHierarquicas, setCategoriasHierarquicas] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);
  const [imagens, setImagens] = useState([]);
  const [clientes, setClientes] = useState([]);
  
  // Opções de Ração - Dados dinâmicos das APIs
  const [opcoesLinhas, setOpcoesLinhas] = useState([]);
  const [opcoesPortes, setOpcoesPortes] = useState([]);
  const [opcoesFases, setOpcoesFases] = useState([]);
  const [opcoesTratamentos, setOpcoesTratamentos] = useState([]);
  const [opcoesSabores, setOpcoesSabores] = useState([]);
  const [opcoesApresentacoes, setOpcoesApresentacoes] = useState([]);
  
  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);
  
  // Estados para controlar edição de campos monetários
  const [camposEmEdicao, setCamposEmEdicao] = useState({
    preco_custo: false,
    markup: false,
    preco_venda: false,
    preco_promocional: false,
  });

  const handleChange = (campo, valor) => {
    setFormData(prev => {
      const novosDados = { ...prev, [campo]: valor };

      if (campo === 'sku' || campo === 'codigo') {
        const skuNormalizado = (valor || '').toString().toUpperCase();
        novosDados.sku = skuNormalizado;
        novosDados.codigo = skuNormalizado;
      }
      
      // Calcular markup automaticamente quando mudar preço
      if (campo === 'preco_custo' || campo === 'preco_venda') {
        const custo = parseNumber(campo === 'preco_custo' ? valor : prev.preco_custo);
        const venda = parseNumber(campo === 'preco_venda' ? valor : prev.preco_venda);
        
        if (custo && venda && custo > 0) {
          const markup = calcularMarkup(custo, venda);
          novosDados.markup = markup.toFixed(2);
        }
      }
      
      // Calcular preço de venda pelo markup
      if (campo === 'markup') {
        const custo = parseNumber(prev.preco_custo);
        const markupVal = parseNumber(valor);
        
        if (custo && custo > 0 && markupVal >= 0) {
          const venda = calcularPrecoVenda(custo, markupVal);
          novosDados.preco_venda = venda.toFixed(2);
        }
      }
      
      return novosDados;
    });
  };

  const {
    mostrarBuscaPredecessor,
    produtosBusca,
    buscaPredecessor,
    predecessorSelecionado,
    predecessorInfo,
    sucessorInfo,
    setPredecessorInfo,
    setSucessorInfo,
    handleToggleBuscaPredecessor,
    handleBuscaPredecessorChange,
    handleSelecionarPredecessor,
    handleRemoverPredecessor,
  } = useProdutosNovoPredecessor({
    handleChange,
  });

  const {
    lotes,
    setLotes,
    modalEntrada,
    setModalEntrada,
    entradaData,
    setEntradaData,
    modalEdicaoLote,
    setModalEdicaoLote,
    loteEmEdicao,
    setLoteEmEdicao,
    handleEntradaEstoque,
    handleEditarLote,
    handleSalvarEdicaoLote,
    handleExcluirLote,
  } = useProdutosNovoLotes({ id });

  const {
    fornecedores,
    setFornecedores,
    modalFornecedor,
    setModalFornecedor,
    fornecedorEdit,
    fornecedorData,
    setFornecedorData,
    handleAddFornecedor,
    handleEditFornecedor,
    handleSaveFornecedor,
    handleDeleteFornecedor,
  } = useProdutosNovoFornecedores({ id });

  const { salvarFiscal } = useProdutosNovoCarregamento({
    id,
    isEdicao,
    formData,
    setCategorias,
    setCategoriasHierarquicas,
    setMarcas,
    setDepartamentos,
    setClientes,
    setOpcoesLinhas,
    setOpcoesPortes,
    setOpcoesFases,
    setOpcoesTratamentos,
    setOpcoesSabores,
    setOpcoesApresentacoes,
    setLoading,
    setFormData,
    setPredecessorInfo,
    setSucessorInfo,
    setImagens,
    setLotes,
    setFornecedores,
  });

  const { handleChangeTributacao, handlePersonalizarFiscal } = useProdutosNovoTributacao({
    setFormData,
  });

  const {
    uploadingImage,
    handleUploadImagem,
    handleDeleteImagem,
    handleSetPrincipal,
  } = useProdutosNovoImagens({
    id,
    setImagens,
  });

  const {
    produtosDisponiveis,
    produtoKitSelecionado,
    setProdutoKitSelecionado,
    quantidadeKit,
    setQuantidadeKit,
    estoqueVirtualKit,
    buscaComponente,
    setBuscaComponente,
    dropdownComponenteVisivel,
    setDropdownComponenteVisivel,
    adicionarProdutoKit,
    removerProdutoKit,
  } = useProdutosNovoKit({
    abaAtiva,
    formData,
    setFormData,
  });

  const {
    variacoes,
    novaVariacao,
    setNovaVariacao,
    mostrarFormVariacao,
    handleToggleFormVariacao,
    handleCancelarVariacao,
    handleSalvarVariacao,
    handleExcluirVariacao,
  } = useProdutosNovoVariacoes({
    id,
    isEdicao,
    abaAtiva,
    formData,
    navigate,
  });

  const { handleTipoRecorrenciaChange } = useProdutosNovoRecorrencia({
    handleChange,
  });

  const {
    handleClassificacaoRacaoChange,
    handleFasePublicoChange,
    handleApresentacaoPesoChange,
  } = useProdutosNovoRacao({
    opcoesApresentacoes,
    opcoesFases,
    setFormData,
  });

  const { handleSubmit } = useProdutosNovoSubmit({
    id,
    isEdicao,
    formData,
    navigate,
    salvarFiscal,
    setSalvando,
  });

  const { handleGerarSKU, handleGerarCodigoBarras } = useProdutosNovoCodigos({
    formData,
    setFormData,
  });

  const handleVoltar = () => {
    if (formData.tipo_produto === 'VARIACAO' && formData.produto_pai_id) {
      navigate(`/produtos/${formData.produto_pai_id}/editar?aba=8`);
      return;
    }

    navigate('/produtos');
  };
  
  // Auto-detectar "ração" no nome do produto
  useEffect(() => {
    if (!isEdicao && formData.nome) {
      const nomeMinusculo = formData.nome.toLowerCase();
      const isRacao = nomeMinusculo.includes('racao') || nomeMinusculo.includes('ração');
      
      if (isRacao && formData.classificacao_racao !== 'sim') {
        setFormData(prev => ({
          ...prev,
          classificacao_racao: 'sim'
        }));
      }
    }
  }, [formData.nome, isEdicao, formData.classificacao_racao]);
  
  // Detectar parâmetro de aba na URL (após carregar o produto)
  useEffect(() => {
    if (!loading && isEdicao) {
      const abaParam = searchParams.get('aba');
      if (abaParam) {
        setAbaAtiva(parseInt(abaParam, 10));
      }
    }
  }, [loading, searchParams, isEdicao]);
  
  // 🛡️ PROTEÇÃO: Se for VARIACAO e estiver na aba 8, voltar para aba 1
  useEffect(() => {
    if (isEdicao && formData.tipo_produto === 'VARIACAO' && abaAtiva === 8) {
      setAbaAtiva(1);
    }
  }, [formData.tipo_produto, abaAtiva, isEdicao]);

  if (loading) {
    return (
      <div className="p-6 flex justify-center items-center h-96">
        <div className="text-gray-600">Carregando produto...</div>
      </div>
    );
  }

  // Proteção: Se é edição mas o formData ainda não foi carregado
  if (isEdicao && !formData.nome) {
    return (
      <div className="p-6 flex justify-center items-center h-96">
        <div className="text-gray-600">Carregando dados...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <ProdutosNovoHeader formData={formData} isEdicao={isEdicao} onVoltar={handleVoltar} />

      <ProdutosNovoTabs
        abaAtiva={abaAtiva}
        onChangeAba={setAbaAtiva}
        tipoProduto={formData.tipo_produto}
        tipoKit={formData.tipo_kit}
      />

      {/* 🔗 Banner: Produto é continuação de outro (Edit Mode) */}
      {isEdicao && predecessorInfo && (
        <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 p-5 rounded-lg shadow-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <svg className="w-7 h-7 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  🔗 Este produto é continuação de outro
                </h3>
              </div>
              <p className="text-sm text-gray-700 mb-3">
                Este produto substitui:{' '}
                <button
                  type="button"
                  onClick={() => navigate(`/produtos/${predecessorInfo.id}/editar`)}
                  className="font-bold text-blue-700 hover:text-blue-900 hover:underline"
                >
                  {predecessorInfo.codigo} - {predecessorInfo.nome}
                </button>
              </p>
              {predecessorInfo.motivo_descontinuacao && (
                <div className="bg-white/70 rounded-md px-3 py-2 text-sm">
                  <span className="font-medium text-gray-700">Motivo da substituição:</span>{' '}
                  <span className="text-gray-900">{predecessorInfo.motivo_descontinuacao}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ⚠️ Banner: Produto foi descontinuado (Edit Mode) */}
      {isEdicao && sucessorInfo && (
        <div className="mb-6 bg-gradient-to-r from-red-50 to-orange-50 border-l-4 border-red-500 p-5 rounded-lg shadow-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <svg className="w-7 h-7 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  ⚠️ Este produto foi descontinuado
                </h3>
              </div>
              <p className="text-sm text-gray-700 mb-3">
                Descontinuado em{' '}
                <span className="font-semibold">
                  {new Date(sucessorInfo.data_descontinuacao).toLocaleDateString('pt-BR')}
                </span>
              </p>
              <p className="text-sm text-gray-700 mb-3">
                Substituído por:{' '}
                <button
                  type="button"
                  onClick={() => navigate(`/produtos/${sucessorInfo.id}/editar`)}
                  className="font-bold text-red-700 hover:text-red-900 hover:underline"
                >
                  {sucessorInfo.codigo} - {sucessorInfo.nome}
                </button>
              </p>
              {sucessorInfo.motivo_descontinuacao && (
                <div className="bg-white/70 rounded-md px-3 py-2 text-sm">
                  <span className="font-medium text-gray-700">Motivo:</span>{' '}
                  <span className="text-gray-900">{sucessorInfo.motivo_descontinuacao}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* FormulÃ¡rio */}
      <form onSubmit={handleSubmit}>
        <div className="bg-white rounded-lg shadow-sm p-6">
          
          {/* ABA 1: CARACTERÃSTICAS */}
          {abaAtiva === 1 && (
            <div className="space-y-6">
              {/* Linha 1: Códigos */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    SKU *
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={formData.sku}
                      onChange={(e) => handleChange('sku', e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Ex: PROD0001"
                    />
                    <button
                      type="button"
                      onClick={handleGerarSKU}
                      className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm"
                    >
                      Gerar
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    Esse valor é salvo como o SKU oficial do produto.
                    {formData.codigo ? ` Atual: ${formData.codigo}` : ''}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Código de Barras
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={formData.codigo_barras}
                      onChange={(e) => handleChange('codigo_barras', e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="EAN-13"
                    />
                    <button
                      type="button"
                      onClick={handleGerarCodigoBarras}
                      className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm"
                    >
                      Gerar
                    </button>
                  </div>
                </div>
              </div>

              {/* Linha 2: Nome */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome do Produto *
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => handleChange('nome', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Ex: Ração Golden para Cães Adultos 15kg"
                  required
                />
              </div>

              {/* Linha 3: Classificação */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tipo
                  </label>
                  <select
                    value={formData.tipo}
                    onChange={(e) => handleChange('tipo', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="produto">Produto</option>
                    <option value="servico">Serviço</option>
                    <option value="ambos">Produto e Serviço</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Departamento
                  </label>
                  <select
                    value={formData.departamento_id}
                    onChange={(e) => handleChange('departamento_id', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Selecione...</option>
                    {departamentos.map(dep => (
                      <option key={dep.id} value={dep.id}>{dep.nome}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Categoria
                  </label>
                  <select
                    value={formData.categoria_id}
                    onChange={(e) => handleChange('categoria_id', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Selecione...</option>
                    { categoriasHierarquicas.map(cat => (
                      <option key={cat.id} value={cat.id}>
                        {cat.nomeFormatado}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Marca
                  </label>
                  <select
                    value={formData.marca_id}
                    onChange={(e) => handleChange('marca_id', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Selecione...</option>
                    {marcas.map(marca => (
                      <option key={marca.id} value={marca.id}>{marca.nome}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Linha 4: Unidade e Descrição */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Unidade
                  </label>
                  <select
                    value={formData.unidade}
                    onChange={(e) => handleChange('unidade', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="UN">UN - Unidade</option>
                    <option value="KG">KG - Quilograma</option>
                    <option value="G">G - Grama</option>
                    <option value="L">L - Litro</option>
                    <option value="ML">ML - Mililitro</option>
                    <option value="M">M - Metro</option>
                    <option value="CX">CX - Caixa</option>
                    <option value="PCT">PCT - Pacote</option>
                  </select>
                </div>

                <div className="md:col-span-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Descrição
                  </label>
                  <textarea
                    value={formData.descricao}
                    onChange={(e) => handleChange('descricao', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows="2"
                    placeholder="Descrição detalhada do produto..."
                  />
                </div>
              </div>

              {/* Linha 5: Preços - Oculta quando for produto PAI */}
              {formData.tipo_produto !== 'PAI' && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Preço de Custo
                    </label>
                    <input
                      type="text"
                      value={
                        camposEmEdicao.preco_custo
                          ? (formData.preco_custo || '')
                          : (formData.preco_custo ? `R$ ${parseNumber(formData.preco_custo).toFixed(2).replace('.', ',')}` : 'R$ 0,00')
                      }
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
                        handleChange('preco_custo', value);
                      }}
                      onFocus={(e) => {
                        setCamposEmEdicao(prev => ({ ...prev, preco_custo: true }));
                        e.target.select();
                      }}
                      onBlur={(e) => {
                        setCamposEmEdicao(prev => ({ ...prev, preco_custo: false }));
                        const value = parseNumber(e.target.value);
                        handleChange('preco_custo', value > 0 ? value.toFixed(2) : '');
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="R$ 0,00"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Markup
                    </label>
                    <input
                      type="text"
                      value={
                        camposEmEdicao.markup
                          ? (formData.markup || '')
                          : (formData.markup ? `${parseNumber(formData.markup).toFixed(2).replace('.', ',')}%` : '0,00%')
                      }
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
                        handleChange('markup', value);
                      }}
                      onFocus={(e) => {
                        setCamposEmEdicao(prev => ({ ...prev, markup: true }));
                        e.target.select();
                      }}
                      onBlur={(e) => {
                        setCamposEmEdicao(prev => ({ ...prev, markup: false }));
                        const value = parseNumber(e.target.value);
                        handleChange('markup', value >= 0 ? value.toFixed(2) : '');
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="0,00%"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Preço de Venda *
                    </label>
                    <input
                      type="text"
                      value={
                        camposEmEdicao.preco_venda
                          ? (formData.preco_venda || '')
                          : (formData.preco_venda ? `R$ ${parseNumber(formData.preco_venda).toFixed(2).replace('.', ',')}` : 'R$ 0,00')
                      }
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
                        handleChange('preco_venda', value);
                      }}
                      onFocus={(e) => {
                        setCamposEmEdicao(prev => ({ ...prev, preco_venda: true }));
                        e.target.select();
                      }}
                      onBlur={(e) => {
                        setCamposEmEdicao(prev => ({ ...prev, preco_venda: false }));
                        const value = parseNumber(e.target.value);
                        handleChange('preco_venda', value > 0 ? value.toFixed(2) : '');
                      }}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="R$ 0,00"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Preço Promocional
                    </label>
                    <input
                      type="text"
                      value={
                        camposEmEdicao.preco_promocional
                          ? (formData.preco_promocional || '')
                          : (formData.preco_promocional ? `R$ ${parseNumber(formData.preco_promocional).toFixed(2).replace('.', ',')}` : 'R$ 0,00')
                      }
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
                        handleChange('preco_promocional', value);
                      }}
                      onFocus={(e) => {
                        setCamposEmEdicao(prev => ({ ...prev, preco_promocional: true }));
                        e.target.select();
                      }}
                      onBlur={(e) => {
                        setCamposEmEdicao(prev => ({ ...prev, preco_promocional: false }));
                        const value = parseNumber(e.target.value);
                        handleChange('preco_promocional', value > 0 ? value.toFixed(2) : '');
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="R$ 0,00"
                    />
                  </div>
                </div>
              )}

              {/* Linha 6: Validade do preço promocional base (ERP) */}
              {formData.tipo_produto !== 'PAI' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Início da Promoção (ERP)
                    </label>
                    <input
                      type="date"
                      value={formData.data_inicio_promocao}
                      onChange={(e) => handleChange('data_inicio_promocao', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Fim da Promoção (ERP)
                    </label>
                    <input
                      type="date"
                      value={formData.data_fim_promocao}
                      onChange={(e) => handleChange('data_fim_promocao', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
              )}

              {/* Linha 7: Preços por Canal (Ecommerce / App) */}
              {formData.tipo_produto !== 'PAI' && (
                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700">Preços por Canal (Ecommerce / App)</h3>
                    <p className="text-xs text-gray-500 mt-1">
                      Se deixar vazio, o sistema usa o preço de venda padrão.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <div className="text-xs font-bold text-purple-700 uppercase">Ecommerce</div>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.preco_ecommerce}
                        onChange={(e) => handleChange('preco_ecommerce', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        placeholder="Preço normal"
                      />
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.preco_ecommerce_promo}
                        onChange={(e) => handleChange('preco_ecommerce_promo', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        placeholder="Preço promocional"
                      />
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <input
                          type="datetime-local"
                          value={formData.preco_ecommerce_promo_inicio ? formData.preco_ecommerce_promo_inicio.toString().slice(0, 16) : ''}
                          onChange={(e) => handleChange('preco_ecommerce_promo_inicio', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        />
                        <input
                          type="datetime-local"
                          value={formData.preco_ecommerce_promo_fim ? formData.preco_ecommerce_promo_fim.toString().slice(0, 16) : ''}
                          onChange={(e) => handleChange('preco_ecommerce_promo_fim', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        />
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="text-xs font-bold text-green-700 uppercase">App Móvel</div>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.preco_app}
                        onChange={(e) => handleChange('preco_app', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                        placeholder="Preço normal"
                      />
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.preco_app_promo}
                        onChange={(e) => handleChange('preco_app_promo', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                        placeholder="Preço promocional"
                      />
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <input
                          type="datetime-local"
                          value={formData.preco_app_promo_inicio ? formData.preco_app_promo_inicio.toString().slice(0, 16) : ''}
                          onChange={(e) => handleChange('preco_app_promo_inicio', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                        />
                        <input
                          type="datetime-local"
                          value={formData.preco_app_promo_fim ? formData.preco_app_promo_fim.toString().slice(0, 16) : ''}
                          onChange={(e) => handleChange('preco_app_promo_fim', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* =========================================
                  SISTEMA PREDECESSOR/SUCESSOR
                  ========================================= */}
              {!isEdicao && (
                <div className="border-t pt-6 mt-6">
                  <div className="p-6 bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <h3 className="text-lg font-semibold text-gray-900">
                          Evolução do Produto
                        </h3>
                      </div>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={mostrarBuscaPredecessor}
                          onChange={(e) => handleToggleBuscaPredecessor(e.target.checked)}
                          className="h-4 w-4 text-amber-600 focus:ring-amber-500 border-gray-300 rounded"
                        />
                        <span className="text-sm font-medium text-gray-700">Este produto substitui outro</span>
                      </label>
                    </div>
                    
                    {mostrarBuscaPredecessor && (
                      <div className="space-y-4">
                        <div className="p-4 bg-white rounded-lg border-2 border-amber-300">
                          {/* Busca de Produto */}
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            🔍 Buscar Produto Anterior
                          </label>
                          <input
                            type="text"
                            placeholder="Digite o nome ou código do produto..."
                            value={buscaPredecessor}
                            onChange={(e) => handleBuscaPredecessorChange(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                          />
                          
                          {/* Resultados da Busca */}
                          {produtosBusca.length > 0 && (
                            <div className="mt-2 max-h-48 overflow-y-auto border border-gray-300 rounded-lg">
                              {produtosBusca.map(produto => (
                                <div
                                  key={produto.id}
                                  onClick={() => handleSelecionarPredecessor(produto)}
                                  className="p-3 hover:bg-amber-50 cursor-pointer border-b border-gray-200 last:border-0"
                                >
                                  <div className="font-medium text-gray-900">{produto.nome}</div>
                                  <div className="text-sm text-gray-600">
                                    SKU: {produto.codigo} | Preço: R$ {produto.preco_venda?.toFixed(2)}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                          
                          {/* Produto Selecionado */}
                          {predecessorSelecionado && (
                            <div className="mt-3 p-3 bg-green-50 border border-green-300 rounded-lg">
                              <div className="flex items-start justify-between">
                                <div>
                                  <div className="text-sm font-medium text-green-800">✅ Produto Selecionado:</div>
                                  <div className="font-semibold text-gray-900 mt-1">{predecessorSelecionado.nome}</div>
                                  <div className="text-sm text-gray-600">SKU: {predecessorSelecionado.codigo}</div>
                                </div>
                                <button
                                  type="button"
                                  onClick={handleRemoverPredecessor}
                                  className="text-red-600 hover:text-red-800"
                                >
                                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                        
                        {/* Motivo da Substituição */}
                        {predecessorSelecionado && (
                          <div className="p-4 bg-white rounded-lg border-2 border-amber-300">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              📝 Motivo da Substituição
                            </label>
                            <select
                              value={formData.motivo_descontinuacao}
                              onChange={(e) => handleChange('motivo_descontinuacao', e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent mb-2"
                            >
                              <option value="">Selecione o motivo...</option>
                              <option value="Mudança de embalagem">Mudança de embalagem</option>
                              <option value="Mudança de peso/gramatura">Mudança de peso/gramatura</option>
                              <option value="Reformulação do produto">Reformulação do produto</option>
                              <option value="Mudança de fornecedor">Mudança de fornecedor</option>
                              <option value="Upgrade de linha">Upgrade de linha</option>
                              <option value="Outro">Outro (descrever abaixo)</option>
                            </select>
                            
                            {formData.motivo_descontinuacao === 'Outro' && (
                              <textarea
                                value={formData.motivo_descontinuacao}
                                onChange={(e) => handleChange('motivo_descontinuacao', e.target.value)}
                                placeholder="Descreva o motivo..."
                                rows="2"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                              />
                            )}
                            
                            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
                              <strong>ℹ️ O que acontecerá:</strong>
                              <ul className="mt-2 space-y-1 list-disc list-inside">
                                <li>O produto "<strong>{predecessorSelecionado.nome}</strong>" será marcado como <strong>descontinuado</strong></li>
                                <li>Todo o histórico de vendas será mantido e poderá ser consultado</li>
                                <li>Você poderá gerar relatórios consolidados somando ambos os produtos</li>
                              </ul>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {!mostrarBuscaPredecessor && (
                      <p className="text-sm text-gray-600 mt-2">
                        Marque esta opção se este produto substitui outro já cadastrado (ex: mudança de embalagem de 350g para 300g).
                        Isso permite manter o histórico consolidado de vendas.
                      </p>
                    )}
                  </div>
                </div>
              )}
              
              {/* =========================================
                  CONTROLE DE TIPO DE PRODUTO (NOVO)
                  ========================================= */}
              {!isEdicao && (
                <div className="border-t pt-6">
                  <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                      </svg>
                      Tipo do Produto
                    </h3>
                    
                    <p className="text-sm text-gray-600 mb-4">
                      Escolha o tipo de produto que está cadastrando:
                    </p>
                    
                    <div className="space-y-3">
                      {/* Produto Simples */}
                      <div className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
                           style={{ borderColor: formData.tipo_produto === 'SIMPLES' ? '#3b82f6' : '#e5e7eb' }}>
                        <input
                          type="radio"
                          id="tipo_simples"
                          name="tipo_produto"
                          value="SIMPLES"
                          checked={formData.tipo_produto === 'SIMPLES'}
                          onChange={(e) => {
                            handleChange('tipo_produto', 'SIMPLES');
                            setFormData(prev => ({ ...prev, composicao_kit: [], e_kit_fisico: false }));
                          }}
                          className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                        />
                        <div className="flex-1">
                          <label htmlFor="tipo_simples" className="font-medium text-gray-900 cursor-pointer">
                            ✅ Produto Simples
                          </label>
                          <p className="text-sm text-gray-600 mt-1">
                            Produto único, vendável, com controle de estoque próprio.
                          </p>
                        </div>
                      </div>
                      
                      {/* Produto com Variações */}
                      <div className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
                           style={{ borderColor: formData.tipo_produto === 'PAI' ? '#3b82f6' : '#e5e7eb' }}>
                        <input
                          type="radio"
                          id="tipo_variacoes"
                          name="tipo_produto"
                          value="PAI"
                          checked={formData.tipo_produto === 'PAI'}
                          onChange={(e) => {
                            handleChange('tipo_produto', 'PAI');
                            // Produto PAI não tem preço próprio
                            setFormData(prev => ({
                              ...prev,
                              preco_custo: '',
                              preco_venda: '',
                              preco_promocional: '',
                              composicao_kit: [],
                              e_kit_fisico: false
                            }));
                          }}
                          className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                        />
                        <div className="flex-1">
                          <label htmlFor="tipo_variacoes" className="font-medium text-gray-900 cursor-pointer">
                            📦 Produto com Variações
                          </label>
                          <p className="text-sm text-gray-600 mt-1">
                            Produto agrupador (não vendável). Terá variações com SKU, preço e estoque próprios.
                            <br />
                            <span className="text-xs italic">Exemplo: Camiseta (produto pai) → P, M, G (variações)</span>
                          </p>
                          {formData.tipo_produto === 'PAI' && !isEdicao && (
                            <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
                              ⚠️ <strong>Salve o produto primeiro</strong> para depois cadastrar as variações na aba "Variações".
                            </div>
                          )}
                          {formData.tipo_produto === 'PAI' && isEdicao && (
                            <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                              ✅ Produto salvo! Vá para a aba "📦 Variações" para cadastrar as variações.
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Produto Kit/Composição */}
                      <div className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
                           style={{ borderColor: formData.tipo_produto === 'KIT' ? '#3b82f6' : '#e5e7eb' }}>
                        <input
                          type="radio"
                          id="tipo_kit"
                          name="tipo_produto"
                          value="KIT"
                          checked={formData.tipo_produto === 'KIT'}
                          onChange={(e) => {
                            handleChange('tipo_produto', 'KIT');
                            setAbaAtiva(9); // Abre automaticamente a aba de composição
                          }}
                          className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                        />
                        <div className="flex-1">
                          <label htmlFor="tipo_kit" className="font-medium text-gray-900 cursor-pointer">
                            🧩 Produto com Composição (Kit)
                          </label>
                          <p className="text-sm text-gray-600 mt-1">
                            Kit composto por outros produtos existentes.
                            <br />
                            <span className="text-xs italic">Exemplo: Kit Banho (shampoo + condicionador + toalha)</span>
                          </p>
                          {formData.tipo_produto === 'KIT' && (
                            <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                              ✅ <strong>Aba "🧩 Composição" aberta!</strong> Vá para a aba Composição para definir se o kit terá estoque virtual ou físico e adicionar os produtos que o compõem.
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* =========================================
                  CHECKBOX: VARIACAO PODE SER KIT (Apenas em edição de variação)
                  ========================================= */}
              {isEdicao && formData.tipo_produto === 'VARIACAO' && (
                <div className="border-t pt-6">
                  <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      Composição (Kit)
                    </h3>
                    
                    <div className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 border-gray-300">
                      <input
                        type="checkbox"
                        id="variacao_e_kit"
                        checked={!!formData.tipo_kit}
                        onChange={(e) => {
                          if (e.target.checked) {
                            handleChange('tipo_kit', 'VIRTUAL');
                            handleChange('e_kit_fisico', false);
                            setAbaAtiva(9); // Abre aba de composição
                          } else {
                            handleChange('tipo_kit', null);
                            handleChange('composicao_kit', []);
                            handleChange('e_kit_fisico', false);
                          }
                        }}
                        className="mt-1 h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <div className="flex-1">
                        <label htmlFor="variacao_e_kit" className="font-medium text-gray-900 cursor-pointer text-lg">
                          🧩 Esta variação é um KIT (possui composição)
                        </label>
                        <p className="text-sm text-gray-600 mt-2">
                          Marque esta opção se esta variação é composta por outros produtos.
                          <br />
                          <span className="text-xs italic">Exemplo: Camiseta P - Kit (camiseta + brinde)</span>
                        </p>
                        {formData.tipo_kit && (
                          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                            ✅ <strong>Variação configurada como KIT!</strong> Vá para a aba "🧩 Composição" para definir os produtos que compõem este kit.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ABA 2: IMAGENS */}
          {abaAtiva === 2 && (
            <div className="space-y-6">
              {!isEdicao ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <p className="mt-2 text-sm text-gray-600">Salve o produto primeiro para adicionar imagens</p>
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900">Imagens do Produto</h3>
                    
                    <label className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer">
                      {uploadingImage ? 'Enviando...' : '+ Adicionar Imagens'}
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        onChange={handleUploadImagem}
                        disabled={uploadingImage}
                        className="hidden"
                        multiple
                      />
                    </label>
                  </div>
                  
                  {imagens.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <p className="text-lg mb-2">📷 Nenhuma imagem cadastrada</p>
                      <p className="text-sm">Clique em "Adicionar Imagem" para enviar fotos do produto</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-4 gap-4">
                      {imagens.map(img => (
                        <div key={img.id} className="relative group border rounded-lg overflow-hidden">
                          <img
                            src={`${import.meta.env.VITE_API_URL || '/api'}${img.url}`}
                            alt="Imagem do produto"
                            className="w-full h-48 object-cover"
                          />
                          
                          {img.e_principal && (
                            <div className="absolute top-2 left-2 px-2 py-1 bg-blue-600 text-white text-xs rounded">
                              Principal
                            </div>
                          )}
                          
                          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                            {!img.e_principal && (
                              <button
                                type="button"
                                onClick={() => handleSetPrincipal(img.id)}
                                className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                                title="Definir como principal"
                              >
                                ⭐ Principal
                              </button>
                            )}
                            
                            <button
                              type="button"
                              onClick={() => handleDeleteImagem(img.id)}
                              className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                              title="Excluir"
                            >
                              🗑️ Excluir
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-800">
                      <strong>Dica:</strong> A primeira imagem marcada como "Principal" será exibida na listagem de produtos. 
                      Formatos aceitos: JPG, PNG, WebP (máx. 5MB).
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ABA 3: ESTOQUE/LOTES */}
          {abaAtiva === 3 && (
            <div className="space-y-6">
              {/* Aviso para produtos PAI */}
              {formData.tipo_produto === 'PAI' ? (
                <div className="text-center py-12 border-2 border-dashed border-blue-300 rounded-lg bg-blue-50">
                  <svg className="mx-auto h-12 w-12 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                  <p className="mt-4 text-lg font-medium text-blue-900">Produto com Variações</p>
                  <p className="mt-2 text-sm text-blue-700">
                    Produtos PAI não possuem estoque próprio.<br/>
                    O controle de estoque é feito individualmente nas variações.
                  </p>
                </div>
              ) : (
                <>
                  {/* Controles de Estoque */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.controle_lote}
                      onChange={(e) => handleChange('controle_lote', e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-sm font-medium text-gray-700">Controlar Estoque</span>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Estoque Mínimo
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.estoque_minimo}
                    onChange={(e) => handleChange('estoque_minimo', e.target.value)}
                    disabled={!formData.controle_lote}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                    placeholder="0"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Estoque Máximo
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.estoque_maximo}
                    onChange={(e) => handleChange('estoque_maximo', e.target.value)}
                    disabled={!formData.controle_lote}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                    placeholder="0"
                  />
                </div>
              </div>

              {/* Lotes (somente na ediÃ§Ã£o) */}
              {isEdicao && formData.controle_lote && (
                <>
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900">Lotes (FIFO)</h3>
                    <button
                      type="button"
                      onClick={() => setModalEntrada(true)}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      + Nova Entrada
                    </button>
                  </div>

                  {lotes.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      Nenhum lote cadastrado
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lote</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qtd Disponível</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fabricação</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validade</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Custo Unit.</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {lotes.map((lote) => (
                            <tr key={lote.id}>
                              <td className="px-4 py-3 text-sm text-gray-900">{lote.nome_lote || '-'}</td>
                              <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">{lote.quantidade_disponivel}</td>
                              <td className="px-4 py-3 text-sm text-gray-700">{formatarData(lote.data_fabricacao)}</td>
                              <td className="px-4 py-3 text-sm text-gray-700">{formatarData(lote.data_validade)}</td>
                              <td className="px-4 py-3 text-sm text-right text-gray-900">{formatarMoeda(lote.custo_unitario)}</td>
                              <td className="px-4 py-3 text-sm text-center">
                                <div className="flex justify-center gap-2">
                                  <button
                                    type="button"
                                    onClick={() => handleEditarLote(lote)}
                                    className="text-blue-600 hover:text-blue-800"
                                    title="Editar lote"
                                  >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                    </svg>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleExcluirLote(lote)}
                                    className="text-red-600 hover:text-red-800"
                                    title="Excluir lote"
                                  >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}

              {!isEdicao && (
                <div className="text-center py-8 text-gray-500">
                  Salve o produto primeiro para gerenciar lotes
                </div>
              )}
              </>
              )}
            </div>
          )}

          {/* ABA 4: FORNECEDORES */}
          {abaAtiva === 4 && (
            <div className="space-y-6">
              {!isEdicao ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
                  <p className="text-gray-600">Salve o produto primeiro para vincular fornecedores</p>
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900">Fornecedores do Produto</h3>
                    
                    <button
                      type="button"
                      onClick={handleAddFornecedor}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      + Adicionar Fornecedor
                    </button>
                  </div>
                  
                  {fornecedores.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <p className="text-lg mb-2">🏭 Nenhum fornecedor vinculado</p>
                      <p className="text-sm">Clique em "Adicionar Fornecedor" para vincular fornecedores a este produto</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fornecedor</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Preço Custo</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Prazo (dias)</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estoque</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Principal</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {fornecedores.map(forn => (
                            <tr key={forn.id} className={!forn.ativo ? 'opacity-50' : ''}>
                              <td className="px-4 py-3">
                                <div>
                                  <p className="text-sm font-medium text-gray-900">{forn.fornecedor_nome}</p>
                                  <p className="text-xs text-gray-500">{forn.fornecedor_cpf_cnpj}</p>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-900">{forn.codigo_fornecedor || '-'}</td>
                              <td className="px-4 py-3 text-sm text-gray-900 text-right">
                                {forn.preco_custo ? formatarMoeda(forn.preco_custo) : '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-900 text-center">{forn.prazo_entrega || '-'}</td>
                              <td className="px-4 py-3 text-sm text-gray-900 text-center">{forn.estoque_fornecedor || '-'}</td>
                              <td className="px-4 py-3 text-center">
                                {forn.e_principal && (
                                  <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">Principal</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-right space-x-2">
                                <button
                                  type="button"
                                  onClick={() => handleEditFornecedor(forn)}
                                  className="text-blue-600 hover:text-blue-800 text-sm"
                                >
                                  Editar
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteFornecedor(forn.id)}
                                  className="text-red-600 hover:text-red-800 text-sm"
                                >
                                  Excluir
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
            </div>
          )}          {/* ABA 5: TRIBUTAÇÃO */}
          {abaAtiva === 5 && (
            <ProdutosNovoTributacaoTab
              formData={formData}
              handleChangeTributacao={handleChangeTributacao}
              handlePersonalizarFiscal={handlePersonalizarFiscal}
            />
          )}          {/* ABA 6: RECORRÊNCIA */}
          {abaAtiva === 6 && (
            <ProdutosNovoRecorrenciaTab
              formData={formData}
              handleChange={handleChange}
              handleTipoRecorrenciaChange={handleTipoRecorrenciaChange}
            />
          )}          {/* ABA 7: RAÇÃO - CALCULADORA */}
          {abaAtiva === 7 && (
            <ProdutosNovoRacaoTab
              formData={formData}
              handleChange={handleChange}
              handleApresentacaoPesoChange={handleApresentacaoPesoChange}
              handleClassificacaoRacaoChange={handleClassificacaoRacaoChange}
              handleFasePublicoChange={handleFasePublicoChange}
              opcoesApresentacoes={opcoesApresentacoes}
              opcoesFases={opcoesFases}
              opcoesLinhas={opcoesLinhas}
              opcoesPortes={opcoesPortes}
              opcoesSabores={opcoesSabores}
              opcoesTratamentos={opcoesTratamentos}
            />
          )}

          {/* ABA 8: VARIAÇÕES (Sprint 2) - Apenas para produtos PAI */}
          {abaAtiva === 8 && formData.tipo_produto === 'PAI' && (
            <ProdutosNovoVariacoesTab
              formData={formData}
              isEdicao={isEdicao}
              mostrarFormVariacao={mostrarFormVariacao}
              novaVariacao={novaVariacao}
              setNovaVariacao={setNovaVariacao}
              variacoes={variacoes}
              handleToggleFormVariacao={handleToggleFormVariacao}
              handleCancelarVariacao={handleCancelarVariacao}
              handleSalvarVariacao={handleSalvarVariacao}
              handleExcluirVariacao={handleExcluirVariacao}
              onEditarVariacao={(variacao) => navigate(`/produtos/${variacao.id}/editar`)}
            />
          )}
          {/* ============================================
              ABA 9: COMPOSIÇÃO/KIT (Produto KIT ou VARIACAO-KIT)
              ============================================ */}
          {abaAtiva === 9 && (formData.tipo_produto === 'KIT' || (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)) && (
            <ProdutosNovoComposicaoTab
              formData={formData}
              handleChange={handleChange}
              estoqueVirtualKit={estoqueVirtualKit}
              produtosDisponiveis={produtosDisponiveis}
              produtoKitSelecionado={produtoKitSelecionado}
              setProdutoKitSelecionado={setProdutoKitSelecionado}
              quantidadeKit={quantidadeKit}
              setQuantidadeKit={setQuantidadeKit}
              buscaComponente={buscaComponente}
              setBuscaComponente={setBuscaComponente}
              dropdownComponenteVisivel={dropdownComponenteVisivel}
              setDropdownComponenteVisivel={setDropdownComponenteVisivel}
              adicionarProdutoKit={adicionarProdutoKit}
              removerProdutoKit={removerProdutoKit}
            />
          )}
        </div>
        <ProdutosNovoFooterActions
          isEdicao={isEdicao}
          onCancel={() => navigate('/produtos')}
          salvando={salvando}
        />
      </form>

      {modalEntrada && (
        <ProdutosNovoEntradaModal
          entradaData={entradaData}
          setEntradaData={setEntradaData}
          onClose={() => setModalEntrada(false)}
          onSubmit={handleEntradaEstoque}
        />
      )}
      {modalEdicaoLote && loteEmEdicao && (
        <ProdutosNovoLoteModal
          loteEmEdicao={loteEmEdicao}
          setLoteEmEdicao={setLoteEmEdicao}
          onClose={() => {
            setModalEdicaoLote(false);
            setLoteEmEdicao(null);
          }}
          onSubmit={handleSalvarEdicaoLote}
        />
      )}
      {modalFornecedor && (
        <ProdutosNovoFornecedorModal
          clientes={clientes}
          fornecedorData={fornecedorData}
          fornecedorEdit={fornecedorEdit}
          setFornecedorData={setFornecedorData}
          onClose={() => setModalFornecedor(false)}
          onSubmit={handleSaveFornecedor}
        />
      )}
    </div>
  );
}


