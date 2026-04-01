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
import ProdutosNovoCaracteristicasTab from '../components/produto/ProdutosNovoCaracteristicasTab';
import ProdutosNovoEstoqueTab from '../components/produto/ProdutosNovoEstoqueTab';
import ProdutosNovoRacaoTab from '../components/produto/ProdutosNovoRacaoTab';
import ProdutosNovoRecorrenciaTab from '../components/produto/ProdutosNovoRecorrenciaTab';
import ProdutosNovoFornecedoresTab from '../components/produto/ProdutosNovoFornecedoresTab';
import ProdutosNovoTabs from '../components/produto/ProdutosNovoTabs';
import ProdutosNovoTributacaoTab from '../components/produto/ProdutosNovoTributacaoTab';
import ProdutosNovoVariacoesTab from '../components/produto/ProdutosNovoVariacoesTab';
import ProdutosNovoImagensTab from '../components/produto/ProdutosNovoImagensTab';
import ProdutosNovoStatusBanners from '../components/produto/ProdutosNovoStatusBanners';
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
import useProdutosNovoPageComposition from '../hooks/useProdutosNovoPageComposition';
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


  const {
    canShowComposicaoTab,
    canShowVariacoesTab,
    caracteristicasTabProps,
    composicaoTabProps,
    entradaModalProps,
    estoqueTabProps,
    footerProps,
    fornecedoresTabProps,
    fornecedorModalProps,
    headerProps,
    imagensTabProps,
    loteModalProps,
    racaoTabProps,
    recorrenciaTabProps,
    statusBannersProps,
    tabsProps,
    tributacaoTabProps,
    variacoesTabProps,
  } = useProdutosNovoPageComposition({
    adicionarProdutoKit,
    abaAtiva,
    buscaComponente,
    buscaPredecessor,
    camposEmEdicao,
    categoriasHierarquicas,
    clientes,
    departamentos,
    dropdownComponenteVisivel,
    entradaData,
    estoqueVirtualKit,
    formData,
    fornecedores,
    fornecedorData,
    fornecedorEdit,
    formatarData,
    formatarMoeda,
    handleAddFornecedor,
    handleApresentacaoPesoChange,
    handleBuscaPredecessorChange,
    handleCancelarVariacao,
    handleChange,
    handleChangeTributacao,
    handleClassificacaoRacaoChange,
    handleDeleteFornecedor,
    handleDeleteImagem,
    handleEditarLote,
    handleEditFornecedor,
    handleExcluirLote,
    handleExcluirVariacao,
    handleEntradaEstoque,
    handleFasePublicoChange,
    handleGerarCodigoBarras,
    handleGerarSKU,
    handlePersonalizarFiscal,
    handleRemoverPredecessor,
    handleSalvarEdicaoLote,
    handleSalvarVariacao,
    handleSaveFornecedor,
    handleSelecionarPredecessor,
    handleSetPrincipal,
    handleTipoRecorrenciaChange,
    handleToggleBuscaPredecessor,
    handleToggleFormVariacao,
    handleUploadImagem,
    handleVoltar,
    imagens,
    isEdicao,
    loading,
    loteEmEdicao,
    lotes,
    marcas,
    modalEdicaoLote,
    modalEntrada,
    modalFornecedor,
    mostrarBuscaPredecessor,
    mostrarFormVariacao,
    navigate,
    novaVariacao,
    opcoesApresentacoes,
    opcoesFases,
    opcoesLinhas,
    opcoesPortes,
    opcoesSabores,
    opcoesTratamentos,
    parseNumber,
    predecessorInfo,
    predecessorSelecionado,
    produtoKitSelecionado,
    produtosBusca,
    produtosDisponiveis,
    quantidadeKit,
    removerProdutoKit,
    salvando,
    setAbaAtiva,
    setCamposEmEdicao,
    setEntradaData,
    setFornecedorData,
    setFormData,
    setLoteEmEdicao,
    setModalEdicaoLote,
    setModalEntrada,
    setModalFornecedor,
    setNovaVariacao,
    setProdutoKitSelecionado,
    setQuantidadeKit,
    setBuscaComponente,
    setDropdownComponenteVisivel,
    sucessorInfo,
    uploadingImage,
    variacoes,
  });
  
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
      <ProdutosNovoHeader {...headerProps} />

      <ProdutosNovoTabs {...tabsProps} />

      <ProdutosNovoStatusBanners {...statusBannersProps} />

      <form onSubmit={handleSubmit}>
        <div className="bg-white rounded-lg shadow-sm p-6">
          {abaAtiva === 1 && <ProdutosNovoCaracteristicasTab {...caracteristicasTabProps} />}
          {abaAtiva === 2 && <ProdutosNovoImagensTab {...imagensTabProps} />}
          {abaAtiva === 3 && <ProdutosNovoEstoqueTab {...estoqueTabProps} />}
          {abaAtiva === 4 && <ProdutosNovoFornecedoresTab {...fornecedoresTabProps} />}
          {abaAtiva === 5 && <ProdutosNovoTributacaoTab {...tributacaoTabProps} />}
          {abaAtiva === 6 && <ProdutosNovoRecorrenciaTab {...recorrenciaTabProps} />}
          {abaAtiva === 7 && <ProdutosNovoRacaoTab {...racaoTabProps} />}
          {canShowVariacoesTab && <ProdutosNovoVariacoesTab {...variacoesTabProps} />}
          {canShowComposicaoTab && <ProdutosNovoComposicaoTab {...composicaoTabProps} />}
        </div>
        <ProdutosNovoFooterActions {...footerProps} />
      </form>

      {entradaModalProps && <ProdutosNovoEntradaModal {...entradaModalProps} />}
      {loteModalProps && <ProdutosNovoLoteModal {...loteModalProps} />}
      {fornecedorModalProps && <ProdutosNovoFornecedorModal {...fornecedorModalProps} />}
    </div>
  );
}
