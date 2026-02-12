/**
 * FormulÃ¡rio de Cadastro/EdiÃ§Ã£o de Produtos - Layout em Abas
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import TabelaConsumoEditor from '../components/TabelaConsumoEditor';
import {
  getProduto,
  createProduto,
  updateProduto,
  deleteProduto,
  getProdutoVariacoes,
  getCategorias,
  getMarcas,
  getDepartamentos,
  gerarSKU,
  gerarCodigoBarras,
  getLotes,
  entradaEstoque,
  updateLote,
  deleteLote,
  uploadImagemProduto,
  deleteImagemProduto,
  getFornecedoresProduto,
  addFornecedorProduto,
  updateFornecedorProduto,
  deleteFornecedorProduto,
  calcularPrecoVenda,
  calcularMarkup,
  formatarMoeda,
  formatarData,
} from '../api/produtos';
import api from '../api';

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
  });

  // Dados auxiliares
  const [categorias, setCategorias] = useState([]);
  const [categoriasHierarquicas, setCategoriasHierarquicas] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);
  const [lotes, setLotes] = useState([]);
  const [imagens, setImagens] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [clientes, setClientes] = useState([]);
  
  // Sprint 2: Estados para variações
  const [variacoes, setVariacoes] = useState([]);
  const [novaVariacao, setNovaVariacao] = useState({
    sku: '',
    nome: '',
    codigo_barras: '',
    preco_custo: '',
    preco_venda: '',
    estoque_minimo: 0,
    e_kit: false, // VARIACAO pode ser KIT
    e_kit_fisico: false,
    composicao_kit: []
  });
  const [mostrarFormVariacao, setMostrarFormVariacao] = useState(false);
  
  // Estados para composição de kit
  const [produtosDisponiveis, setProdutosDisponiveis] = useState([]);
  const [produtoKitSelecionado, setProdutoKitSelecionado] = useState('');
  const [quantidadeKit, setQuantidadeKit] = useState('');
  const [estoqueVirtualKit, setEstoqueVirtualKit] = useState(0);
  
  // Estados para predecessor/sucessor
  const [mostrarBuscaPredecessor, setMostrarBuscaPredecessor] = useState(false);
  const [produtosBusca, setProdutosBusca] = useState([]);
  const [buscaPredecessor, setBuscaPredecessor] = useState('');
  const [predecessorSelecionado, setPredecessorSelecionado] = useState(null);
  const [predecessorInfo, setPredecessorInfo] = useState(null); // Info do predecessor ao editar
  const [sucessorInfo, setSucessorInfo] = useState(null); // Info do sucessor (se descontinuado)
  
  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);

  // Modal de entrada de estoque
  const [modalEntrada, setModalEntrada] = useState(false);
  const [entradaData, setEntradaData] = useState({
    quantidade: '',
    nome_lote: '',
    data_fabricacao: '',
    data_validade: '',
    preco_custo: '',
  });

  // Modal de edição de lote
  const [modalEdicaoLote, setModalEdicaoLote] = useState(false);
  const [loteEmEdicao, setLoteEmEdicao] = useState(null);

  // Modal de fornecedor
  const [modalFornecedor, setModalFornecedor] = useState(false);
  const [fornecedorEdit, setFornecedorEdit] = useState(null);
  const [fornecedorData, setFornecedorData] = useState({
    fornecedor_id: '',
    codigo_fornecedor: '',
    preco_custo: '',
    prazo_entrega: '',
    estoque_fornecedor: '',
    e_principal: false,
  });

  // Carregar dados iniciais
  useEffect(() => {
    carregarDadosAuxiliares();
    
    if (isEdicao) {
      carregarProduto();
    }
  }, [id]);
  
  // Detectar parâmetro de aba na URL (após carregar o produto)
  useEffect(() => {
    if (!loading && isEdicao) {
      const abaParam = searchParams.get('aba');
      if (abaParam) {
        setAbaAtiva(parseInt(abaParam));
      }
    }
  }, [loading, searchParams, isEdicao]);
  
  // 🛡️ PROTEÇÃO: Se for VARIACAO e estiver na aba 8, voltar para aba 1
  useEffect(() => {
    if (isEdicao && formData.tipo_produto === 'VARIACAO' && abaAtiva === 8) {
      setAbaAtiva(1);
    }
  }, [formData.tipo_produto, abaAtiva, isEdicao]);
  
  // Sprint 2: Carregar variações quando abrir a aba
  useEffect(() => {
    if (isEdicao && abaAtiva === 8 && formData.tipo_produto === 'PAI') {
      carregarVariacoes();
    }
  }, [abaAtiva, isEdicao, formData.tipo_produto]);
  
  const carregarVariacoes = async () => {
    try {
      const response = await getProdutoVariacoes(id);
      setVariacoes(response.data);
    } catch (error) {
      console.error('Erro ao carregar variações:', error);
    }
  };

  const carregarDadosAuxiliares = async () => {
    try {
      const [catRes, marcRes, depRes, cliRes] = await Promise.all([
        getCategorias(),
        getMarcas(),
        getDepartamentos(),
        api.get('/clientes', { params: { tipo_cadastro: 'fornecedor', apenas_ativos: true } }),
      ]);
      setCategorias(catRes.data);
      
      // Construir lista hierárquica para o select
      const hierarquica = construirListaHierarquica(catRes.data);
      setCategoriasHierarquicas(hierarquica);
      
      setMarcas(marcRes.data);
      setDepartamentos(depRes.data);
      setClientes(cliRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados auxiliares:', error);
    }
  };
  
  // Função para construir lista hierárquica de categorias para o select
  const construirListaHierarquica = (cats, parentId = null, nivel = 0) => {
    let resultado = [];
    
    const filhos = cats.filter(c => c.categoria_pai_id === parentId);
    
    filhos.forEach((cat) => {
      // Usar espaços não-quebráveis (\u00a0) e seta para indicar nível
      const indentacao = '\u00a0\u00a0\u00a0\u00a0'.repeat(nivel); // 4 espaços não-quebráveis por nível
      const seta = nivel > 0 ? '→ ' : '';
      
      resultado.push({
        ...cat,
        nomeFormatado: indentacao + seta + cat.nome,
        nivel
      });
      
      // Recursão para filhos
      const subFilhos = construirListaHierarquica(cats, cat.id, nivel + 1);
      resultado = resultado.concat(subFilhos);
    });
    
    return resultado;
  };

  const carregarProduto = async () => {
    try {
      setLoading(true);
      
      // 🧹 Limpar estados de predecessor/sucessor ao carregar novo produto
      setPredecessorInfo(null);
      setSucessorInfo(null);
      
      const response = await getProduto(id);
      const produto = response.data;
      
      // Calcular markup baseado nos preços salvos
      let markup = '';
      if (produto.preco_custo && produto.preco_venda && produto.preco_custo > 0) {
        markup = calcularMarkup(produto.preco_custo, produto.preco_venda).toFixed(2);
      }
      
      // Preencher formulário
      setFormData({
        ...produto,
        sku: produto.codigo || '', // Mapear codigo para sku
        codigo: produto.codigo || '',
        nome: produto.nome || '',
        codigo_barras: produto.codigo_barras || '',
        categoria_id: produto.categoria_id || '',
        marca_id: produto.marca_id || '',
        departamento_id: produto.departamento_id || '',
        unidade: produto.unidade || 'UN',
        descricao: produto.descricao_curta || '',
        tipo: produto.tipo || 'produto',
        preco_custo: produto.preco_custo || '',
        preco_venda: produto.preco_venda || '',
        preco_promocional: produto.preco_promocional || '',
        data_inicio_promocao: produto.promocao_inicio || '',
        data_fim_promocao: produto.promocao_fim || '',
        estoque_minimo: produto.estoque_minimo || '',
        estoque_maximo: produto.estoque_maximo || '',
        controle_lote: produto.controle_lote ?? true,
        markup: markup, // Adicionar markup calculado
        // Sprint 2: Tipo de produto e composição
        tipo_produto: produto.tipo_produto || 'SIMPLES',
        produto_pai_id: produto.produto_pai_id || null,
        tipo_kit: produto.tipo_kit || null, // VARIACAO pode ser KIT
        e_kit_fisico: produto.e_kit_fisico || false,
        composicao_kit: produto.composicao_kit || [],
        // Tributação
        origem: produto.origem || '0',
        ncm: produto.ncm || '',
        cest: produto.cest || '',
        cfop: produto.cfop || '',
        aliquota_icms: produto.aliquota_icms || '',
        aliquota_pis: produto.aliquota_pis || '',
        aliquota_cofins: produto.aliquota_cofins || '',
        // Garantir campos de recorrência sempre definidos
        tem_recorrencia: produto.tem_recorrencia || false,
        tipo_recorrencia: produto.tipo_recorrencia || 'monthly',
        intervalo_dias: produto.intervalo_dias || '',
        numero_doses: produto.numero_doses || '',
        especie_compativel: produto.especie_compativel || 'both',
        observacoes_recorrencia: produto.observacoes_recorrencia || '',
        // Ração - Calculadora (Fase 2)
        classificacao_racao: produto.classificacao_racao || '',
        peso_embalagem: produto.peso_embalagem || '',
        tabela_nutricional: produto.tabela_nutricional || '',
        tabela_consumo: produto.tabela_consumo || '',
        categoria_racao: produto.categoria_racao || '',
        especies_indicadas: produto.especies_indicadas || 'both',
      });

      // 🔗 Carregar informações do predecessor
      if (produto.produto_predecessor_id) {
        try {
          const predecessorRes = await getProduto(produto.produto_predecessor_id);
          setPredecessorInfo({
            id: predecessorRes.data.id,
            codigo: predecessorRes.data.codigo,
            nome: predecessorRes.data.nome,
            motivo_descontinuacao: produto.motivo_descontinuacao,
            data_descontinuacao: produto.predecessor?.data_descontinuacao
          });
        } catch (error) {
          console.error('Erro ao carregar predecessor:', error);
        }
      }

      // 🔗 Carregar informações do sucessor (se produto foi descontinuado)
      if (produto.data_descontinuacao) {
        try {
          // Buscar produtos que têm este como predecessor
          const response = await api.get('/produtos/', {
            params: { 
              produto_predecessor_id: produto.id,
              ativo: null // Incluir ativos e inativos
            }
          });
          
          // A API pode retornar um array direto ou um objeto paginado
          const sucessores = Array.isArray(response.data) ? response.data : (response.data.items || []);
          
          if (sucessores && sucessores.length > 0) {
            const sucessor = sucessores[0];
            setSucessorInfo({
              id: sucessor.id,
              codigo: sucessor.codigo,
              nome: sucessor.nome,
              motivo_descontinuacao: produto.motivo_descontinuacao,
              data_descontinuacao: produto.data_descontinuacao
            });
          }
        } catch (error) {
          console.error('❌ Erro ao carregar sucessor:', error);
        }
      }

      // Carregar imagens do endpoint específico
      try {
        const imagensRes = await api.get(`/produtos/${id}/imagens`);
        setImagens(imagensRes.data || []);
      } catch (error) {
        console.error('Erro ao carregar imagens:', error);
        setImagens([]);
      }

      // Carregar lotes
      if (produto.controle_lote) {
        const lotesRes = await getLotes(id);
        setLotes(lotesRes.data);
      }

      // Carregar fornecedores
      const fornRes = await getFornecedoresProduto(id);
      setFornecedores(fornRes.data);

      // 📦 FISCAL V2: Carregar dados fiscais
      await carregarFiscal(produto);
    } catch (error) {
      console.error('❌ Erro ao carregar produto:', error);
      alert('Erro ao carregar produto: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 📦 FISCAL V2: Carregar dados fiscais
  const carregarFiscal = async (produto) => {
    try {
      const isKit = produto.tipo_produto === 'KIT';

      const { data } = isKit
        ? await api.get(`/produtos/${produto.id}/kit/fiscal`)
        : await api.get(`/produtos/${produto.id}/fiscal`);

      setFormData((prev) => ({
        ...prev,
        tributacao: {
          origem: data.origem,
          herdado_da_empresa: data.herdado_da_empresa,
          origem_mercadoria: data.origem_mercadoria ?? '0',
          ncm: data.ncm ?? '',
          cest: data.cest ?? '',
          cfop: data.cfop ?? '',
          cst_icms: data.cst_icms ?? '',
          icms_aliquota: data.icms_aliquota ?? '',
          icms_st: data.icms_st ?? false,
          pis_aliquota: data.pis_aliquota ?? '',
          cofins_aliquota: data.cofins_aliquota ?? '',
        },
      }));
    } catch (e) {
      console.error('Erro ao carregar fiscal:', e);
    }
  };

  // 💾 FISCAL V2: Salvar dados fiscais
  const salvarFiscal = async (produto) => {
    const payload = {
      origem_mercadoria: formData.tributacao.origem_mercadoria,
      ncm: formData.tributacao.ncm,
      cest: formData.tributacao.cest,
      cfop: formData.tributacao.cfop,
      cst_icms: formData.tributacao.cst_icms,
      icms_aliquota: formData.tributacao.icms_aliquota,
      icms_st: formData.tributacao.icms_st,
      pis_aliquota: formData.tributacao.pis_aliquota,
      cofins_aliquota: formData.tributacao.cofins_aliquota,
    };

    if (produto.tipo_produto === 'KIT') {
      await api.put(`/produtos/${produto.id}/kit/fiscal`, payload);
    } else {
      await api.put(`/produtos/${produto.id}/fiscal`, payload);
    }
  };

  const handleChange = (campo, valor) => {
    setFormData(prev => {
      const novosDados = { ...prev, [campo]: valor };
      
      // Calcular markup automaticamente quando mudar preÃ§o
      if (campo === 'preco_custo' || campo === 'preco_venda') {
        const custo = parseFloat(campo === 'preco_custo' ? valor : prev.preco_custo);
        const venda = parseFloat(campo === 'preco_venda' ? valor : prev.preco_venda);
        
        if (custo && venda && custo > 0) {
          const markup = calcularMarkup(custo, venda);
          novosDados.markup = markup.toFixed(2);
        }
      }
      
      // Calcular preÃ§o de venda pelo markup
      if (campo === 'markup') {
        const custo = parseFloat(prev.preco_custo);
        const markupVal = parseFloat(valor);
        
        if (custo && custo > 0 && markupVal >= 0) {
          const venda = calcularPrecoVenda(custo, markupVal);
          novosDados.preco_venda = venda.toFixed(2);
        }
      }
      
      return novosDados;
    });
  };

  const handleGerarSKU = async () => {
    try {
      const response = await gerarSKU('PROD');
      setFormData(prev => ({ ...prev, sku: response.data.sku }));
      alert('SKU gerado com sucesso!');
    } catch (error) {
      console.error('Erro ao gerar SKU:', error);
      alert('Erro ao gerar SKU');
    }
  };

  const handleGerarCodigoBarras = async () => {
    if (!formData.sku) {
      alert('Gere ou informe um SKU primeiro!');
      return;
    }

    try {
      const response = await gerarCodigoBarras(formData.sku);
      setFormData(prev => ({ ...prev, codigo_barras: response.data.codigo_barras }));
      alert('Código de barras gerado com sucesso!');
    } catch (error) {
      console.error('Erro ao gerar cÃ³digo de barras:', error);
      alert('Erro ao gerar cÃ³digo de barras');
    }
  };

  const handleEntradaEstoque = async () => {
    if (!entradaData.quantidade || !entradaData.preco_custo) {
      alert('Preencha quantidade e preÃ§o de custo!');
      return;
    }

    try {
      // Gerar nÃºmero de lote automÃ¡tico se nÃ£o preenchido
      const numeroLote = entradaData.nome_lote || `LOTE-${Date.now()}`;
      
      // Converter datas para formato ISO com hora
      const dataFabricacao = entradaData.data_fabricacao 
        ? new Date(entradaData.data_fabricacao + 'T00:00:00').toISOString() 
        : null;
      const dataValidade = entradaData.data_validade 
        ? new Date(entradaData.data_validade + 'T23:59:59').toISOString() 
        : null;
      
      await entradaEstoque(id, {
        nome_lote: numeroLote,
        quantidade: parseFloat(entradaData.quantidade),
        preco_custo: parseFloat(entradaData.preco_custo),
        data_fabricacao: dataFabricacao,
        data_validade: dataValidade,
        observacoes: entradaData.observacoes || null,
      });
      
      alert('Entrada de estoque realizada com sucesso!');
      setModalEntrada(false);
      setEntradaData({
        quantidade: '',
        nome_lote: '',
        data_fabricacao: '',
        data_validade: '',
        preco_custo: '',
      });
      
      // Recarregar lotes
      const lotesRes = await getLotes(id);
      setLotes(lotesRes.data);
    } catch (error) {
      console.error('Erro ao registrar entrada:', error);
      alert(error.response?.data?.detail || 'Erro ao registrar entrada de estoque');
    }
  };

  const handleEditarLote = (lote) => {
    setLoteEmEdicao({
      id: lote.id,
      nome_lote: lote.nome_lote,
      quantidade_inicial: lote.quantidade_inicial,
      data_fabricacao: lote.data_fabricacao?.split('T')[0] || '',
      data_validade: lote.data_validade?.split('T')[0] || '',
      custo_unitario: lote.custo_unitario,
    });
    setModalEdicaoLote(true);
  };

  const handleSalvarEdicaoLote = async () => {
    try {
      const dataFabricacao = loteEmEdicao.data_fabricacao 
        ? new Date(loteEmEdicao.data_fabricacao + 'T00:00:00').toISOString()
        : null;
      
      const dataValidade = loteEmEdicao.data_validade 
        ? new Date(loteEmEdicao.data_validade + 'T23:59:59').toISOString()
        : null;

      const dados = {
        nome_lote: loteEmEdicao.nome_lote,
        quantidade_inicial: parseFloat(loteEmEdicao.quantidade_inicial),
        data_fabricacao: dataFabricacao,
        data_validade: dataValidade,
        custo_unitario: parseFloat(loteEmEdicao.custo_unitario),
      };

      await updateLote(id, loteEmEdicao.id, dados);
      alert('Lote atualizado com sucesso!');
      setModalEdicaoLote(false);
      setLoteEmEdicao(null);
      
      // Recarregar lotes
      const lotesRes = await getLotes(id);
      setLotes(lotesRes.data);
    } catch (error) {
      console.error('Erro ao atualizar lote:', error);
      alert(error.response?.data?.detail || 'Erro ao atualizar lote');
    }
  };

  const handleExcluirLote = async (lote) => {
    if (!window.confirm(`Deseja realmente excluir o lote ${lote.nome_lote}?\n\nQuantidade: ${lote.quantidade_disponivel} unidades\nIsso removerá o registro de entrada do estoque.`)) {
      return;
    }

    try {
      await deleteLote(id, lote.id);
      alert('Lote excluído com sucesso!');
      
      // Recarregar lotes
      const lotesRes = await getLotes(id);
      setLotes(lotesRes.data);
    } catch (error) {
      console.error('Erro ao excluir lote:', error);
      alert(error.response?.data?.detail || 'Erro ao excluir lote');
    }
  };

  // ==================== IMAGENS ====================
  
  const handleUploadImagem = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;
    
    // Validações
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const maxSize = 5 * 1024 * 1024; // 5MB
    
    // Validar todos os arquivos
    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        alert(`${file.name}: Apenas JPG, PNG e WebP são permitidos`);
        return;
      }
      if (file.size > maxSize) {
        alert(`${file.name}: Imagem deve ter no máximo 5MB`);
        return;
      }
    }
    
    try {
      setUploadingImage(true);
      
      // Upload de cada arquivo
      const uploadedImages = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
          const response = await uploadImagemProduto(id, formData);
          uploadedImages.push(response.data);
        } catch (error) {
          console.error(`Erro ao enviar ${file.name}:`, error);
          alert(`Erro ao enviar ${file.name}: ${error.response?.data?.detail || 'Erro desconhecido'}`);
        }
      }
      
      // Recarregar todas as imagens do servidor
      const imagensRes = await api.get(`/produtos/${id}/imagens`);
      setImagens(imagensRes.data || []);
      
      alert(`${uploadedImages.length} imagem(ns) enviada(s) com sucesso!`);
      
    } catch (error) {
      console.error('Erro ao enviar imagens:', error);
      alert(error.response?.data?.detail || 'Erro ao enviar imagens');
    } finally {
      setUploadingImage(false);
      e.target.value = '';
    }
  };
  
  const handleDeleteImagem = async (imagemId) => {
    if (!confirm('Deseja realmente excluir esta imagem?')) return;
    
    try {
      await deleteImagemProduto(imagemId);
      
      // Recarregar imagens do servidor
      const imagensRes = await api.get(`/produtos/${id}/imagens`);
      setImagens(imagensRes.data || []);
      
      alert('Imagem excluída com sucesso!');
    } catch (error) {
      console.error('Erro ao excluir imagem:', error);
      alert('Erro ao excluir imagem');
    }
  };
  
  const handleSetPrincipal = async (imagemId) => {
    try {
      await api.put(`/produtos/imagens/${imagemId}`, { principal: true });
      
      // Recarregar imagens do servidor
      const imagensRes = await api.get(`/produtos/${id}/imagens`);
      setImagens(imagensRes.data || []);
      
      alert('Imagem principal atualizada!');
    } catch (error) {
      console.error('Erro ao definir imagem principal:', error);
      alert('Erro ao definir imagem principal');
    }
  };

  // ==================== FORNECEDORES ====================
  
  const handleAddFornecedor = () => {
    setFornecedorEdit(null);
    setFornecedorData({
      fornecedor_id: '',
      codigo_fornecedor: '',
      preco_custo: '',
      prazo_entrega: '',
      estoque_fornecedor: '',
      e_principal: false,
    });
    setModalFornecedor(true);
  };
  
  const handleEditFornecedor = (fornecedor) => {
    setFornecedorEdit(fornecedor);
    setFornecedorData({
      fornecedor_id: fornecedor.fornecedor_id,
      codigo_fornecedor: fornecedor.codigo_fornecedor || '',
      preco_custo: fornecedor.preco_custo || '',
      prazo_entrega: fornecedor.prazo_entrega || '',
      estoque_fornecedor: fornecedor.estoque_fornecedor || '',
      e_principal: fornecedor.e_principal || false,
    });
    setModalFornecedor(true);
  };
  
  const handleSaveFornecedor = async () => {
    if (!fornecedorData.fornecedor_id) {
      alert('Selecione um fornecedor');
      return;
    }

    try {
      const dados = {
        ...fornecedorData,
        preco_custo: fornecedorData.preco_custo ? parseFloat(fornecedorData.preco_custo) : null,
        prazo_entrega: fornecedorData.prazo_entrega ? parseInt(fornecedorData.prazo_entrega) : null,
        estoque_fornecedor: fornecedorData.estoque_fornecedor ? parseFloat(fornecedorData.estoque_fornecedor) : null,
      };

      if (fornecedorEdit) {
        await updateFornecedorProduto(fornecedorEdit.id, dados);
        alert('Fornecedor atualizado!');
      } else {
        await addFornecedorProduto(id, dados);
        alert('Fornecedor vinculado!');
      }
      
      // Recarregar fornecedores
      const fornRes = await getFornecedoresProduto(id);
      setFornecedores(fornRes.data);
      
      setModalFornecedor(false);
      
    } catch (error) {
      console.error('Erro ao salvar fornecedor:', error);
      alert(error.response?.data?.detail || 'Erro ao salvar fornecedor');
    }
  };
  
  const handleDeleteFornecedor = async (fornecedorId) => {
    if (!confirm('Deseja realmente desvincular este fornecedor?')) return;
    
    try {
      await deleteFornecedorProduto(fornecedorId);
      
      // Recarregar fornecedores
      const fornRes = await getFornecedoresProduto(id);
      setFornecedores(fornRes.data);
      
      alert('Fornecedor desvinculado!');
    } catch (error) {
      console.error('Erro ao desvincular fornecedor:', error);
      alert('Erro ao desvincular fornecedor');
    }
  };
  
  // ============================================
  // FUNÇÕES DE GERENCIAMENTO DE KIT/COMPOSIÇÃO
  // ============================================
  
  // Carregar produtos disponíveis para compor o kit
  const carregarProdutosDisponiveis = async () => {
    try {
      const response = await api.get('/produtos', {
        params: {
          apenas_ativos: true,
          tipo_produto: 'SIMPLES', // Só produtos simples podem ser componentes
        }
      });
      // Backend retorna objeto paginado: {items: [...], total: 0, page: 1}
      setProdutosDisponiveis(response.data.items || []);
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
      setProdutosDisponiveis([]);
    }
  };
  
  // Adicionar produto à composição do kit
  const adicionarProdutoKit = () => {
    if (!produtoKitSelecionado || !quantidadeKit || quantidadeKit <= 0) {
      alert('Selecione um produto e informe a quantidade!');
      return;
    }
    
    // Verificar se já existe
    const jaExiste = formData.composicao_kit.find(
      item => item.produto_id === parseInt(produtoKitSelecionado)
    );
    
    if (jaExiste) {
      alert('Este produto já foi adicionado ao kit!');
      return;
    }
    
    const produtoSelecionado = produtosDisponiveis.find(
      p => p.id === parseInt(produtoKitSelecionado)
    );
    
    const novoItem = {
      produto_componente_id: produtoSelecionado.id, // Backend espera produto_componente_id
      produto_id: produtoSelecionado.id, // Mantém para exibição no frontend
      produto_nome: produtoSelecionado.nome,
      produto_sku: produtoSelecionado.codigo,
      quantidade: parseFloat(quantidadeKit),
      estoque_componente: produtoSelecionado.estoque_atual || 0,
    };
    
    setFormData(prev => ({
      ...prev,
      composicao_kit: [...prev.composicao_kit, novoItem]
    }));
    
    // Limpar seleção
    setProdutoKitSelecionado('');
    setQuantidadeKit('');
    
    // Recalcular estoque virtual
    calcularEstoqueVirtualKit([...formData.composicao_kit, novoItem]);
  };
  
  // Remover produto da composição
  const removerProdutoKit = (produtoId) => {
    const novaComposicao = formData.composicao_kit.filter(
      item => item.produto_id !== produtoId
    );
    
    setFormData(prev => ({
      ...prev,
      composicao_kit: novaComposicao
    }));
    
    calcularEstoqueVirtualKit(novaComposicao);
  };
  
  // Calcular estoque virtual do kit baseado nos componentes
  const calcularEstoqueVirtualKit = (composicao) => {
    if (!composicao || composicao.length === 0) {
      setEstoqueVirtualKit(0);
      return;
    }
    
    // Calcular quantos kits podem ser montados com cada componente
    const possibilidades = composicao.map(item => {
      const estoqueComponente = item.estoque_componente || 0;
      const quantidadeNecessaria = item.quantidade || 1;
      return Math.floor(estoqueComponente / quantidadeNecessaria);
    });
    
    // O estoque do kit é o MENOR valor (gargalo)
    const estoqueMin = Math.min(...possibilidades);
    setEstoqueVirtualKit(estoqueMin >= 0 ? estoqueMin : 0);
  };
  
  // Carregar produtos quando abrir a aba de composição
  useEffect(() => {
    // Carregar se for KIT ou VARIACAO-KIT
    const ehKit = formData.tipo_produto === 'KIT' || (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit);
    
    if (abaAtiva === 9 && ehKit) {
      carregarProdutosDisponiveis();
      if (formData.composicao_kit && formData.composicao_kit.length > 0) {
        calcularEstoqueVirtualKit(formData.composicao_kit);
      }
    }
  }, [abaAtiva, formData.tipo_produto, formData.tipo_kit]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // ValidaÃ§Ãµes bÃ¡sicas
    if (!formData.nome) {
      alert('Preencha o campo Nome');
      return;
    }
    
    // Produto PAI não precisa de preço
    if (formData.tipo_produto !== 'PAI' && !formData.preco_venda) {
      alert('Preencha o Preço de Venda');
      return;
    }

    if (!formData.codigo && !formData.sku) {
      alert('Preencha o campo SKU/Código');
      return;
    }

    try {
      setSalvando(true);
      
      // Preparar dados para envio
      const dados = {
        codigo: formData.codigo || formData.sku, // Usar codigo ou sku
        nome: formData.nome,
        descricao_curta: formData.descricao || null,
        codigo_barras: formData.codigo_barras || null,
        unidade: formData.unidade || 'UN',
        preco_custo: formData.preco_custo ? parseFloat(formData.preco_custo) : 0,
        preco_venda: parseFloat(formData.preco_venda),
        preco_promocional: formData.preco_promocional ? parseFloat(formData.preco_promocional) : null,
        promocao_inicio: formData.data_inicio_promocao || null,
        promocao_fim: formData.data_fim_promocao || null,
        controle_lote: formData.controle_lote || false,
        estoque_minimo: formData.estoque_minimo ? parseInt(formData.estoque_minimo) : 0,
        estoque_maximo: formData.estoque_maximo ? parseInt(formData.estoque_maximo) : null,
        // Apenas enviar IDs se nÃ£o forem vazios
        categoria_id: formData.categoria_id ? parseInt(formData.categoria_id) : null,
        marca_id: formData.marca_id ? parseInt(formData.marca_id) : null,
        departamento_id: formData.departamento_id ? parseInt(formData.departamento_id) : null,
        // Sprint 2: Tipo de produto (SIMPLES, PAI, KIT, VARIACAO)
        tipo_produto: formData.tipo_produto || 'SIMPLES',
        produto_pai_id: formData.produto_pai_id || null,
        // Kit/Composição (KIT ou VARIACAO-KIT)
        tipo_kit: (formData.tipo_produto === 'KIT' || (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)) 
          ? (formData.e_kit_fisico ? 'FISICO' : 'VIRTUAL') 
          : null,
        e_kit_fisico: (formData.tipo_produto === 'KIT' || (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)) 
          ? formData.e_kit_fisico 
          : null,
        composicao_kit: (formData.tipo_produto === 'KIT' || (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)) 
          ? formData.composicao_kit 
          : null,
        // Sistema Predecessor/Sucessor
        produto_predecessor_id: formData.produto_predecessor_id || null,
        motivo_descontinuacao: formData.motivo_descontinuacao || null,
        // ❌ Tributação: NÃO enviar mais para produtos (agora via Fiscal V2)
        // Recorrência (Fase 1)
        tem_recorrencia: formData.tem_recorrencia || false,
        tipo_recorrencia: formData.tem_recorrencia ? formData.tipo_recorrencia : null,
        intervalo_dias: formData.tem_recorrencia && formData.intervalo_dias ? parseInt(formData.intervalo_dias) : null,
        numero_doses: formData.tem_recorrencia && formData.numero_doses ? parseInt(formData.numero_doses) : null,
        especie_compativel: formData.tem_recorrencia ? formData.especie_compativel : null,
        observacoes_recorrencia: formData.tem_recorrencia ? formData.observacoes_recorrencia : null,
        // Ração - Calculadora (Fase 2)
        classificacao_racao: formData.classificacao_racao || null,
        peso_embalagem: formData.peso_embalagem ? parseFloat(formData.peso_embalagem) : null,
        tabela_nutricional: formData.tabela_nutricional || null,
        tabela_consumo: formData.tabela_consumo || null,
        categoria_racao: formData.categoria_racao || null,
        especies_indicadas: formData.especies_indicadas || null,
      };
      
      console.log('ðŸ“¤ Enviando dados para API:', dados);

      if (isEdicao) {
        // 💾 FISCAL V2: Salvar dados fiscais ANTES de atualizar produto
        await salvarFiscal({ id, tipo_produto: formData.tipo_produto });
        
        await updateProduto(id, dados);
        alert('Produto atualizado com sucesso!');
        navigate('/produtos');
      } else {
        const response = await createProduto(dados);
        const produtoId = response.data.id;
        
        // Se for produto PAI, redirecionar para edição (aba de variações)
        if (formData.tipo_produto === 'PAI') {
          alert('Produto PAI criado com sucesso! Agora cadastre as variações.');
          navigate(`/produtos/${produtoId}/editar?aba=variacoes`);
        } else {
          alert('Produto cadastrado com sucesso!');
          navigate('/produtos');
        }
      }
    } catch (error) {
      console.error('Erro ao salvar produto:', error);
      alert(error.response?.data?.detail || 'Erro ao salvar produto');
    } finally {
      setSalvando(false);
    }
  };

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
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-start">
          <div>
            <button
              onClick={() => {
                // Se for variação, voltar para o produto PAI
                if (formData.tipo_produto === 'VARIACAO' && formData.produto_pai_id) {
                  navigate(`/produtos/${formData.produto_pai_id}/editar?aba=8`);
                } else {
                  navigate('/produtos');
                }
              }}
              className="text-blue-600 hover:text-blue-800 mb-2 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Voltar
            </button>
            <h1 className="text-3xl font-bold text-gray-900">
              {isEdicao ? 'Editar Produto' : 'Novo Produto'}
            </h1>
          </div>
          <a
            href="/cadastros/categorias"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 border border-blue-200 flex items-center gap-2 text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Gerenciar Categorias
          </a>
        </div>
      </div>

      {/* Abas */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="flex gap-8">
          {[
            { id: 1, label: 'Características' },
            { id: 2, label: 'Imagens' },
            { id: 3, label: 'Estoque/Lotes' },
            { id: 4, label: 'Fornecedores' },
            { id: 5, label: 'Tributação' },
            { id: 6, label: '🔄 Recorrência' },
            { id: 7, label: '🥫 Ração' },
            // Aba de variações (aparece sempre que produto for PAI)
            ...(formData.tipo_produto === 'PAI' ? [{ id: 8, label: '📦 Variações' }] : []),
            // Aba de composição (aparece se produto for KIT OU se for VARIACAO com tipo_kit definido)
            ...(formData.tipo_produto === 'KIT' || (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit) ? [{ id: 9, label: '🧩 Composição' }] : []),
          ].map((aba) => (
            <button
              key={aba.id}
              onClick={() => setAbaAtiva(aba.id)}
              className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                abaAtiva === aba.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {aba.label}
            </button>
          ))}
        </nav>
      </div>

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
                  placeholder="Ex: RaÃ§Ã£o Golden para CÃ£es Adultos 15kg"
                  required
                />
              </div>

              {/* Linha 3: ClassificaÃ§Ã£o */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
                      value={formData.preco_custo ? `R$ ${Number(formData.preco_custo).toFixed(2).replace('.', ',')}` : 'R$ 0,00'}
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d,]/g, '').replace(',', '.');
                        handleChange('preco_custo', value);
                      }}
                      onFocus={(e) => {
                        if (formData.preco_custo) {
                          e.target.value = Number(formData.preco_custo).toFixed(2).replace('.', ',');
                          e.target.select();
                        }
                      }}
                      onBlur={(e) => {
                        const value = e.target.value.replace(',', '.');
                        handleChange('preco_custo', value);
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
                      value={formData.markup ? `${Number(formData.markup).toFixed(2).replace('.', ',')}%` : '0,00%'}
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d,]/g, '').replace(',', '.');
                        handleChange('markup', value);
                      }}
                      onFocus={(e) => {
                        if (formData.markup) {
                          e.target.value = Number(formData.markup).toFixed(2).replace('.', ',');
                          e.target.select();
                        }
                      }}
                      onBlur={(e) => {
                        const value = e.target.value.replace(',', '.');
                        handleChange('markup', value);
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
                      value={formData.preco_venda ? `R$ ${Number(formData.preco_venda).toFixed(2).replace('.', ',')}` : 'R$ 0,00'}
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d,]/g, '').replace(',', '.');
                        handleChange('preco_venda', value);
                      }}
                      onFocus={(e) => {
                        if (formData.preco_venda) {
                          e.target.value = Number(formData.preco_venda).toFixed(2).replace('.', ',');
                          e.target.select();
                        }
                      }}
                      onBlur={(e) => {
                        const value = e.target.value.replace(',', '.');
                        handleChange('preco_venda', value);
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
                      value={formData.preco_promocional ? `R$ ${Number(formData.preco_promocional).toFixed(2).replace('.', ',')}` : 'R$ 0,00'}
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d,]/g, '').replace(',', '.');
                        handleChange('preco_promocional', value);
                      }}
                      onFocus={(e) => {
                        if (formData.preco_promocional) {
                          e.target.value = Number(formData.preco_promocional).toFixed(2).replace('.', ',');
                          e.target.select();
                        }
                      }}
                      onBlur={(e) => {
                        const value = e.target.value.replace(',', '.');
                        handleChange('preco_promocional', value);
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="R$ 0,00"
                    />
                  </div>
                </div>
              )}

              {/* Linha 6: Datas da PromoÃ§Ã£o */}
              {formData.preco_promocional && formData.tipo_produto !== 'PAI' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      InÃ­cio da PromoÃ§Ã£o
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
                      Fim da PromoÃ§Ã£o
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
                          onChange={(e) => {
                            setMostrarBuscaPredecessor(e.target.checked);
                            if (!e.target.checked) {
                              setPredecessorSelecionado(null);
                              handleChange('produto_predecessor_id', null);
                              handleChange('motivo_descontinuacao', '');
                            }
                          }}
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
                            onChange={async (e) => {
                              setBuscaPredecessor(e.target.value);
                              if (e.target.value.length >= 2) {
                                try {
                                  const response = await api.get('/produtos/', {
                                    params: { busca: e.target.value, page_size: 10 }
                                  });
                                  setProdutosBusca(response.data.items || []);
                                } catch (err) {
                                  console.error('Erro ao buscar produtos:', err);
                                }
                              } else {
                                setProdutosBusca([]);
                              }
                            }}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                          />
                          
                          {/* Resultados da Busca */}
                          {produtosBusca.length > 0 && (
                            <div className="mt-2 max-h-48 overflow-y-auto border border-gray-300 rounded-lg">
                              {produtosBusca.map(produto => (
                                <div
                                  key={produto.id}
                                  onClick={() => {
                                    setPredecessorSelecionado(produto);
                                    handleChange('produto_predecessor_id', produto.id);
                                    setBuscaPredecessor('');
                                    setProdutosBusca([]);
                                  }}
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
                                  onClick={() => {
                                    setPredecessorSelecionado(null);
                                    handleChange('produto_predecessor_id', null);
                                  }}
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
                            src={`http://localhost:8000${img.url}`}
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
          )}

          {/* ABA 5: TRIBUTAÇÃO */}
          {abaAtiva === 5 && (
            <div className="space-y-6">
              {/* 🏷️ FISCAL V2: Badge de Origem */}
              {isEdicao && formData.tributacao && (
                <div className="mb-4 flex gap-2">
                  {formData.tributacao.origem === 'produto_legado' && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-200 text-gray-800">
                      ⚪ Legado
                    </span>
                  )}
                  {(formData.tributacao.origem === 'produto_fiscal_v2' || formData.tributacao.origem === 'kit_fiscal_v2') && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-200 text-yellow-800">
                      🟡 Personalizado
                    </span>
                  )}
                  {formData.tributacao.herdado_da_empresa && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-200 text-blue-800">
                      🔵 Herdado da empresa
                    </span>
                  )}
                </div>
              )}

              {/* 🔒 Aviso e botão de personalização quando fiscal é herdado */}
              {isEdicao && formData.tributacao?.herdado_da_empresa === true && (
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4">
                  <div className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3 flex-1">
                      <p className="text-sm text-blue-700">
                        Esta configuração fiscal está sendo herdada da empresa. Para editar, personalize o fiscal deste produto.
                      </p>
                      <div className="mt-3">
                        <button
                          type="button"
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-yellow-600 hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                          onClick={() =>
                            setFormData((prev) => ({
                              ...prev,
                              tributacao: {
                                ...prev.tributacao,
                                herdado_da_empresa: false,
                              },
                            }))
                          }
                        >
                          ✏️ Personalizar fiscal deste produto
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Origem
                    <span
                      className="tooltip-icon"
                      title="Define se o produto é nacional ou importado. Impacta o cálculo do ICMS."
                    >
                      🛈
                    </span>
                  </label>
                  <select
                    value={formData.tributacao?.origem_mercadoria || '0'}
                    onChange={(e) => setFormData(prev => ({ ...prev, tributacao: { ...prev.tributacao, origem_mercadoria: e.target.value } }))}
                    disabled={formData.tributacao?.herdado_da_empresa === true}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    <option value="0">0 - Nacional</option>
                    <option value="1">1 - Estrangeira (Importação direta)</option>
                    <option value="2">2 - Estrangeira (Adquirida no mercado interno)</option>
                    <option value="3">3 - Nacional (&gt; 40% conteúdo importado)</option>
                    <option value="4">4 - Nacional (Conforme processo produtivo básico)</option>
                    <option value="5">5 - Nacional (&lt; 40% conteúdo importado)</option>
                    <option value="6">6 - Estrangeira (Importação direta sem similar)</option>
                    <option value="7">7 - Estrangeira (Mercado interno sem similar)</option>
                    <option value="8">8 - Nacional (&gt; 70% conteúdo importado)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    NCM
                    <span
                      className="tooltip-icon"
                      title="Nomenclatura Comum do Mercosul. Classificação fiscal do produto, base para impostos."
                    >
                      🛈
                    </span>
                  </label>
                  <input
                    type="text"
                    value={formData.tributacao?.ncm || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, tributacao: { ...prev.tributacao, ncm: e.target.value } }))}
                    disabled={formData.tributacao?.herdado_da_empresa === true}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="00000000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    CEST
                    <span
                      className="tooltip-icon"
                      title="Código Especificador da Substituição Tributária. Para produtos sujeitos a ICMS ST."
                    >
                      🛈
                    </span>
                  </label>
                  <input
                    type="text"
                    value={formData.tributacao?.cest || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, tributacao: { ...prev.tributacao, cest: e.target.value } }))}
                    disabled={formData.tributacao?.herdado_da_empresa === true}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="0000000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    CFOP
                    <span
                      className="tooltip-icon"
                      title="Código Fiscal de Operações e Prestações. Define a natureza da operação de venda."
                    >
                      🛈
                    </span>
                  </label>
                  <input
                    type="text"
                    value={formData.tributacao?.cfop || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, tributacao: { ...prev.tributacao, cfop: e.target.value } }))}
                    disabled={formData.tributacao?.herdado_da_empresa === true}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="0000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Alíquota ICMS (%)
                    <span
                      className="tooltip-icon"
                      title="Imposto sobre Circulação de Mercadorias. Alíquota estadual aplicada na venda. Impacta o preço final."
                    >
                      🛈
                    </span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.tributacao?.icms_aliquota || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, tributacao: { ...prev.tributacao, icms_aliquota: e.target.value } }))}
                    disabled={formData.tributacao?.herdado_da_empresa === true}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="0,00"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Alíquota PIS (%)
                    <span
                      className="tooltip-icon"
                      title="Programa de Integração Social. Contribuição federal sobre a venda. Geralmente 1,65%."
                    >
                      🛈
                    </span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.tributacao?.pis_aliquota || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, tributacao: { ...prev.tributacao, pis_aliquota: e.target.value } }))}
                    disabled={formData.tributacao?.herdado_da_empresa === true}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="0,00"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Alíquota COFINS (%)
                    <span
                      className="tooltip-icon"
                      title="Contribuição para Financiamento da Seguridade Social. Contribuição federal sobre a venda. Geralmente 7,6%."
                    >
                      🛈
                    </span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.tributacao?.cofins_aliquota || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, tributacao: { ...prev.tributacao, cofins_aliquota: e.target.value } }))}
                    disabled={formData.tributacao?.herdado_da_empresa === true}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="0,00"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ABA 6: RECORRÊNCIA */}
          {abaAtiva === 6 && (
            <div className="space-y-6">
              <div className="bg-purple-50 border-l-4 border-purple-500 p-4 mb-6">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-purple-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-purple-800">Sistema de Recorrência (Fase 1)</h3>
                    <div className="mt-2 text-sm text-purple-700">
                      <p>Configure produtos que precisam ser recomprados periodicamente (vacinas, antipulgas, rações).</p>
                      <p className="mt-1">O sistema criará lembretes automáticos para notificar clientes 7 dias antes.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Ativar Recorrência */}
              <div className="flex items-center p-4 bg-gray-50 rounded-lg">
                <input
                  type="checkbox"
                  id="tem_recorrencia"
                  checked={formData.tem_recorrencia}
                  onChange={(e) => handleChange('tem_recorrencia', e.target.checked)}
                  className="h-5 w-5 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                />
                <label htmlFor="tem_recorrencia" className="ml-3">
                  <span className="text-base font-medium text-gray-900">Produto com Recorrência</span>
                  <p className="text-sm text-gray-500">Ativar lembretes automáticos para este produto</p>
                </label>
              </div>

              {formData.tem_recorrencia && (
                <div className="space-y-4 border-t pt-6">
                  {/* Tipo de Recorrência */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Tipo de Recorrência *
                      </label>
                      <select
                        value={formData.tipo_recorrencia}
                        onChange={(e) => {
                          handleChange('tipo_recorrencia', e.target.value);
                          // Auto-preencher intervalo_dias baseado no tipo
                          if (e.target.value === 'daily') handleChange('intervalo_dias', '1');
                          else if (e.target.value === 'weekly') handleChange('intervalo_dias', '7');
                          else if (e.target.value === 'monthly') handleChange('intervalo_dias', '30');
                          else if (e.target.value === 'yearly') handleChange('intervalo_dias', '365');
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      >
                        <option value="daily">Diária</option>
                        <option value="weekly">Semanal (7 dias)</option>
                        <option value="monthly">Mensal (30 dias)</option>
                        <option value="yearly">Anual (365 dias)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Intervalo (em dias) *
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={formData.intervalo_dias}
                        onChange={(e) => handleChange('intervalo_dias', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        placeholder="Ex: 30 (para Nexgard)"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Exemplos: Nexgard = 30, Vacina Anual = 365
                      </p>
                    </div>
                  </div>

                  {/* Número de Doses */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Número de Doses (opcional)
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={formData.numero_doses}
                      onChange={(e) => handleChange('numero_doses', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      placeholder="Ex: 3 (para vacina com 3 doses)"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      💉 Se vazio, será recorrente indefinidamente. Se preenchido (ex: 3), o sistema finalizará após a última dose.
                    </p>
                  </div>

                  {/* Espécie Compatível */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Compatibilidade por Espécie
                    </label>
                    <div className="flex gap-4">
                      <label className="flex items-center">
                        <input
                          type="radio"
                          name="especie_compativel"
                          value="both"
                          checked={formData.especie_compativel === 'both'}
                          onChange={(e) => handleChange('especie_compativel', e.target.value)}
                          className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-700">🐶🐱 Cães e Gatos</span>
                      </label>
                      <label className="flex items-center">
                        <input
                          type="radio"
                          name="especie_compativel"
                          value="dog"
                          checked={formData.especie_compativel === 'dog'}
                          onChange={(e) => handleChange('especie_compativel', e.target.value)}
                          className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-700">🐶 Apenas Cães</span>
                      </label>
                      <label className="flex items-center">
                        <input
                          type="radio"
                          name="especie_compativel"
                          value="cat"
                          checked={formData.especie_compativel === 'cat'}
                          onChange={(e) => handleChange('especie_compativel', e.target.value)}
                          className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-700">🐱 Apenas Gatos</span>
                      </label>
                    </div>
                  </div>

                  {/* Observações */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Observações / Instruções
                    </label>
                    <textarea
                      value={formData.observacoes_recorrencia}
                      onChange={(e) => handleChange('observacoes_recorrencia', e.target.value)}
                      rows="3"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      placeholder="Ex: Aplicar mensalmente no mesmo dia. Não atrasar mais de 5 dias."
                    />
                  </div>

                  {/* Preview do Lembrete */}
                  {formData.intervalo_dias && (
                    <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                      <h4 className="text-sm font-semibold text-purple-900 mb-2">📌 Preview do Lembrete</h4>
                      <div className="text-sm text-purple-700 space-y-1">
                        <p>✓ Cliente será notificado <strong>7 dias antes</strong> da próxima dose</p>
                        <p>✓ Intervalo configurado: <strong>{formData.intervalo_dias} dias</strong></p>
                        <p>✓ Após a compra, um novo lembrete será criado automaticamente</p>
                        {formData.especie_compativel !== 'both' && (
                          <p className="mt-2 text-purple-800">
                            ⚠️ Sistema validará se o pet é compatível na hora da venda
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ABA 7: RAÇÃO - CALCULADORA */}
          {abaAtiva === 7 && (
            <div className="space-y-6">
              <div className="bg-orange-50 border-l-4 border-orange-500 p-4 mb-6">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-orange-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-orange-800">Calculadora de Ração (Fase 2)</h3>
                    <div className="mt-2 text-sm text-orange-700">
                      <p>Configure informações de ração para usar na calculadora de duração e custo.</p>
                      <p className="mt-1">A IA usará esses dados para recomendar rações aos clientes.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Classificação e Peso */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Classificação da Ração
                  </label>
                  <select
                    value={formData.classificacao_racao}
                    onChange={(e) => handleChange('classificacao_racao', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  >
                    <option value="">Não é ração</option>
                    <option value="super_premium">Super Premium</option>
                    <option value="premium">Premium</option>
                    <option value="especial">Especial</option>
                    <option value="standard">Standard</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Peso da Embalagem (kg) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.peso_embalagem}
                    onChange={(e) => handleChange('peso_embalagem', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    placeholder="Ex: 15 (15kg)"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Necessário para calcular duração e custo/dia
                  </p>
                </div>
              </div>

              {/* Categoria e Espécies */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Categoria
                  </label>
                  <select
                    value={formData.categoria_racao}
                    onChange={(e) => handleChange('categoria_racao', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  >
                    <option value="">Selecione...</option>
                    <option value="filhote">Filhote</option>
                    <option value="adulto">Adulto</option>
                    <option value="senior">Senior (Idoso)</option>
                    <option value="gestante">Gestante</option>
                    <option value="light">Light (Obesidade)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Espécies Indicadas
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="especies_indicadas"
                        value="both"
                        checked={formData.especies_indicadas === 'both'}
                        onChange={(e) => handleChange('especies_indicadas', e.target.value)}
                        className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300"
                      />
                      <span className="ml-2 text-sm text-gray-700">🐶🐱 Ambos</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="especies_indicadas"
                        value="dog"
                        checked={formData.especies_indicadas === 'dog'}
                        onChange={(e) => handleChange('especies_indicadas', e.target.value)}
                        className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300"
                      />
                      <span className="ml-2 text-sm text-gray-700">🐶 Cães</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="especies_indicadas"
                        value="cat"
                        checked={formData.especies_indicadas === 'cat'}
                        onChange={(e) => handleChange('especies_indicadas', e.target.value)}
                        className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300"
                      />
                      <span className="ml-2 text-sm text-gray-700">🐱 Gatos</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Tabela Nutricional (JSON) - OCULTO - Usado apenas pelo sistema */}
              <input
                type="hidden"
                value={formData.tabela_nutricional}
              />

              {/* Tabela de Consumo da Embalagem - EDITOR VISUAL */}
              <div>
                <TabelaConsumoEditor
                  value={formData.tabela_consumo}
                  onChange={(value) => handleChange('tabela_consumo', value)}
                  pesoEmbalagem={parseFloat(formData.peso_embalagem) || null}
                />
              </div>

              {/* Preview */}
              {formData.peso_embalagem && formData.classificacao_racao && (
                <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
                  <h4 className="text-sm font-semibold text-orange-900 mb-2">📊 Preview da Calculadora</h4>
                  <div className="text-sm text-orange-700 space-y-1">
                    <p>✓ Peso: <strong>{formData.peso_embalagem}kg</strong></p>
                    <p>✓ Classificação: <strong>{formData.classificacao_racao.replace('_', ' ')}</strong></p>
                    {formData.categoria_racao && <p>✓ Categoria: <strong>{formData.categoria_racao}</strong></p>}
                    {formData.tabela_consumo && <p className="text-green-600">✓ Tabela de consumo configurada</p>}
                    {!formData.tabela_consumo && <p className="text-yellow-600">⚠️ Sem tabela de consumo (usará cálculo genérico)</p>}
                    <p className="mt-2 text-orange-800">
                      💡 Use a Calculadora de Ração para ver duração e custo/dia
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* ABA 8: VARIAÇÕES (Sprint 2) - Apenas para produtos PAI */}
          {abaAtiva === 8 && formData.tipo_produto === 'PAI' && (
            <div className="space-y-6">
              {!isEdicao ? (
                /* Mensagem quando produto ainda não foi salvo */
                <div className="text-center py-16 border-2 border-dashed border-yellow-300 rounded-lg bg-yellow-50">
                  <svg className="mx-auto h-16 w-16 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <p className="mt-4 text-xl font-semibold text-yellow-900">Aba Bloqueada</p>
                  <p className="mt-2 text-sm text-yellow-800">
                    Salve o produto primeiro para habilitar o cadastro de variações.
                  </p>
                  <p className="mt-4 text-xs text-yellow-700">
                    Após salvar, você será redirecionado automaticamente para cadastrar as variações.
                  </p>
                </div>
              ) : (
                <>
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h3 className="text-lg font-semibold text-blue-900 mb-2">
                      Variações do Produto: {formData.nome}
                    </h3>
                    <p className="text-sm text-blue-700">
                      Cadastre as variações deste produto. Cada variação é um produto vendável independente 
                      com seu próprio SKU, preço e estoque.
                    </p>
                  </div>

                  {/* Grid de Variações Cadastradas */}
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="text-md font-semibold">Variações Cadastradas</h4>
                      <button
                        type="button"
                        onClick={() => setMostrarFormVariacao(!mostrarFormVariacao)}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        {mostrarFormVariacao ? '❌ Cancelar' : '➕ Nova Variação'}
                      </button>
                    </div>

                    {/* Formulário de Nova Variação */}
                    {mostrarFormVariacao && (
                      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-4">
                        <h5 className="font-semibold mb-3">Cadastrar Nova Variação</h5>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              SKU *
                            </label>
                            <input
                              type="text"
                              value={novaVariacao.sku}
                              onChange={(e) => setNovaVariacao({...novaVariacao, sku: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                              placeholder="Ex: PROD001-P"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Nome Complementar *
                            </label>
                            <input
                              type="text"
                              value={novaVariacao.nome}
                              onChange={(e) => setNovaVariacao({...novaVariacao, nome: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                              placeholder="Ex: Tamanho P"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Código de Barras
                            </label>
                            <input
                              type="text"
                              value={novaVariacao.codigo_barras}
                              onChange={(e) => setNovaVariacao({...novaVariacao, codigo_barras: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                              placeholder="EAN-13"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Preço de Custo
                            </label>
                            <input
                              type="number"
                              step="0.01"
                              value={novaVariacao.preco_custo}
                              onChange={(e) => setNovaVariacao({...novaVariacao, preco_custo: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                              placeholder="0.00"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Preço de Venda *
                            </label>
                            <input
                              type="number"
                              step="0.01"
                              value={novaVariacao.preco_venda}
                              onChange={(e) => setNovaVariacao({...novaVariacao, preco_venda: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                              placeholder="0.00"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Estoque Mínimo
                            </label>
                            <input
                              type="number"
                              value={novaVariacao.estoque_minimo}
                              onChange={(e) => setNovaVariacao({...novaVariacao, estoque_minimo: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                              placeholder="0"
                            />
                          </div>
                        </div>
                        
                        {/* REGRA OFICIAL: VARIACAO pode ser KIT */}
                        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                          <label className="flex items-start gap-3 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={novaVariacao.e_kit}
                              onChange={(e) => setNovaVariacao({...novaVariacao, e_kit: e.target.checked})}
                              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <div>
                              <span className="font-medium text-gray-900">🧩 Esta variação é um KIT (possui composição)</span>
                              <p className="text-sm text-gray-600 mt-1">
                                Se marcado, você poderá definir a composição do kit após salvar a variação.
                              </p>
                            </div>
                          </label>
                        </div>
                        
                        <div className="mt-4 flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setMostrarFormVariacao(false);
                              setNovaVariacao({
                                sku: '',
                                nome: '',
                                codigo_barras: '',
                                preco_custo: '',
                                preco_venda: '',
                                estoque_minimo: 0,
                                e_kit: false,
                                e_kit_fisico: false,
                                composicao_kit: []
                              });
                            }}
                            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                          >
                            Cancelar
                          </button>
                          <button
                            type="button"
                            onClick={async () => {
                              // Validações
                              if (!novaVariacao.sku || !novaVariacao.nome || !novaVariacao.preco_venda) {
                                alert('Preencha SKU, Nome e Preço de Venda');
                                return;
                              }
                              
                              try {
                                // Criar variação via API
                                const dadosVariacao = {
                                  codigo: novaVariacao.sku,
                                  nome: `${formData.nome} - ${novaVariacao.nome}`,
                                  codigo_barras: novaVariacao.codigo_barras || null,
                                  preco_custo: parseFloat(novaVariacao.preco_custo) || 0,
                                  preco_venda: parseFloat(novaVariacao.preco_venda),
                                  estoque_minimo: parseInt(novaVariacao.estoque_minimo) || 0,
                                  tipo_produto: 'VARIACAO',
                                  produto_pai_id: parseInt(id),
                                  categoria_id: formData.categoria_id || null,
                                  marca_id: formData.marca_id || null,
                                  unidade: formData.unidade || 'UN',
                                };
                                
                                // REGRA OFICIAL: VARIACAO pode ser KIT
                                if (novaVariacao.e_kit) {
                                  dadosVariacao.tipo_kit = 'VIRTUAL'; // Padrão: virtual (será configurado depois na aba composição)
                                  dadosVariacao.e_kit_fisico = false;
                                  dadosVariacao.composicao_kit = [];
                                }
                                
                                await createProduto(dadosVariacao);
                                
                                alert('Variação cadastrada com sucesso!');
                                setMostrarFormVariacao(false);
                                setNovaVariacao({
                                  sku: '',
                                  nome: '',
                                  codigo_barras: '',
                                  preco_custo: '',
                                  preco_venda: '',
                                  estoque_minimo: 0,
                                  e_kit: false,
                                  e_kit_fisico: false,
                                  composicao_kit: []
                                });
                                
                                // Recarregar variações
                                const response = await getProdutoVariacoes(id);
                                setVariacoes(response.data);
                              } catch (error) {
                                console.error('Erro ao cadastrar variação:', error);
                                alert(error.response?.data?.detail || 'Erro ao cadastrar variação');
                              }
                            }}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                          >
                            Salvar Variação
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Tabela de Variações */}
                    {variacoes.length === 0 ? (
                      <div className="text-center py-8 border-2 border-dashed border-gray-300 rounded-lg">
                        <p className="text-gray-500">Nenhuma variação cadastrada ainda.</p>
                        <p className="text-sm text-gray-400 mt-1">Clique em "Nova Variação" para começar.</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código de Barras</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Custo</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Venda</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Estoque</th>
                              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {variacoes.map((variacao) => (
                              <tr key={variacao.id} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-sm font-medium text-gray-900">{variacao.codigo}</td>
                                <td className="px-4 py-3 text-sm text-gray-700">{variacao.nome}</td>
                                <td className="px-4 py-3 text-sm text-gray-600">{variacao.codigo_barras || '-'}</td>
                                <td className="px-4 py-3 text-sm text-right text-gray-900">
                                  R$ {(variacao.preco_custo || 0).toFixed(2)}
                                </td>
                                <td className="px-4 py-3 text-sm text-right text-gray-900 font-semibold">
                                  R$ {variacao.preco_venda.toFixed(2)}
                                </td>
                                <td className="px-4 py-3 text-sm text-right">
                                  <span className={`font-semibold ${
                                    variacao.estoque_atual <= variacao.estoque_minimo 
                                      ? 'text-red-600' 
                                      : 'text-green-600'
                                  }`}>
                                    {variacao.estoque_atual || 0}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <button
                                    type="button"
                                    onClick={() => navigate(`/produtos/${variacao.id}/editar`)}
                                    className="text-blue-600 hover:text-blue-800 mr-2"
                                    title="Editar"
                                  >
                                    ✏️
                                  </button>
                                  <button
                                    type="button"
                                    onClick={async () => {
                                      if (!confirm(`Deseja excluir a variação ${variacao.nome}?`)) return;
                                      try {
                                        await deleteProduto(variacao.id);
                                        alert('Variação excluída com sucesso!');
                                        // Recarrega a lista completa
                                        const response = await getProdutoVariacoes(id);
                                        setVariacoes(response.data || []);
                                      } catch (error) {
                                        console.error('Erro ao excluir variação:', error);
                                        alert('Erro ao excluir variação');
                                      }
                                    }}
                                    className="text-red-600 hover:text-red-800"
                                    title="Excluir"
                                  >
                                    🗑️
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
          
          {/* ============================================
              ABA 9: COMPOSIÇÃO/KIT (Produto KIT ou VARIACAO-KIT)
              ============================================ */}
          {abaAtiva === 9 && (formData.tipo_produto === 'KIT' || (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)) && (
            <div className="space-y-6">
              {/* Escolha do tipo de estoque: Virtual ou Físico */}
              <div className="bg-white border-2 border-gray-300 rounded-lg p-5">
                <h3 className="font-semibold text-gray-900 mb-4">Tipo de Estoque do Kit</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Opção: Estoque Virtual */}
                  <div 
                    onClick={() => handleChange('e_kit_fisico', false)}
                    className={`cursor-pointer p-4 border-2 rounded-lg transition-all ${
                      !formData.e_kit_fisico 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-300 bg-white hover:border-blue-300'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="radio"
                        name="tipo_estoque_kit"
                        checked={!formData.e_kit_fisico}
                        onChange={() => handleChange('e_kit_fisico', false)}
                        className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">📊</span>
                          <h4 className="font-semibold text-gray-900">Estoque Virtual</h4>
                        </div>
                        <p className="text-sm text-gray-600 mt-2">
                          O estoque é calculado <strong>automaticamente</strong> com base nos componentes disponíveis.
                        </p>
                        <div className="mt-2 text-xs text-gray-500 space-y-1">
                          <div>✓ Não permite movimentação manual</div>
                          <div>✓ Estoque = menor disponibilidade dos componentes</div>
                          <div>✓ Ideal para kits montados sob demanda</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Opção: Estoque Físico */}
                  <div 
                    onClick={() => handleChange('e_kit_fisico', true)}
                    className={`cursor-pointer p-4 border-2 rounded-lg transition-all ${
                      formData.e_kit_fisico 
                        ? 'border-green-500 bg-green-50' 
                        : 'border-gray-300 bg-white hover:border-green-300'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="radio"
                        name="tipo_estoque_kit"
                        checked={formData.e_kit_fisico}
                        onChange={() => handleChange('e_kit_fisico', true)}
                        className="mt-1 h-4 w-4 text-green-600 focus:ring-green-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">📦</span>
                          <h4 className="font-semibold text-gray-900">Estoque Físico</h4>
                        </div>
                        <p className="text-sm text-gray-600 mt-2">
                          O kit possui estoque <strong>próprio e independente</strong> dos componentes.
                        </p>
                        <div className="mt-2 text-xs text-gray-500 space-y-1">
                          <div>✓ Permite movimentação manual</div>
                          <div>✓ Entrada: diminui componentes (montou kits)</div>
                          <div>✓ Ideal para kits pré-montados</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <svg className="w-6 h-6 text-purple-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                  <div>
                    <h3 className="font-semibold text-gray-900">Composição do Kit</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Defina quais produtos compõem este kit e as quantidades necessárias de cada um.
                    </p>
                    {!formData.e_kit_fisico && (
                      <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
                        <strong>📊 Estoque Virtual Ativo</strong>
                        <br />
                        O estoque deste kit será calculado automaticamente baseado nos componentes.
                        <br />
                        <span className="text-xs italic">
                          Estoque do kit = menor disponibilidade entre os componentes (considerando as quantidades necessárias)
                        </span>
                      </div>
                    )}
                    {formData.e_kit_fisico && (
                      <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                        <strong>📦 Estoque Físico Ativo</strong>
                        <br />
                        <strong>Entrada no kit:</strong> Os componentes serão automaticamente DIMINUÍDOS (unitários viraram kit).
                        <br />
                        <strong>Saída manual:</strong> Você poderá escolher se os componentes voltam ao estoque (desfez o kit) ou não (perda/roubo).
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Estoque Virtual Calculado */}
              {!formData.e_kit_fisico && formData.composicao_kit.length > 0 && (
                <div className="bg-white border-2 border-green-300 rounded-lg p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-medium text-gray-700">Estoque Virtual do Kit</h4>
                      <p className="text-xs text-gray-500 mt-1">Calculado automaticamente</p>
                    </div>
                    <div className="text-right">
                      <div className="text-4xl font-bold text-green-600">
                        {estoqueVirtualKit}
                      </div>
                      <p className="text-xs text-gray-500">kits disponíveis</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Formulário para adicionar produto */}
              <div className="border border-gray-300 rounded-lg p-5 bg-gray-50">
                <h4 className="font-semibold text-gray-900 mb-4">Adicionar Produto ao Kit</h4>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Produto
                    </label>
                    <select
                      value={produtoKitSelecionado}
                      onChange={(e) => setProdutoKitSelecionado(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="">Selecione um produto...</option>
                      {produtosDisponiveis.map(produto => (
                        <option key={produto.id} value={produto.id}>
                          [{produto.codigo}] {produto.nome} - Estoque: {produto.estoque_atual || 0}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Quantidade
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={quantidadeKit}
                      onChange={(e) => setQuantidadeKit(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="1"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={adicionarProdutoKit}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Adicionar ao Kit
                </button>
              </div>

              {/* Lista de Produtos no Kit */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Produtos no Kit ({formData.composicao_kit.length})</h4>
                
                {formData.composicao_kit.length === 0 ? (
                  <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                    </svg>
                    <p className="mt-2 text-sm text-gray-600">Nenhum produto adicionado ao kit ainda</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produto</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Quantidade</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estoque</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Kits Possíveis</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {formData.composicao_kit.map((item, index) => {
                          const kitsPossiveis = Math.floor(item.estoque_componente / item.quantidade);
                          const eGargalo = kitsPossiveis === estoqueVirtualKit && estoqueVirtualKit > 0;
                          
                          return (
                            <tr key={item.produto_id} className={`hover:bg-gray-50 ${eGargalo ? 'bg-yellow-50' : ''}`}>
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                {item.produto_sku || '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-700">
                                {item.produto_nome}
                                {eGargalo && (
                                  <span className="ml-2 text-xs bg-yellow-200 text-yellow-800 px-2 py-1 rounded">
                                    ⚠️ LIMITADOR
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm text-center text-gray-900 font-semibold">
                                {item.quantidade}
                              </td>
                              <td className="px-4 py-3 text-sm text-center text-gray-600">
                                {item.estoque_componente || 0}
                              </td>
                              <td className="px-4 py-3 text-sm text-center">
                                <span className={`font-semibold ${
                                  kitsPossiveis === 0 ? 'text-red-600' : 
                                  kitsPossiveis < 5 ? 'text-yellow-600' : 
                                  'text-green-600'
                                }`}>
                                  {kitsPossiveis}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-center">
                                <button
                                  type="button"
                                  onClick={() => removerProdutoKit(item.produto_id)}
                                  className="text-red-600 hover:text-red-800"
                                  title="Remover do kit"
                                >
                                  🗑️
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Alertas */}
              {formData.composicao_kit.length > 0 && estoqueVirtualKit === 0 && !formData.e_kit_fisico && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div className="text-sm text-red-800">
                      <strong>Kit sem estoque disponível!</strong>
                      <p className="mt-1">
                        Pelo menos um dos componentes está sem estoque suficiente para montar o kit.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Botões de Ação */}
        <div className="mt-6 flex justify-end gap-4">
          <button
            type="button"
            onClick={() => navigate('/produtos')}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={salvando}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
          >
            {salvando ? 'Salvando...' : isEdicao ? 'Atualizar' : 'Cadastrar'}
          </button>
        </div>
      </form>

      {/* Modal de Entrada de Estoque */}
      {modalEntrada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Nova Entrada de Estoque</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantidade *
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={entradaData.quantidade}
                  onChange={(e) => setEntradaData({...entradaData, quantidade: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex justify-between items-center">
                  <span>NÃºmero do Lote</span>
                  <button
                    type="button"
                    onClick={() => {
                      const sugestao = `LOTE-${new Date().toISOString().split('T')[0].replace(/-/g, '')}-${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`;
                      setEntradaData({...entradaData, nome_lote: sugestao});
                    }}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    Gerar SugestÃ£o
                  </button>
                </label>
                <input
                  type="text"
                  value={entradaData.nome_lote}
                  onChange={(e) => setEntradaData({...entradaData, nome_lote: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Ex: LOTE-20260105-001 (deixe vazio para gerar automaticamente)"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Data de Fabricação
                </label>
                <input
                  type="date"
                  value={entradaData.data_fabricacao}
                  onChange={(e) => setEntradaData({...entradaData, data_fabricacao: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Data de Validade
                </label>
                <input
                  type="date"
                  value={entradaData.data_validade}
                  onChange={(e) => setEntradaData({...entradaData, data_validade: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Preço de Custo *
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                  <input
                    type="number"
                    step="0.01"
                    value={entradaData.preco_custo}
                    onChange={(e) => setEntradaData({...entradaData, preco_custo: e.target.value})}
                    className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="0,00"
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setModalEntrada(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleEntradaEstoque}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Registrar Entrada
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Edição de Lote */}
      {modalEdicaoLote && loteEmEdicao && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Editar Lote</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome do Lote *
                </label>
                <input
                  type="text"
                  value={loteEmEdicao.nome_lote}
                  onChange={(e) => setLoteEmEdicao({...loteEmEdicao, nome_lote: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Nome do lote"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantidade *
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={loteEmEdicao.quantidade_inicial}
                  onChange={(e) => setLoteEmEdicao({...loteEmEdicao, quantidade_inicial: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Data de Fabricação
                </label>
                <input
                  type="date"
                  value={loteEmEdicao.data_fabricacao}
                  onChange={(e) => setLoteEmEdicao({...loteEmEdicao, data_fabricacao: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Data de Validade
                </label>
                <input
                  type="date"
                  value={loteEmEdicao.data_validade}
                  onChange={(e) => setLoteEmEdicao({...loteEmEdicao, data_validade: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Custo Unitário *
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={loteEmEdicao.custo_unitario}
                  onChange={(e) => setLoteEmEdicao({...loteEmEdicao, custo_unitario: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="0,00"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setModalEdicaoLote(false);
                  setLoteEmEdicao(null);
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSalvarEdicaoLote}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Salvar Alterações
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Fornecedor */}
      {modalFornecedor && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-gray-900 mb-4">
              {fornecedorEdit ? 'Editar Fornecedor' : 'Adicionar Fornecedor'}
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fornecedor *
                </label>
                <select
                  value={fornecedorData.fornecedor_id}
                  onChange={(e) => setFornecedorData({...fornecedorData, fornecedor_id: e.target.value})}
                  disabled={Boolean(fornecedorEdit)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                >
                  <option value="">Selecione...</option>
                  {clientes.map(cli => (
                    <option key={cli.id} value={cli.id}>{cli.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Código no Fornecedor
                </label>
                <input
                  type="text"
                  value={fornecedorData.codigo_fornecedor}
                  onChange={(e) => setFornecedorData({...fornecedorData, codigo_fornecedor: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="SKU-FORNECEDOR-001"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Preço de Custo
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                  <input
                    type="number"
                    step="0.01"
                    value={fornecedorData.preco_custo}
                    onChange={(e) => setFornecedorData({...fornecedorData, preco_custo: e.target.value})}
                    className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="0,00"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Prazo de Entrega (dias)
                </label>
                <input
                  type="number"
                  value={fornecedorData.prazo_entrega}
                  onChange={(e) => setFornecedorData({...fornecedorData, prazo_entrega: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="7"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Estoque no Fornecedor
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={fornecedorData.estoque_fornecedor}
                  onChange={(e) => setFornecedorData({...fornecedorData, estoque_fornecedor: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="100"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={fornecedorData.e_principal}
                  onChange={(e) => setFornecedorData({...fornecedorData, e_principal: e.target.checked})}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <label className="text-sm font-medium text-gray-700">
                  Fornecedor Principal
                </label>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setModalFornecedor(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSaveFornecedor}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

