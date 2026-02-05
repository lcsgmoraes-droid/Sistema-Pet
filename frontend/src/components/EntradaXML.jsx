import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { toast } from 'react-hot-toast';

const EntradaXML = () => {
  const navigate = useNavigate();
  const [notasEntrada, setNotasEntrada] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [notaSelecionada, setNotaSelecionada] = useState(null);
  const [mostrarDetalhes, setMostrarDetalhes] = useState(false);
  const [mostrarVisualizacao, setMostrarVisualizacao] = useState(false);
  
  // Estados para upload em lote
  const [uploadingLote, setUploadingLote] = useState(false);
  const [mostrarModalLote, setMostrarModalLote] = useState(false);
  const [resultadoLote, setResultadoLote] = useState(null);
  
  // Estados para histórico de preços
  const [mostrarHistoricoPrecos, setMostrarHistoricoPrecos] = useState(false);
  const [historicoPrecos, setHistoricoPrecos] = useState([]);
  const [produtoHistorico, setProdutoHistorico] = useState(null);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  
  // Estados para revisão de preços
  const [mostrarRevisaoPrecos, setMostrarRevisaoPrecos] = useState(false);
  const [previewProcessamento, setPreviewProcessamento] = useState(null);
  const [precosAjustados, setPrecosAjustados] = useState({});
  const [filtroCusto, setFiltroCusto] = useState('todos'); // 'todos', 'aumentou', 'diminuiu', 'igual'
  
  // Estados para rateio (APENAS informativo - estoque é UNIFICADO)
  const [tipoRateio, setTipoRateio] = useState('loja'); // 'online', 'loja', 'parcial'
  const [quantidadesOnline, setQuantidadesOnline] = useState({}); // {item_id: quantidade_online}
  
  // Estados para criar produto
  const [mostrarModalCriarProduto, setMostrarModalCriarProduto] = useState(false);
  const [itemSelecionadoParaCriar, setItemSelecionadoParaCriar] = useState(null);
  const [sugestaoSku, setSugestaoSku] = useState(null);
  const [carregandoSugestao, setCarregandoSugestao] = useState(false);
  const [formProduto, setFormProduto] = useState({
    sku: '',
    nome: '',
    descricao: '',
    preco_custo: '',
    preco_venda: '',
    margem_lucro: '',
    estoque_minimo: 10,
    estoque_maximo: 100
  });
  
  // Estado para filtro de pesquisa de produtos (por item)
  const [filtroProduto, setFiltroProduto] = useState({});

  useEffect(() => {
    console.log('🔄 [EntradaXML] Componente montado, iniciando carregamento...');
    carregarDados();
  }, []);

  const carregarDados = async () => {
    console.log('📊 [EntradaXML] Carregando dados...');
    try {
      const token = localStorage.getItem('token');
      console.log('🔑 [EntradaXML] Token obtido:', token ? 'SIM' : 'NÃO');
      const headers = { Authorization: `Bearer ${token}` };

      console.log('🌐 [EntradaXML] Fazendo requisições para:', {
        notasEntrada: `/notas-entrada/`,
        produtos: `/produtos/` // Sem filtro de ativo para trazer todos os produtos
      });

      const [notasRes, produtosRes] = await Promise.all([
        api.get(`/notas-entrada/`, { headers }),
        api.get(`/produtos/`, { headers, params: { ativo: null } }) // null = todos os produtos
      ]);

      console.log('✅ [EntradaXML] Dados carregados:', {
        notasEntrada: notasRes.data?.length || 0,
        produtos: produtosRes.data?.items?.length || produtosRes.data?.length || 0
      });

      const listaProdutos = produtosRes.data?.items || produtosRes.data;
      
      // Log para debug: contar produtos ativos vs inativos
      const produtosAtivos = listaProdutos.filter(p => p.ativo === true).length;
      const produtosInativos = listaProdutos.filter(p => p.ativo === false).length;
      
      console.log('📊 [EntradaXML] Produtos por status:', {
        ativos: produtosAtivos,
        inativos: produtosInativos,
        total: listaProdutos.length
      });

      setNotasEntrada(notasRes.data);
      setProdutos(listaProdutos);
    } catch (error) {
      console.error('❌ [EntradaXML] ERRO ao carregar dados:');
      console.error('  - Mensagem:', error.message);
      console.error('  - Response:', error.response?.data);
      console.error('  - Status:', error.response?.status);
      console.error('  - Stack:', error.stack);
      toast.error(`Erro ao carregar dados: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    console.log('📤 [EntradaXML] Upload iniciado');
    console.log('  - Arquivo selecionado:', file?.name);
    console.log('  - Tamanho:', file?.size, 'bytes');
    console.log('  - Tipo:', file?.type);
    
    if (!file) {
      console.warn('⚠️ [EntradaXML] Nenhum arquivo selecionado');
      return;
    }

    if (!file.name.toLowerCase().endsWith('.xml')) {
      console.error('❌ [EntradaXML] Arquivo não é XML:', file.name);
      toast.error('❌ Por favor, selecione um arquivo XML');
      return;
    }

    setUploadingFile(true);
    const formData = new FormData();
    formData.append('file', file);

    console.log('🚀 [EntradaXML] Enviando arquivo para:', `/notas-entrada/upload`);
    console.log('📦 [EntradaXML] FormData preparado:', file.name, file.size, 'bytes');

    try {
      const response = await api.post(`/notas-entrada/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('✅ [EntradaXML] Upload bem-sucedido!');
      console.log('  - Response data:', response.data);

      const itensVinculados = response.data.produtos_vinculados || 0;
      const totalItens = response.data.itens_total || 0;

      console.log(`📊 [EntradaXML] Produtos vinculados: ${itensVinculados}/${totalItens}`);

      // Mensagem de fornecedor criado
      if (response.data.fornecedor_criado_automaticamente) {
        toast.success(
          `🏢 Novo fornecedor cadastrado: ${response.data.fornecedor}`,
          { duration: 4000 }
        );
      }

      // Mensagem de produtos reativados
      if (response.data.produtos_reativados > 0) {
        toast.success(
          `♻️ ${response.data.produtos_reativados} produto(s) inativo(s) reativado(s) automaticamente`,
          { duration: 4000 }
        );
      }

      toast.success(
        `✅ NF-e ${response.data.numero_nota} processada! ${itensVinculados}/${totalItens} produtos vinculados automaticamente`,
        { duration: 5000 }
      );
      
      carregarDados();
      event.target.value = ''; // Limpar input
    } catch (error) {
      console.error('❌ [EntradaXML] ERRO no upload:');
      console.error('  - Mensagem:', error.message);
      console.error('  - Response data:', error.response?.data);
      console.error('  - Status:', error.response?.status);
      console.error('  - Headers:', error.response?.headers);
      console.error('  - Stack completo:', error.stack);
      
      const errorMsg = error.response?.data?.detail || error.message || 'Erro ao processar XML da NF-e';
      console.error('  - Mensagem para usuário:', errorMsg);
      
      toast.error(`❌ ${errorMsg}`);
    } finally {
      setUploadingFile(false);
      console.log('🏁 [EntradaXML] Upload finalizado');
    }
  };

  const handleMultipleFilesUpload = async (event) => {
    const files = Array.from(event.target.files);
    console.log('📦 [EntradaXML] Upload em lote iniciado -', files.length, 'arquivos');
    
    if (files.length === 0) {
      console.warn('⚠️ [EntradaXML] Nenhum arquivo selecionado');
      return;
    }

    // Validar se todos são XML
    const invalidFiles = files.filter(f => !f.name.toLowerCase().endsWith('.xml'));
    if (invalidFiles.length > 0) {
      toast.error(`❌ ${invalidFiles.length} arquivo(s) não são XML: ${invalidFiles.map(f => f.name).join(', ')}`);
      return;
    }

    setUploadingLote(true);
    setMostrarModalLote(true);
    setResultadoLote(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    console.log('🚀 [EntradaXML] Enviando', files.length, 'arquivos para:', `/notas-entrada/upload-lote`);

    try {
            const response = await api.post(`/notas-entrada/upload-lote`, formData);

      console.log('✅ [EntradaXML] Upload em lote bem-sucedido!');
      console.log('  - Response:', response.data);

      setResultadoLote(response.data);
      
      if (response.data.sucessos > 0) {
        toast.success(
          `✅ ${response.data.sucessos}/${response.data.total_arquivos} nota(s) processada(s) com sucesso!`,
          { duration: 5000 }
        );
      }
      
      if (response.data.erros > 0) {
        toast.error(
          `⚠️ ${response.data.erros}/${response.data.total_arquivos} nota(s) com erro`,
          { duration: 5000 }
        );
      }
      
      carregarDados();
      event.target.value = ''; // Limpar input
    } catch (error) {
      console.error('❌ [EntradaXML] ERRO no upload em lote:', error);
      toast.error(`❌ Erro ao processar lote: ${error.response?.data?.detail || error.message}`);
      setMostrarModalLote(false);
    } finally {
      setUploadingLote(false);
    }
  };

  const abrirDetalhes = async (notaId) => {
    try {
            const response = await api.get(`/notas-entrada/${notaId}`);
      setNotaSelecionada(response.data);
      setMostrarDetalhes(true);
      
      // Sincronizar estado de rateio
      setTipoRateio(response.data.tipo_rateio || 'loja');
    } catch (error) {
      toast.error('Erro ao carregar detalhes da nota');
    }
  };

  const abrirVisualizacao = async (notaId) => {
    try {
            const response = await api.get(`/notas-entrada/${notaId}`);
      setNotaSelecionada(response.data);
      setMostrarVisualizacao(true);
    } catch (error) {
      toast.error('Erro ao carregar nota');
    }
  };

  const vincularProduto = async (notaId, itemId, produtoId) => {
    try {
      await api.post(
        `/notas-entrada/${notaId}/itens/${itemId}/vincular?produto_id=${parseInt(produtoId)}`
      );
      
      toast.success('✅ Produto vinculado com sucesso!');
      
      // Recarregar detalhes
      const response = await api.get(`/notas-entrada/${notaId}`);
      setNotaSelecionada(response.data);
    } catch (error) {
      console.error('❌ Erro ao vincular produto:', error);
      toast.error(error.response?.data?.detail || 'Erro ao vincular produto');
    }
  };

  const salvarRateioItem = async (notaId, itemId, percentualOnline, percentualLoja) => {
    try {
      await api.post(`/notas-entrada/${notaId}/itens/${itemId}/rateio`, {
        percentual_online: parseFloat(percentualOnline),
        percentual_loja: parseFloat(percentualLoja)
      });
      
      toast.success('📊 Rateio configurado com sucesso!');
      
      // Recarregar detalhes
      const response = await api.get(`/notas-entrada/${notaId}`);
      setNotaSelecionada(response.data);
    } catch (error) {
      console.error('❌ Erro ao salvar rateio:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar rateio');
    }
  };

  const salvarTipoRateio = async (notaId, tipo) => {
    try {
      await api.post(`/notas-entrada/${notaId}/rateio`, {
        tipo_rateio: tipo
      });
      
      toast.success(`✅ Nota configurada: ${tipo === 'online' ? '100% Online' : tipo === 'loja' ? '100% Loja Física' : 'Rateio Parcial'}`);
      
      // Recarregar detalhes
      const response = await api.get(`/notas-entrada/${notaId}`);
      setNotaSelecionada(response.data);
      
      // Atualizar estado local para seleção visual
      setTipoRateio(tipo);
    } catch (error) {
      console.error('❌ Erro ao salvar tipo de rateio:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar tipo de rateio');
    }
  };

  const salvarQuantidadeOnlineItem = async (notaId, itemId, quantidadeOnline) => {
    try {
      const response = await api.post(`/notas-entrada/${notaId}/itens/${itemId}/rateio`, {
        quantidade_online: parseFloat(quantidadeOnline) || 0  // Permitir 0
      });
      
      toast.success('📊 Quantidade online configurada!');
      
      // Mostrar totais da nota
      const totais = response.data.nota_totais;
      toast.success(
        `Nota: ${totais.percentual_online.toFixed(1)}% Online (R$ ${totais.valor_online.toFixed(2)}) | ` +
        `${totais.percentual_loja.toFixed(1)}% Loja (R$ ${totais.valor_loja.toFixed(2)})`
      );
      
      // Atualizar apenas o item específico e os totais da nota, sem recarregar tudo
      setNotaSelecionada(prev => ({
        ...prev,
        percentual_online: totais.percentual_online,
        percentual_loja: totais.percentual_loja,
        valor_online: totais.valor_online,
        valor_loja: totais.valor_loja,
        itens: prev.itens.map(i => 
          i.id === itemId 
            ? { ...i, quantidade_online: parseFloat(quantidadeOnline) || 0 }
            : i
        )
      }));
      
      // Sincronizar estado local com valor salvo
      setQuantidadesOnline(prev => ({
        ...prev,
        [itemId]: parseFloat(quantidadeOnline) || 0
      }));
    } catch (error) {
      console.error('❌ Erro ao salvar quantidade online:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar');
    }
  };

  const processarNota = async (notaId) => {
    // Primeiro, buscar preview
    try {
            const response = await api.get(
        `/notas-entrada/${notaId}/preview-processamento`
      );
      
      setPreviewProcessamento(response.data);
      setMostrarRevisaoPrecos(true);
      
      // Inicializar preços ajustados com valores atuais
      const precosIniciais = {};
      response.data.itens.forEach(item => {
        precosIniciais[item.produto_id] = {
          preco_venda: item.preco_venda_atual,
          margem: item.margem_atual
        };
      });
      setPrecosAjustados(precosIniciais);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao carregar preview');
    }
  };

  const confirmarProcessamento = async () => {
    setLoading(true);
    try {
            // Atualizar preços se houver alterações
      const precosParaAtualizar = [];
      Object.entries(precosAjustados).forEach(([produtoId, dados]) => {
        const itemOriginal = previewProcessamento.itens.find(i => i.produto_id == produtoId);
        if (itemOriginal && dados.preco_venda !== itemOriginal.preco_venda_atual) {
          precosParaAtualizar.push({
            produto_id: parseInt(produtoId),
            preco_venda: dados.preco_venda
          });
        }
      });
      
      if (precosParaAtualizar.length > 0) {
        await api.post(
          `/notas-entrada/${previewProcessamento.nota_id}/atualizar-precos`,
          precosParaAtualizar
        );
      }
      
      // Processar a nota
      const response = await api.post(
        `/notas-entrada/${previewProcessamento.nota_id}/processar`,
        {}
      );

      toast.success(
        `✅ Nota processada! ${response.data.itens_processados} itens lançados no estoque`,
        { duration: 5000 }
      );
      
      setMostrarDetalhes(false);
      setNotaSelecionada(null);
      setMostrarRevisaoPrecos(false);
      setPreviewProcessamento(null);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao processar nota');
    } finally {
      setLoading(false);
    }
  };

  const calcularPrecoVenda = (custoNovo, margemDesejada) => {
    // Margem = (Preço Venda - Custo) / Preço Venda * 100
    // Preço Venda = Custo / (1 - Margem/100)
    if (margemDesejada >= 100) return custoNovo * 2;
    return custoNovo / (1 - margemDesejada / 100);
  };

  const calcularMargem = (precoVenda, custoNovo) => {
    // Margem = (Preço Venda - Custo) / Preço Venda * 100
    if (precoVenda <= 0) return 0;
    return ((precoVenda - custoNovo) / precoVenda) * 100;
  };

  const atualizarPrecoVenda = (produtoId, novoPreco, custoNovo) => {
    const novaMargem = calcularMargem(novoPreco, custoNovo);
    setPrecosAjustados(prev => ({
      ...prev,
      [produtoId]: {
        preco_venda: novoPreco,
        margem: novaMargem
      }
    }));
  };

  const atualizarMargem = (produtoId, novaMargem, custoNovo) => {
    const novoPreco = calcularPrecoVenda(custoNovo, novaMargem);
    setPrecosAjustados(prev => ({
      ...prev,
      [produtoId]: {
        preco_venda: novoPreco,
        margem: novaMargem
      }
    }));
  };

  const excluirNota = async (notaId, numeroNota) => {
    if (!confirm(`Tem certeza que deseja excluir a nota ${numeroNota}?`)) {
      return;
    }

    setLoading(true);
    try {
            await api.delete(`/notas-entrada/${notaId}`);

      toast.success('🗑️ Nota excluída com sucesso!');
      
      if (mostrarDetalhes) {
        setMostrarDetalhes(false);
        setNotaSelecionada(null);
      }
      
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao excluir nota');
    } finally {
      setLoading(false);
    }
  };

  const buscarHistoricoPrecos = async (produtoId, produtoNome) => {
    setCarregandoHistorico(true);
    setProdutoHistorico({ id: produtoId, nome: produtoNome });
    setMostrarHistoricoPrecos(true);
    
    try {
            const response = await api.get(
        `/produtos/${produtoId}/historico-precos`
      );
      
      setHistoricoPrecos(response.data);
    } catch (error) {
      toast.error('Erro ao carregar histórico de preços');
      setMostrarHistoricoPrecos(false);
    } finally {
      setCarregandoHistorico(false);
    }
  };

  const reverterNota = async (notaId, numeroNota) => {
    if (!confirm(`⚠️ Tem certeza que deseja REVERTER a entrada da nota ${numeroNota}?\n\nIsso irá:\n• Remover as quantidades do estoque\n• Excluir os lotes criados\n• Estornar as contas a pagar lançadas\n• Restaurar o status da nota para pendente`)) {
      return;
    }

    setLoading(true);
    try {
            const response = await api.post(
        `/notas-entrada/${notaId}/reverter`,
        {}
      );

      toast.success(
        `✅ Entrada revertida! ${response.data.itens_revertidos} produtos ajustados`,
        { duration: 5000 }
      );
      
      if (mostrarDetalhes) {
        setMostrarDetalhes(false);
        setNotaSelecionada(null);
      }
      
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao reverter entrada');
    } finally {
      setLoading(false);
    }
  };

  const desvincularProduto = async (itemId) => {
    if (!notaSelecionada) return;
    
    try {
      await api.post(
        `/notas-entrada/${notaSelecionada.id}/itens/${itemId}/desvincular`,
        {}
      );
      
      toast.success('✅ Produto desvinculado!');
      
      // Recarregar preview
      await carregarPreviewProcessamento(notaSelecionada.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao desvincular produto');
    }
  };

  const abrirModalVincularProduto = (item) => {
    setItemSelecionado(item);
    setMostrarModalVincular(true);
  };

  // Detectar divergências entre NF e produto vinculado
  const detectarDivergencias = (item) => {
    if (!item.produto_vinculado) return [];
    
    const divergencias = [];
    const descNF = item.descricao_nf.toLowerCase();
    const descProd = item.produto_vinculado.produto_nome.toLowerCase();
    
    // Detectar peso/tamanho
    const regexPeso = /(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|un|und|unid)/gi;
    const pesosNF = [...descNF.matchAll(regexPeso)];
    const pesosProd = [...descProd.matchAll(regexPeso)];
    
    if (pesosNF.length > 0 && pesosProd.length > 0) {
      const pesoNF = pesosNF[0][0];
      const pesoProd = pesosProd[0][0];
      if (pesoNF.toLowerCase() !== pesoProd.toLowerCase()) {
        divergencias.push({
          tipo: 'peso',
          mensagem: `Peso/Tamanho diferente: NF="${pesoNF}" vs Produto="${pesoProd}"`,
          gravidade: 'alta'
        });
      }
    }
    
    // Detectar cor
    const cores = ['preto', 'branco', 'vermelho', 'azul', 'verde', 'amarelo', 'rosa', 'roxo', 'laranja', 'marrom', 'cinza'];
    const corNF = cores.find(cor => descNF.includes(cor));
    const corProd = cores.find(cor => descProd.includes(cor));
    
    if (corNF && corProd && corNF !== corProd) {
      divergencias.push({
        tipo: 'cor',
        mensagem: `Cor diferente: NF="${corNF}" vs Produto="${corProd}"`,
        gravidade: 'media'
      });
    }
    
    // Detectar sabor (para rações)
    const sabores = ['frango', 'carne', 'peixe', 'cordeiro', 'salmao', 'atum', 'vegetais'];
    const saborNF = sabores.find(sabor => descNF.includes(sabor));
    const saborProd = sabores.find(sabor => descProd.includes(sabor));
    
    if (saborNF && saborProd && saborNF !== saborProd) {
      divergencias.push({
        tipo: 'sabor',
        mensagem: `Sabor diferente: NF="${saborNF}" vs Produto="${saborProd}"`,
        gravidade: 'alta'
      });
    }
    
    // Detectar animal (cachorro/gato)
    if ((descNF.includes('cao') || descNF.includes('cachorro') || descNF.includes('dog')) && 
        (descProd.includes('gato') || descProd.includes('cat'))) {
      divergencias.push({
        tipo: 'animal',
        mensagem: 'Animal diferente: NF parece ser para CACHORRO mas produto é para GATO',
        gravidade: 'critica'
      });
    }
    
    if ((descNF.includes('gato') || descNF.includes('cat')) && 
        (descProd.includes('cao') || descProd.includes('cachorro') || descProd.includes('dog'))) {
      divergencias.push({
        tipo: 'animal',
        mensagem: 'Animal diferente: NF parece ser para GATO mas produto é para CACHORRO',
        gravidade: 'critica'
      });
    }
    
    return divergencias;
  };

  const abrirModalCriarProduto = async (item) => {
    setItemSelecionadoParaCriar(item);
    setMostrarModalCriarProduto(true);
    setCarregandoSugestao(true);
    
    // Resetar formulário
    setFormProduto({
      sku: '',
      nome: '',
      descricao: '',
      preco_custo: '',
      preco_venda: '',
      margem_lucro: '',
      estoque_minimo: 10,
      estoque_maximo: 100
    });
    
    try {
            const response = await api.get(
        `/notas-entrada/${notaSelecionada.id}/itens/${item.id}/sugerir-sku`
      );
      
      setSugestaoSku(response.data);
      
      // Determinar qual SKU usar
      let skuParaUsar = response.data.sku_proposto || item.codigo_produto || 'PROD-' + item.id;
      
      // Se o SKU já existe, usar a primeira sugestão alternativa (a recomendada com ⭐)
      if (response.data.ja_existe && response.data.sugestoes && response.data.sugestoes.length > 0) {
        const sugestaoRecomendada = response.data.sugestoes.find(s => s.padrao) || response.data.sugestoes[0];
        skuParaUsar = sugestaoRecomendada.sku;
      }
      
      // Preencher formulário com dados do item
      setFormProduto({
        sku: skuParaUsar,
        nome: item.descricao || item.descricao_produto || 'Produto sem nome',
        descricao: item.descricao || item.descricao_produto || '',
        preco_custo: item.valor_unitario.toString(),
        preco_venda: (item.valor_unitario * 1.5).toFixed(2), // Sugestão de 50% de margem
        margem_lucro: '50',
        estoque_minimo: 10,
        estoque_maximo: 100
      });
      
      console.log('✅ Formulário preenchido:', {
        sku: skuParaUsar,
        nome: item.descricao,
        preco_custo: item.valor_unitario
      });
      
    } catch (error) {
      toast.error('Erro ao buscar sugestões de SKU');
      console.error('Erro ao buscar SKU:', error);
      
      // Preencher mesmo com erro
      setFormProduto({
        sku: item.codigo_produto || 'PROD-' + item.id,
        nome: item.descricao || 'Produto sem nome',
        descricao: item.descricao || '',
        preco_custo: item.valor_unitario.toString(),
        preco_venda: (item.valor_unitario * 1.5).toFixed(2),
        margem_lucro: '50',
        estoque_minimo: 10,
        estoque_maximo: 100
      });
    } finally {
      setCarregandoSugestao(false);
    }
  };

  const criarProdutoNovo = async () => {
    try {
      setLoading(true);
            // Preparar dados convertendo strings para números
      const dadosProduto = {
        ...formProduto,
        preco_custo: parseFloat(formProduto.preco_custo) || 0,
        preco_venda: parseFloat(formProduto.preco_venda) || 0,
        margem_lucro: parseFloat(formProduto.margem_lucro) || 0,
        estoque_minimo: parseInt(formProduto.estoque_minimo) || 10,
        estoque_maximo: parseInt(formProduto.estoque_maximo) || 100
      };
      
      const response = await api.post(
        `/notas-entrada/${notaSelecionada.id}/itens/${itemSelecionadoParaCriar.id}/criar-produto`,
        dadosProduto
      );
      
      toast.success(`✅ Produto ${response.data.produto.codigo} criado e vinculado!`);
      
      // Fechar modal
      setMostrarModalCriarProduto(false);
      setItemSelecionadoParaCriar(null);
      setSugestaoSku(null);
      
      // Recarregar dados
      await carregarDados();
      
      // Recarregar detalhes da nota
      const notaResponse = await api.get(
        `/notas-entrada/${notaSelecionada.id}`
      );
      setNotaSelecionada(notaResponse.data);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao criar produto');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const criarTodosProdutosNaoVinculados = async () => {
    const itensNaoVinculados = notaSelecionada.itens.filter(item => !item.produto_id);
    
    if (itensNaoVinculados.length === 0) {
      toast.success('Todos os produtos já estão vinculados!');
      return;
    }
    
    const confirmacao = window.confirm(
      `Criar ${itensNaoVinculados.length} produto(s) automaticamente?\n\n` +
      `Padrões aplicados:\n` +
      `• Estoque mínimo: 10\n` +
      `• Estoque máximo: 100\n` +
      `• Margem de lucro: 50%\n\n` +
      `Você poderá editar os produtos depois no cadastro.`
    );
    
    if (!confirmacao) return;
    
    try {
      setLoading(true);
      let sucessos = 0;
      let erros = 0;
      
      const loadingToast = toast.loading(`📦 Criando ${itensNaoVinculados.length} produtos...`);
      
      for (const item of itensNaoVinculados) {
        try {
          // Buscar SKU sugerido
          const skuResponse = await api.get(
            `/notas-entrada/${notaSelecionada.id}/itens/${item.id}/sugerir-sku`
          );
          
          let skuParaUsar = skuResponse.data.sku_proposto || item.codigo_produto || `PROD-${item.id}`;
          
          // Se já existe, usar primeira sugestão alternativa
          if (skuResponse.data.ja_existe && skuResponse.data.sugestoes?.length > 0) {
            const sugestaoRecomendada = skuResponse.data.sugestoes.find(s => s.padrao) || skuResponse.data.sugestoes[0];
            skuParaUsar = sugestaoRecomendada.sku;
          }
          
          // Criar produto com padrões
          const dadosProduto = {
            sku: skuParaUsar,
            nome: item.descricao || 'Produto sem nome',
            descricao: item.descricao || '',
            preco_custo: parseFloat(item.valor_unitario) || 0,
            preco_venda: parseFloat((item.valor_unitario * 1.5).toFixed(2)),
            margem_lucro: 50,
            estoque_minimo: 10,
            estoque_maximo: 100
          };
          
          await api.post(
            `/notas-entrada/${notaSelecionada.id}/itens/${item.id}/criar-produto`,
            dadosProduto
          );
          
          sucessos++;
        } catch (error) {
          console.error(`Erro ao criar produto do item ${item.id}:`, error);
          erros++;
        }
      }
      
      toast.dismiss(loadingToast);
      
      if (sucessos > 0) {
        toast.success(`✅ ${sucessos} produto(s) criado(s) com sucesso!`);
      }
      
      if (erros > 0) {
        toast.error(`❌ ${erros} erro(s) ao criar produtos`);
      }
      
      // Recarregar dados
      await carregarDados();
      
      // Recarregar detalhes da nota
      const notaResponse = await api.get(`/notas-entrada/${notaSelecionada.id}`);
      setNotaSelecionada(notaResponse.data);
      
    } catch (error) {
      toast.error('Erro ao criar produtos em lote');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const calcularMargemLucro = (custo, venda) => {
    if (custo === 0) return 0;
    return ((venda - custo) / custo * 100).toFixed(2);
  };

  // Funções para determinar cores baseadas em comparações
  const getCorComparacao = (valorNovo, valorAntigo, tipo) => {
    // Validações de segurança
    const novo = parseFloat(valorNovo) || 0;
    const antigo = parseFloat(valorAntigo) || 0;
    
    if (novo === antigo) {
      return { cor: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-300', label: '=' };
    }
    
    // Para custo: menor é melhor (verde), maior é pior (vermelho)
    if (tipo === 'custo') {
      return novo < antigo 
        ? { cor: 'text-green-600', bg: 'bg-green-50', border: 'border-green-300', label: '↓' }
        : { cor: 'text-red-600', bg: 'bg-red-50', border: 'border-red-300', label: '↑' };
    }
    
    // Para preço e margem: maior é melhor (verde), menor é pior (vermelho)
    return novo > antigo
      ? { cor: 'text-green-600', bg: 'bg-green-50', border: 'border-green-300', label: '↑' }
      : { cor: 'text-red-600', bg: 'bg-red-50', border: 'border-red-300', label: '↓' };
  };

  const getStatusBadge = (status) => {
    const styles = {
      pendente: 'bg-yellow-200 text-yellow-800',
      processada: 'bg-green-200 text-green-800',
      cancelada: 'bg-red-200 text-red-800',
      erro: 'bg-red-300 text-red-900'
    };
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${styles[status] || 'bg-gray-200'}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  const getConfiancaBadge = (confianca) => {
    if (!confianca) return <span className="text-gray-400 text-sm">Não vinculado</span>;
    
    const nivel = confianca >= 90 ? 'alta' : confianca >= 70 ? 'media' : 'baixa';
    const styles = {
      alta: 'bg-green-100 text-green-800',
      media: 'bg-yellow-100 text-yellow-800',
      baixa: 'bg-orange-100 text-orange-800'
    };
    
    return (
      <span className={`px-2 py-1 rounded text-xs font-semibold ${styles[nivel]}`}>
        {confianca.toFixed(1)}% {nivel === 'alta' ? '✅' : nivel === 'media' ? '⚠️' : '⚡'}
      </span>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">📄 Entrada por NF-e (XML)</h1>
        <p className="text-gray-600">Importe notas fiscais eletrônicas e vincule produtos automaticamente</p>
      </div>

      {/* Área de Upload */}
      <div className="bg-white rounded-lg shadow-md p-8 mb-6">
        <div className="text-center">
          <div className="mb-4">
            <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2">
            {uploadingFile ? '⏳ Processando XML...' : 'Selecione o arquivo XML da NF-e'}
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            O sistema irá processar automaticamente os dados da nota fiscal
          </p>
          
          {/* Botões de Upload */}
          <div className="flex gap-3 justify-center">
            {/* Upload Único */}
            <label className="inline-block">
              <input
                type="file"
                accept=".xml"
                onChange={handleFileUpload}
                disabled={uploadingFile || uploadingLote}
                className="hidden"
              />
              <span className={`
                px-6 py-3 rounded-lg font-semibold cursor-pointer inline-block
                ${(uploadingFile || uploadingLote)
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-blue-600 hover:bg-blue-700 text-white'}
              `}>
                {uploadingFile ? '⏳ Processando...' : '📁 Upload Único'}
              </span>
            </label>
            
            {/* Upload Múltiplo */}
            <label className="inline-block">
              <input
                type="file"
                accept=".xml"
                multiple
                onChange={handleMultipleFilesUpload}
                disabled={uploadingFile || uploadingLote}
                className="hidden"
              />
              <span className={`
                px-6 py-3 rounded-lg font-semibold cursor-pointer inline-block
                ${(uploadingFile || uploadingLote)
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-green-600 hover:bg-green-700 text-white'}
              `}>
                {uploadingLote ? '⏳ Processando Lote...' : '📦 Upload Múltiplo'}
              </span>
            </label>
          </div>
          
          <p className="text-xs text-gray-500 mt-3">
            Formatos aceitos: XML de NF-e (padrão SEFAZ)
          </p>
        </div>
      </div>

      {/* Estatísticas */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-blue-600">
            {notasEntrada.length}
          </div>
          <div className="text-sm text-gray-600">Total de Notas</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-yellow-600">
            {notasEntrada.filter(n => n.status === 'pendente').length}
          </div>
          <div className="text-sm text-gray-600">Pendentes</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-green-600">
            {notasEntrada.filter(n => n.status === 'processada').length}
          </div>
          <div className="text-sm text-gray-600">Processadas</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-purple-600">
            R$ {notasEntrada
              .filter(n => n.status === 'processada')
              .reduce((sum, n) => sum + (n.valor_total || 0), 0)
              .toFixed(2)}
          </div>
          <div className="text-sm text-gray-600">Valor Processado</div>
        </div>
      </div>

      {/* Lista de Notas */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50">
          <h2 className="text-lg font-semibold">Notas Fiscais Importadas</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">Chave NF-e</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Fornecedor</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Data Emissão</th>
                <th className="px-4 py-3 text-right text-sm font-semibold">Valor</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">Itens</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">Status</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">Ações</th>
              </tr>
            </thead>
            <tbody>
              {notasEntrada.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                    Nenhuma nota fiscal importada ainda. Faça o upload de um XML acima.
                  </td>
                </tr>
              ) : (
                notasEntrada.map(nota => (
                  <tr 
                    key={nota.id} 
                    onClick={() => abrirVisualizacao(nota.id)}
                    className="border-t hover:bg-blue-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="font-mono text-xs">{nota.chave_acesso.substring(0, 20)}...</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold">{nota.fornecedor_nome}</div>
                      <div className="text-xs text-gray-500">{nota.fornecedor_cnpj}</div>
                    </td>
                    <td className="px-4 py-3">{new Date(nota.data_emissao).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right font-semibold">R$ {(nota.valor_total || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-semibold">
                        {nota.produtos_vinculados + nota.produtos_nao_vinculados} itens
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">{getStatusBadge(nota.status)}</td>
                    <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-2 justify-center">
                        {nota.status === 'pendente' && (
                          <button
                            onClick={() => abrirDetalhes(nota.id)}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold text-sm"
                            title="Vincular produtos"
                          >
                            🔗 Vincular
                          </button>
                        )}
                        {nota.entrada_estoque_realizada ? (
                          <button
                            onClick={() => reverterNota(nota.id, nota.numero_nota)}
                            className="text-orange-600 hover:text-orange-800 font-semibold text-sm"
                            title="Reverter entrada no estoque"
                          >
                            ↩️ Reverter
                          </button>
                        ) : (
                          <button
                            onClick={() => excluirNota(nota.id, nota.numero_nota)}
                            className="text-red-600 hover:text-red-800 font-semibold text-sm"
                            title="Excluir nota"
                          >
                            🗑️ Excluir
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Detalhes */}
      {mostrarDetalhes && notaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
            {/* Cabeçalho */}
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">📄 Detalhes da NF-e</h2>
                <p className="text-sm text-gray-600">Chave: {notaSelecionada.chave_acesso}</p>
              </div>
              <button
                onClick={() => {
                  setMostrarDetalhes(false);
                  setNotaSelecionada(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>

            {/* Informações da Nota */}
            <div className="px-6 py-4 border-b bg-gray-50">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Fornecedor:</span>
                  <div className="font-semibold">{notaSelecionada.fornecedor_nome}</div>
                  <div className="text-xs text-gray-500">{notaSelecionada.fornecedor_cnpj}</div>
                  {notaSelecionada.fornecedor_id && (
                    <div className="text-xs text-green-600 mt-1">✅ Cadastrado</div>
                  )}
                </div>
                <div>
                  <span className="text-gray-600">Data Emissão:</span>
                  <div className="font-semibold">{new Date(notaSelecionada.data_emissao).toLocaleDateString()}</div>
                </div>
                <div>
                  <span className="text-gray-600">Valor Total:</span>
                  <div className="font-bold text-lg text-green-600">R$ {(notaSelecionada.valor_total || 0).toFixed(2)}</div>
                </div>
              </div>
            </div>

            {/* Alerta de Fornecedor Novo - Versão Compacta */}
            {notaSelecionada.fornecedor_id && notaSelecionada.fornecedor_criado_automaticamente && (
              <div className="px-6 py-2 bg-blue-50 border-b border-blue-200">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-blue-800">
                    <strong>{notaSelecionada.fornecedor_nome}</strong> foi cadastrado automaticamente.
                  </div>
                  <button
                    onClick={() => navigate(`/clientes/${notaSelecionada.fornecedor_id}`)}
                    className="px-3 py-1 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 text-xs"
                  >
                    📝 Completar Cadastro
                  </button>
                </div>
              </div>
            )}

            {/* Itens da Nota */}
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-xl text-gray-800">
                  📦 Produtos da Nota ({notaSelecionada.itens.length})
                </h3>
                
                {notaSelecionada.status === 'pendente' && 
                 notaSelecionada.itens.some(item => !item.produto_id) && (
                  <button
                    onClick={criarTodosProdutosNaoVinculados}
                    disabled={loading}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400 flex items-center gap-2 text-sm"
                    title="Cria automaticamente todos os produtos não vinculados com os padrões: Estoque mín: 10, máx: 100, Margem: 50%"
                  >
                    <span>✨ Criar Todos Não Vinculados</span>
                    <span className="text-xs bg-purple-800 px-2 py-0.5 rounded">
                      {notaSelecionada.itens.filter(i => !i.produto_id).length}
                    </span>
                  </button>
                )}
              </div>
              
              <div className="space-y-3">
                {notaSelecionada.itens.map(item => (
                  <div key={item.id} className="border-2 border-gray-400 rounded-lg p-4 bg-white shadow-sm">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1">
                        <div className="font-semibold text-lg">{item.descricao}</div>
                        <div className="text-sm text-gray-600 space-x-4">
                          <span>Código: <span className="font-mono">{item.codigo_produto}</span></span>
                          <span>NCM: <span className="font-mono">{item.ncm}</span></span>
                          {item.ean && item.ean !== 'SEM GTIN' && <span>EAN: <span className="font-mono">{item.ean}</span></span>}
                        </div>
                      </div>
                      {getConfiancaBadge(item.confianca_vinculo)}
                    </div>

                    <div className="grid grid-cols-4 gap-4 mb-3 text-sm">
                      <div>
                        <span className="text-gray-600">Quantidade:</span>
                        <div className="font-semibold">{item.quantidade}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">Valor Unit.:</span>
                        <div className="font-semibold">R$ {item.valor_unitario.toFixed(2)}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">Valor Total:</span>
                        <div className="font-semibold text-green-600">R$ {item.valor_total.toFixed(2)}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">CFOP:</span>
                        <div className="font-semibold">{item.cfop}</div>
                      </div>
                    </div>

                    {/* Lote e Validade */}
                    {(item.lote || item.data_validade) && (
                      <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
                        {item.lote && (
                          <div className="bg-purple-50 border border-purple-200 rounded p-2">
                            <span className="text-gray-600">📦 Lote:</span>
                            <div className="font-semibold text-purple-800">{item.lote}</div>
                          </div>
                        )}
                        {item.data_validade && (
                          <div className="bg-orange-50 border border-orange-200 rounded p-2">
                            <span className="text-gray-600">📅 Validade:</span>
                            <div className="font-semibold text-orange-800">
                              {new Date(item.data_validade).toLocaleDateString('pt-BR')}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Mostrar descrição completa do item da NF-e */}
                    {item.descricao && (
                      <div className="mb-3 p-2 bg-blue-50 rounded text-sm">
                        <span className="text-gray-600">📄 Descrição NF-e:</span>
                        <div className="font-semibold text-blue-900">{item.descricao}</div>
                      </div>
                    )}

                    {/* Vinculação de Produto */}
                    {notaSelecionada.status === 'pendente' && (
                      <div className="mt-3 pt-3 border-t">
                        {item.produto_id ? (
                          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                            <div className="flex items-center justify-between mb-2">
                              <div>
                                <span className="text-green-800 font-semibold">✅ Vinculado ao produto:</span>
                                <span className="ml-2">{item.produto_nome}</span>
                              </div>
                              <button
                                onClick={() => desvincularProduto(notaSelecionada.id, item.id)}
                                className="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-sm font-semibold"
                                title="Remover vinculação"
                              >
                                ❌ Desvincular
                              </button>
                            </div>
                            <div className="text-xs text-green-700 mb-2">
                              💡 Para alterar, selecione outro produto abaixo ou clique em desvincular
                            </div>
                            <select
                              value={item.produto_id}
                              onChange={(e) => {
                                if (e.target.value && e.target.value != item.produto_id) {
                                  vincularProduto(notaSelecionada.id, item.id, e.target.value);
                                }
                              }}
                              className="w-full px-3 py-1 border border-gray-300 rounded text-sm"
                            >
                              <option value={item.produto_id}>{item.produto_nome}</option>
                              {Array.isArray(produtos) && produtos
                                .filter(p => p.id !== item.produto_id)
                                .map(p => (
                                  <option key={p.id} value={p.id}>
                                    {p.codigo} - {p.nome} {p.descricao ? `| ${p.descricao.substring(0, 50)}...` : ''} (Est: {p.estoque_atual || 0})
                                  </option>
                                ))}
                            </select>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div className="text-orange-600 font-semibold">⚠️ Produto não vinculado - selecione manualmente:</div>
                            
                            {/* Campo de pesquisa */}
                            <input
                              type="text"
                              placeholder="🔍 Digite para pesquisar por nome ou SKU..."
                              value={filtroProduto[item.id] || ''}
                              onChange={(e) => setFiltroProduto({...filtroProduto, [item.id]: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                            />
                            
                            {/* Lista de produtos filtrados - só aparece quando digitar */}
                            {filtroProduto[item.id] && filtroProduto[item.id].length >= 2 && (
                              <div className="border border-gray-300 rounded max-h-60 overflow-y-auto">
                                {Array.isArray(produtos) && produtos
                                  .filter(p => {
                                    const filtro = filtroProduto[item.id].toLowerCase();
                                    return (
                                      p.nome?.toLowerCase().includes(filtro) ||
                                      p.codigo?.toLowerCase().includes(filtro) ||
                                      p.descricao?.toLowerCase().includes(filtro)
                                    );
                                  })
                                  .sort((a, b) => {
                                    // Produtos ativos aparecem primeiro
                                    if (a.ativo === b.ativo) return 0;
                                    return a.ativo ? -1 : 1;
                                  })
                                  .slice(0, 20) // Limitar a 20 resultados
                                  .map(p => (
                                    <button
                                      key={`produto-${item.id}-${p.id}`}
                                      type="button"
                                      onClick={() => {
                                        vincularProduto(notaSelecionada.id, item.id, p.id);
                                        setFiltroProduto({...filtroProduto, [item.id]: ''}); // Limpar apenas o filtro deste item
                                      }}
                                      className={`w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-200 last:border-b-0 text-sm ${!p.ativo ? 'text-red-600 font-bold' : ''}`}
                                    >
                                      {!p.ativo && '🔴 '}{p.codigo} - {p.nome} {p.descricao ? `| ${p.descricao.substring(0, 40)}...` : ''} 
                                      {!p.ativo && ' [INATIVO]'} 
                                      <span className="text-gray-500 ml-2">(Est: {p.estoque_atual || 0})</span>
                                    </button>
                                  ))}
                                {produtos.filter(p => {
                                  const filtro = filtroProduto[item.id].toLowerCase();
                                  return (
                                    p.nome?.toLowerCase().includes(filtro) ||
                                    p.codigo?.toLowerCase().includes(filtro) ||
                                    p.descricao?.toLowerCase().includes(filtro)
                                  );
                                }).length === 0 && (
                                  <div className="px-3 py-4 text-center text-gray-500">
                                    ❌ Nenhum produto encontrado
                                  </div>
                                )}
                              </div>
                            )}
                            
                            <div className="text-center text-sm text-gray-600">
                              ou
                            </div>
                            <button
                              onClick={() => abrirModalCriarProduto(item)}
                              className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700"
                            >
                              ➕ Produto não existe? Criar novo
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Rateio de Estoque (se modo PARCIAL) */}
                    {notaSelecionada.status === 'pendente' && 
                     tipoRateio === 'parcial' && 
                     item.produto_id && (
                      <div className="mt-3 pt-3 border-t">
                        <div className="bg-gray-50 border border-gray-300 rounded p-3">
                          <h4 className="font-medium text-gray-700 mb-2 flex items-center text-sm">
                            📦 Quantidade destinada ao estoque online
                          </h4>
                          
                          <div className="grid grid-cols-3 gap-3">
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">
                                Total NF
                              </label>
                              <input
                                type="number"
                                value={item.quantidade}
                                disabled
                                className="w-full px-2 py-1.5 border border-gray-300 rounded bg-gray-100 text-sm font-medium"
                              />
                            </div>
                            
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">
                                🌐 Online
                              </label>
                              <input
                                type="number"
                                min="0"
                                max={item.quantidade}
                                step="0.01"
                                value={quantidadesOnline[item.id] ?? item.quantidade_online ?? 0}
                                onChange={(e) => {
                                  const valor = parseFloat(e.target.value) || 0;
                                  setQuantidadesOnline({
                                    ...quantidadesOnline,
                                    [item.id]: Math.min(valor, item.quantidade)
                                  });
                                }}
                                className="w-full px-2 py-1.5 border-2 border-gray-400 rounded focus:ring-2 focus:ring-gray-500 focus:border-gray-500 text-sm font-medium"
                                placeholder="0"
                              />
                            </div>
                            
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">
                                🏪 Loja
                              </label>
                              <input
                                type="number"
                                value={(item.quantidade - (quantidadesOnline[item.id] ?? item.quantidade_online ?? 0)).toFixed(2)}
                                disabled
                                className="w-full px-2 py-1.5 border border-gray-300 rounded bg-gray-100 text-sm font-medium"
                              />
                            </div>
                          </div>
                          
                          <div className="mt-2 text-xs text-gray-600 bg-white rounded p-2 border border-gray-200">
                            Valor online: R$ {((quantidadesOnline[item.id] ?? item.quantidade_online ?? 0) * item.valor_unitario).toFixed(2)}
                          </div>
                          
                          {(quantidadesOnline[item.id] !== undefined && 
                            quantidadesOnline[item.id] !== item.quantidade_online) ? (
                            <button
                              onClick={() => salvarQuantidadeOnlineItem(
                                notaSelecionada.id, 
                                item.id, 
                                quantidadesOnline[item.id]
                              )}
                              className="w-full px-3 py-1.5 bg-gray-800 text-white rounded font-medium hover:bg-gray-900 mt-2 text-sm"
                            >
                              💾 Salvar
                            </button>
                          ) : (
                            item.quantidade_online !== null && item.quantidade_online !== undefined && (
                              <div className="mt-2 text-xs text-green-700 bg-green-50 rounded p-2 border border-green-200 flex items-center justify-center">
                                ✅ Salvo: {item.quantidade_online} online / {(item.quantidade - item.quantidade_online).toFixed(2)} loja
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}

                    {notaSelecionada.status === 'processada' && item.produto_id && (
                      <div className="mt-3 pt-3 border-t bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <span className="text-blue-800 font-semibold">✅ Lançado no estoque:</span>
                        <span className="ml-2">{item.produto_nome}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Rodapé com Ações */}
            {notaSelecionada.status === 'pendente' && (
              <div className="sticky bottom-0 bg-white border-t px-6 py-4 space-y-3">
                {/* Seção de Rateio - ANTES de processar */}
                <div className="bg-gray-50 border border-gray-200 rounded p-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-700">
                      📊 Distribuição (informativo para relatórios)
                    </h4>
                    <div className="text-xs text-gray-500">
                      Estoque unificado • Classificação apenas para análises
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'loja')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'loja'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      🏪 Loja
                    </button>
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'online')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'online'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      🌐 Online
                    </button>
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'parcial')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'parcial'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      📊 Parcial
                    </button>
                    
                    {(notaSelecionada.percentual_online > 0 || notaSelecionada.tipo_rateio) && (
                      <div className="ml-auto flex gap-3 text-xs text-gray-600">
                        <span>Online: {(notaSelecionada.percentual_online || 0).toFixed(0)}%</span>
                        <span>Loja: {(notaSelecionada.percentual_loja || 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>

                  {tipoRateio === 'parcial' && (
                    <div className="mt-2 text-xs text-gray-600 bg-gray-100 rounded p-2">
                      💡 Defina a quantidade destinada ao <strong>estoque online</strong> em cada produto acima. O sistema calcula automaticamente a % baseado nos valores.
                    </div>
                  )}
                </div>

                {/* Barra de Status e Botões de Ação */}
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    {notaSelecionada.itens.filter(i => i.produto_id).length} de {notaSelecionada.itens.length} produtos vinculados
                  </div>
                  <div className="flex gap-3">
                    {notaSelecionada.entrada_estoque_realizada ? (
                      <button
                        onClick={() => reverterNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                        disabled={loading}
                        className="px-6 py-2 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 disabled:bg-gray-400"
                      >
                        {loading ? '⏳ Revertendo...' : '↩️ Reverter Entrada'}
                      </button>
                    ) : (
                      <>
                        {!notaSelecionada.entrada_estoque_realizada && (
                          <button
                            onClick={() => excluirNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                            disabled={loading}
                            className="px-6 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400"
                          >
                            🗑️ Excluir Nota
                          </button>
                        )}
                        {notaSelecionada.itens.some(i => i.produto_id) && (
                          <>
                            <button
                              onClick={() => processarNota(notaSelecionada.id)}
                              disabled={loading}
                              className="px-6 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400"
                            >
                              💰 Revisar Preços
                            </button>
                            <button
                              onClick={() => processarNota(notaSelecionada.id)}
                              disabled={loading}
                              className="px-6 py-2 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400"
                            >
                              {loading ? '⏳ Processando...' : '✅ Processar Nota'}
                            </button>
                          </>
                        )}
                      </>
                    )}
                    <button
                      onClick={() => {
                        setMostrarDetalhes(false);
                        setNotaSelecionada(null);
                      }}
                      className="px-6 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
                    >
                      Fechar
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal de Criar Produto */}
      {mostrarModalCriarProduto && itemSelecionadoParaCriar && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">➕ Criar Novo Produto</h2>
                <p className="text-sm text-gray-600">A partir do item da NF-e</p>
              </div>
              <button
                onClick={() => {
                  setMostrarModalCriarProduto(false);
                  setItemSelecionadoParaCriar(null);
                  setSugestaoSku(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>

            <div className="px-6 py-4">
              {carregandoSugestao ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-600">Gerando sugestões de SKU...</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Informações do Item da NF-e */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="font-semibold text-blue-900 mb-2">📄 Dados da NF-e:</div>
                    <div className="text-sm space-y-1 text-blue-800">
                      <div><strong>Descrição:</strong> {itemSelecionadoParaCriar.descricao}</div>
                      <div><strong>Código Fornecedor:</strong> {itemSelecionadoParaCriar.codigo_produto}</div>
                      <div><strong>NCM:</strong> {itemSelecionadoParaCriar.ncm}</div>
                      {itemSelecionadoParaCriar.ean && (
                        <div><strong>EAN:</strong> {itemSelecionadoParaCriar.ean}</div>
                      )}
                      <div><strong>Valor Unitário:</strong> R$ {itemSelecionadoParaCriar.valor_unitario.toFixed(2)}</div>
                    </div>
                  </div>

                  {/* Alerta de SKU existente */}
                  {sugestaoSku?.ja_existe && (
                    <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <span className="text-2xl">⚠️</span>
                        <div className="flex-1">
                          <div className="font-semibold text-yellow-900 mb-2">
                            Código do fornecedor "{sugestaoSku.sku_proposto}" já está em uso!
                          </div>
                          <div className="text-sm text-yellow-800 mb-3">
                            Produto existente: <strong>{sugestaoSku.produto_existente.nome}</strong><br/>
                            <span className="text-xs">Um SKU alternativo foi sugerido automaticamente. Você pode alterar se preferir.</span>
                          </div>
                          <div className="text-sm text-yellow-800 mb-2 font-semibold">
                            Outras opções de SKU disponíveis:
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {sugestaoSku.sugestoes.map(sug => (
                              <button
                                key={sug.sku}
                                onClick={() => setFormProduto({ ...formProduto, sku: sug.sku })}
                                className={`px-3 py-1 rounded-lg text-sm font-semibold transition-all ${
                                  formProduto.sku === sug.sku
                                    ? 'bg-blue-600 text-white shadow-md'
                                    : 'bg-white border border-blue-300 text-blue-700 hover:bg-blue-50'
                                } ${sug.padrao ? 'ring-2 ring-yellow-400' : ''}`}
                              >
                                {sug.sku} {sug.padrao && '⭐'}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sucesso - SKU disponível */}
                  {sugestaoSku && !sugestaoSku.ja_existe && (
                    <div className="bg-green-50 border border-green-300 rounded-lg p-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">✅</span>
                        <div className="text-sm text-green-800">
                          <strong>SKU disponível!</strong> O código do fornecedor pode ser usado diretamente.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Formulário */}
                  <div className="space-y-4">
                    {/* SKU */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        SKU / Código do Produto *
                        <span className="text-xs text-gray-500 font-normal ml-2">(Baseado no código do fornecedor)</span>
                      </label>
                      <input
                        type="text"
                        value={formProduto.sku}
                        onChange={(e) => setFormProduto({ ...formProduto, sku: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono"
                        placeholder="Ex: MGZ-12345"
                      />
                      <p className="text-xs text-gray-500 mt-1">💡 Você pode editar o SKU se preferir</p>
                    </div>

                    {/* Nome */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        Nome do Produto *
                      </label>
                      <input
                        type="text"
                        value={formProduto.nome}
                        onChange={(e) => setFormProduto({ ...formProduto, nome: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Nome completo do produto"
                      />
                    </div>

                    {/* Descrição */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        Descrição
                      </label>
                      <textarea
                        value={formProduto.descricao}
                        onChange={(e) => setFormProduto({ ...formProduto, descricao: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        rows="2"
                        placeholder="Descrição detalhada (opcional)"
                      />
                    </div>

                    {/* Preços */}
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">
                          Preço de Custo *
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={formProduto.preco_custo}
                          onChange={(e) => {
                            const custo = e.target.value;
                            const margem = parseFloat(formProduto.margem_lucro) || 0;
                            setFormProduto({ 
                              ...formProduto, 
                              preco_custo: custo,
                              preco_venda: custo ? calcularPrecoVenda(parseFloat(custo), margem) : ''
                            });
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">
                          Margem (%) *
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={formProduto.margem_lucro}
                          onChange={(e) => {
                            const margem = e.target.value;
                            const custo = parseFloat(formProduto.preco_custo) || 0;
                            setFormProduto({ 
                              ...formProduto, 
                              margem_lucro: margem,
                              preco_venda: custo && margem ? calcularPrecoVenda(custo, parseFloat(margem)) : ''
                            });
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">
                          Preço de Venda *
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={formProduto.preco_venda}
                          onChange={(e) => {
                            const venda = e.target.value;
                            const custo = parseFloat(formProduto.preco_custo) || 0;
                            setFormProduto({ 
                              ...formProduto, 
                              preco_venda: venda,
                              margem_lucro: custo && venda ? calcularMargemLucro(custo, parseFloat(venda)) : ''
                            });
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>

                    {/* Estoque */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">
                          Estoque Mínimo
                        </label>
                        <input
                          type="number"
                          value={formProduto.estoque_minimo}
                          onChange={(e) => setFormProduto({ ...formProduto, estoque_minimo: parseInt(e.target.value) })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">
                          Estoque Máximo
                        </label>
                        <input
                          type="number"
                          value={formProduto.estoque_maximo}
                          onChange={(e) => setFormProduto({ ...formProduto, estoque_maximo: parseInt(e.target.value) })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Rodapé */}
            <div className="sticky bottom-0 bg-white border-t px-6 py-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  setMostrarModalCriarProduto(false);
                  setItemSelecionadoParaCriar(null);
                  setSugestaoSku(null);
                }}
                className="px-6 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={criarProdutoNovo}
                disabled={
                  loading || 
                  !formProduto.sku || 
                  !formProduto.nome || 
                  !formProduto.preco_custo || 
                  parseFloat(formProduto.preco_custo) <= 0 || 
                  !formProduto.preco_venda || 
                  parseFloat(formProduto.preco_venda) <= 0
                }
                className="px-6 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? '⏳ Criando...' : '✅ Criar e Vincular Produto'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Visualização da Nota */}
      {mostrarVisualizacao && notaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold">📄 NF-e {notaSelecionada.numero_nota}</h2>
                  <p className="text-blue-100 mt-1">Série: {notaSelecionada.serie}</p>
                </div>
                <button
                  onClick={() => {
                    setMostrarVisualizacao(false);
                    setNotaSelecionada(null);
                  }}
                  className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Informações da Nota */}
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                  <h3 className="font-semibold text-gray-700 mb-3">📋 Dados da Nota</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Data Emissão:</span>
                      <span className="font-semibold">{new Date(notaSelecionada.data_emissao).toLocaleDateString('pt-BR')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status:</span>
                      <span>{getStatusBadge(notaSelecionada.status)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Valor Total:</span>
                      <span className="font-bold text-green-600">R$ {notaSelecionada.valor_total.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-700 mb-3">🏢 Fornecedor</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-gray-600">Nome:</span>
                      <div className="font-semibold">{notaSelecionada.fornecedor_nome}</div>
                    </div>
                    <div>
                      <span className="text-gray-600">CNPJ:</span>
                      <div className="font-mono text-xs">{notaSelecionada.fornecedor_cnpj}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chave de Acesso */}
              <div className="mb-6 p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-600 mb-1">🔑 Chave de Acesso</div>
                <div className="font-mono text-xs break-all">{notaSelecionada.chave_acesso}</div>
              </div>

              {/* Status de Vinculação */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-blue-600">{notaSelecionada.itens?.length || 0}</div>
                  <div className="text-sm text-gray-600">Total Itens</div>
                </div>
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-600">{notaSelecionada.produtos_vinculados}</div>
                  <div className="text-sm text-gray-600">Vinculados</div>
                </div>
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-orange-600">{notaSelecionada.produtos_nao_vinculados}</div>
                  <div className="text-sm text-gray-600">Não Vinculados</div>
                </div>
              </div>

              {/* Itens da Nota */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">📦 Itens da Nota</h3>
                <div className="space-y-3">
                  {notaSelecionada.itens?.map((item, index) => (
                    <div key={item.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="font-semibold text-gray-800">{item.descricao}</div>
                          <div className="text-xs text-gray-500 mt-1">
                            Código: {item.codigo_produto} | NCM: {item.ncm}
                          </div>
                        </div>
                        {item.vinculado ? (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">
                            ✓ Vinculado
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-semibold rounded">
                            ⚠ Não Vinculado
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-4 gap-3 text-sm mt-3">
                        <div>
                          <span className="text-gray-600">Qtd:</span>
                          <div className="font-semibold">{item.quantidade}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Unit:</span>
                          <div className="font-semibold">R$ {item.valor_unitario.toFixed(2)}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Total:</span>
                          <div className="font-semibold text-green-600">R$ {item.valor_total.toFixed(2)}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">CFOP:</span>
                          <div className="font-semibold">{item.cfop}</div>
                        </div>
                      </div>

                      {/* Lote e Validade */}
                      {(item.lote || item.data_validade) && (
                        <div className="grid grid-cols-2 gap-3 mt-3 text-sm">
                          {item.lote && (
                            <div className="bg-purple-50 border border-purple-200 rounded p-2">
                              <span className="text-gray-600">📦 Lote:</span>
                              <div className="font-semibold text-purple-800">{item.lote}</div>
                            </div>
                          )}
                          {item.data_validade && (
                            <div className="bg-orange-50 border border-orange-200 rounded p-2">
                              <span className="text-gray-600">📅 Validade:</span>
                              <div className="font-semibold text-orange-800">
                                {new Date(item.data_validade).toLocaleDateString('pt-BR')}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {item.vinculado && item.produto_nome && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <span className="text-xs text-gray-600">→ Produto vinculado: </span>
                          <span className="text-sm font-semibold text-blue-600">{item.produto_nome}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t p-6 bg-gray-50 flex justify-between items-center">
              <div className="text-sm text-gray-600">
                {notaSelecionada.entrada_estoque_realizada ? (
                  <span className="text-green-600 font-semibold">✅ Entrada realizada no estoque</span>
                ) : (
                  <span className="text-orange-600 font-semibold">⚠️ Entrada ainda não processada</span>
                )}
              </div>
              <div className="flex gap-3">
                {notaSelecionada.status === 'pendente' && notaSelecionada.produtos_vinculados > 0 && !notaSelecionada.entrada_estoque_realizada && (
                  <>
                    <button
                      onClick={() => {
                        setMostrarVisualizacao(false);
                        processarNota(notaSelecionada.id);
                      }}
                      className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold"
                    >
                      💰 Revisar Preços e Processar
                    </button>
                  </>
                )}
                {notaSelecionada.status === 'pendente' && (
                  <button
                    onClick={() => {
                      setMostrarVisualizacao(false);
                      abrirDetalhes(notaSelecionada.id);
                    }}
                    className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold"
                  >
                    🔗 Vincular Produtos
                  </button>
                )}
                <button
                  onClick={() => {
                    setMostrarVisualizacao(false);
                    setNotaSelecionada(null);
                  }}
                  className="px-6 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Revisão de Preços */}
      {mostrarRevisaoPrecos && previewProcessamento && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6">
              <h2 className="text-2xl font-bold">💰 Revisão de Preços e Custos</h2>
              <p className="text-purple-100 mt-1">
                NF-e {previewProcessamento.numero_nota} - {previewProcessamento.fornecedor_nome}
              </p>
            </div>

            {/* Resumo de Alterações */}
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-semibold text-gray-700">Filtrar:</span>
                {(() => {
                  const itensVinculados = previewProcessamento.itens.filter(i => i.produto_vinculado);
                  const aumentos = itensVinculados.filter(i => i.produto_vinculado.variacao_custo_percentual > 0).length;
                  const reducoes = itensVinculados.filter(i => i.produto_vinculado.variacao_custo_percentual < 0).length;
                  const iguais = itensVinculados.filter(i => i.produto_vinculado.variacao_custo_percentual === 0).length;
                  const total = previewProcessamento.itens.length;
                  
                  return (
                    <>
                      <button
                        onClick={() => setFiltroCusto('todos')}
                        className={`px-3 py-1 rounded-full text-sm font-semibold flex items-center gap-1 transition-all ${
                          filtroCusto === 'todos' 
                            ? 'bg-blue-600 text-white shadow-md' 
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        <span className="text-base">📋</span>
                        Todos ({total})
                      </button>
                      
                      {aumentos > 0 && (
                        <button
                          onClick={() => setFiltroCusto('aumentou')}
                          className={`px-3 py-1 rounded-full text-sm font-semibold flex items-center gap-1 transition-all ${
                            filtroCusto === 'aumentou' 
                              ? 'bg-red-600 text-white shadow-md' 
                              : 'bg-red-100 text-red-700 hover:bg-red-200'
                          }`}
                        >
                          <span className="text-base">📈</span>
                          {aumentos} custo{aumentos > 1 ? 's' : ''} maior{aumentos > 1 ? 'es' : ''}
                        </button>
                      )}
                      
                      {reducoes > 0 && (
                        <button
                          onClick={() => setFiltroCusto('diminuiu')}
                          className={`px-3 py-1 rounded-full text-sm font-semibold flex items-center gap-1 transition-all ${
                            filtroCusto === 'diminuiu' 
                              ? 'bg-green-600 text-white shadow-md' 
                              : 'bg-green-100 text-green-700 hover:bg-green-200'
                          }`}
                        >
                          <span className="text-base">📉</span>
                          {reducoes} custo{reducoes > 1 ? 's' : ''} menor{reducoes > 1 ? 'es' : ''}
                        </button>
                      )}
                      
                      {iguais > 0 && (
                        <button
                          onClick={() => setFiltroCusto('igual')}
                          className={`px-3 py-1 rounded-full text-sm font-semibold flex items-center gap-1 transition-all ${
                            filtroCusto === 'igual' 
                              ? 'bg-gray-600 text-white shadow-md' 
                              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                          }`}
                        >
                          <span className="text-base">➡️</span>
                          {iguais} sem alteração
                        </button>
                      )}
                    </>
                  );
                })()}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-6">
                {previewProcessamento.itens
                  .filter(item => {
                    // Filtrar baseado no status de vinculação E variação de custo
                    const vinculado = item.produto_vinculado !== null;
                    const custoVariacao = item.produto_vinculado?.variacao_custo_percentual || 0;
                    
                    if (filtroCusto === 'todos') return true;
                    if (filtroCusto === 'aumentou') return vinculado && custoVariacao > 0;
                    if (filtroCusto === 'diminuiu') return vinculado && custoVariacao < 0;
                    if (filtroCusto === 'igual') return vinculado && custoVariacao === 0;
                    return true;
                  })
                  .map((item) => {
                  const vinculado = item.produto_vinculado !== null;
                  const produtoVinc = item.produto_vinculado;
                  
                  // Se vinculado, usar dados do produto vinculado para variação
                  const custoVariacao = produtoVinc?.variacao_custo_percentual || 0;
                  const custoAumentou = custoVariacao > 0;
                  
                  const precosAtuais = vinculado ? (precosAjustados[produtoVinc.produto_id] || {
                    preco_venda: produtoVinc.preco_venda_atual,
                    margem: produtoVinc.margem_atual
                  }) : null;

                  return (
                    <div key={item.item_id} className="border-2 border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow">
                      
                      {/* Alertas de Divergência */}
                      {vinculado && (() => {
                        const divs = detectarDivergencias(item);
                        if (divs.length === 0) return null;
                        
                        return (
                          <div className="bg-yellow-50 border-b-2 border-yellow-300 p-3">
                            <div className="flex items-start gap-2">
                              <span className="text-xl">⚠️</span>
                              <div className="flex-1">
                                <div className="font-bold text-yellow-800 mb-1">Possíveis Divergências Detectadas:</div>
                                <ul className="space-y-1">
                                  {divs.map((div, idx) => (
                                    <li key={idx} className={`text-sm ${
                                      div.gravidade === 'critica' ? 'text-red-700 font-bold' :
                                      div.gravidade === 'alta' ? 'text-orange-700 font-semibold' :
                                      'text-yellow-700'
                                    }`}>
                                      • {div.mensagem}
                                    </li>
                                  ))}
                                </ul>
                                <p className="text-xs text-yellow-700 mt-2">
                                  ⚠️ Verifique se o produto vinculado está correto!
                                </p>
                              </div>
                            </div>
                          </div>
                        );
                      })()}
                      
                      {/* Layout de Duas Colunas */}
                      <div className="grid grid-cols-[1fr_auto_1fr] gap-0">
                        
                        {/* COLUNA ESQUERDA: Dados da NF */}
                        <div className="p-4 bg-blue-50 border-r border-gray-300">
                          <div className="flex items-start gap-2 mb-2">
                            <span className="text-2xl">📄</span>
                            <div className="flex-1">
                              <div className="text-xs font-semibold text-blue-700 mb-1">NOTA FISCAL</div>
                              <h3 className="font-bold text-base text-gray-800">{item.descricao_nf}</h3>
                              <div className="mt-2 space-y-1">
                                <p className="text-xs text-gray-600">
                                  <span className="font-semibold">SKU Fornecedor:</span> {item.codigo_produto_nf || 'N/A'}
                                </p>
                                {item.ean_nf && (
                                  <p className="text-xs text-gray-600">
                                    <span className="font-semibold">EAN:</span> {item.ean_nf}
                                  </p>
                                )}
                                <p className="text-xs text-gray-600">
                                  <span className="font-semibold">Quantidade:</span> {item.quantidade_nf}
                                </p>
                                <p className="text-xs text-gray-600">
                                  <span className="font-semibold">Valor Unit.:</span> R$ {item.valor_unitario_nf.toFixed(2)}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* COLUNA CENTRAL: Ícone de Conexão */}
                        <div className="flex items-center justify-center bg-gray-100 px-4">
                          {vinculado ? (
                            <button
                              onClick={() => desvincularProduto(item.item_id)}
                              className="group relative"
                              title="Clique para desvincular"
                            >
                              <div className="w-12 h-12 rounded-full bg-green-500 hover:bg-red-500 transition-colors flex items-center justify-center shadow-lg">
                                <span className="text-2xl group-hover:hidden">✓</span>
                                <span className="text-2xl hidden group-hover:inline">✕</span>
                              </div>
                              <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap text-xs text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity">
                                Desvincular
                              </div>
                            </button>
                          ) : (
                            <div className="w-12 h-12 rounded-full bg-gray-300 flex items-center justify-center">
                              <span className="text-2xl text-gray-500">✕</span>
                            </div>
                          )}
                        </div>

                        {/* COLUNA DIREITA: Produto Vinculado */}
                        <div className={`p-4 ${vinculado ? 'bg-green-50' : 'bg-gray-50'}`}>
                          {vinculado ? (
                            <div className="flex items-start gap-2">
                              <span className="text-2xl">📦</span>
                              <div className="flex-1">
                                <div className="text-xs font-semibold text-green-700 mb-1">PRODUTO VINCULADO</div>
                                <h3 className="font-bold text-base text-gray-800">{produtoVinc.produto_nome}</h3>
                                <div className="mt-2 space-y-1">
                                  <p className="text-xs text-gray-600">
                                    <span className="font-semibold">SKU Sistema:</span> {produtoVinc.produto_codigo}
                                  </p>
                                  {produtoVinc.produto_ean && (
                                    <p className="text-xs text-gray-600">
                                      <span className="font-semibold">EAN:</span> {produtoVinc.produto_ean}
                                    </p>
                                  )}
                                  <p className="text-xs text-gray-600">
                                    <span className="font-semibold">Estoque:</span> {produtoVinc.estoque_atual}
                                  </p>
                                  <p className="text-xs text-gray-600">
                                    <span className="font-semibold">Custo Atual:</span> R$ {produtoVinc.custo_anterior.toFixed(2)}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="flex flex-col items-center justify-center h-full text-center">
                              <span className="text-4xl mb-2">❓</span>
                              <p className="text-sm font-semibold text-gray-600 mb-3">Produto não vinculado</p>
                              <button
                                onClick={() => abrirModalVincularProduto(item)}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition-colors"
                              >
                                🔗 Vincular Produto
                              </button>
                              <button
                                onClick={() => abrirModalCriarProduto(item)}
                                className="mt-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-semibold transition-colors"
                              >
                                ✨ Criar Novo
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Seção de Custos e Preços (só aparece se vinculado) */}
                      {vinculado && (
                        <div className="p-4 bg-white border-t-2 border-gray-200">
                          {/* Comparação de Custos */}
                          <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-gray-50 rounded">
                            <div>
                              <div className="text-xs text-gray-600 mb-1">💵 Custo Anterior</div>
                              <div className="text-lg font-semibold text-gray-700">
                                R$ {produtoVinc.custo_anterior.toFixed(2)}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-600 mb-1">🆕 Custo Novo</div>
                              <div className="text-lg font-semibold text-blue-600">
                                R$ {produtoVinc.custo_novo.toFixed(2)}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-600 mb-1">📊 Variação</div>
                              <div className={`text-lg font-bold ${custoAumentou ? 'text-red-600' : custoVariacao < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                                {custoVariacao > 0 ? '↗' : custoVariacao < 0 ? '↘' : '➡'} {Math.abs(custoVariacao).toFixed(1)}%
                              </div>
                            </div>
                          </div>

                          {/* Ajuste de Preços */}
                          <div className="grid grid-cols-2 gap-4 p-4 bg-purple-50 border border-purple-200 rounded">
                            {/* Preço de Venda */}
                            <div>
                              <label className="block text-sm font-semibold text-gray-700 mb-2">
                                💰 Preço de Venda
                              </label>
                              <div className="flex items-center gap-2">
                                <span className="text-lg">R$</span>
                                <input
                                  type="number"
                                  step="0.01"
                                  value={precosAtuais.preco_venda}
                                  onChange={(e) => atualizarPrecoVenda(
                                    produtoVinc.produto_id,
                                    parseFloat(e.target.value) || 0,
                                    produtoVinc.custo_novo
                                  )}
                                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-lg font-semibold focus:ring-2 focus:ring-purple-500"
                                />
                              </div>
                              <div className="mt-1 text-xs text-gray-500">
                                Anterior: R$ {produtoVinc.preco_venda_atual.toFixed(2)}
                              </div>
                            </div>

                            {/* Margem */}
                            <div>
                              <label className="block text-sm font-semibold text-gray-700 mb-2">
                                📈 Margem de Lucro
                              </label>
                              <div className="flex items-center gap-2">
                                <input
                                  type="number"
                                  step="0.1"
                                  value={precosAtuais.margem}
                                  onChange={(e) => atualizarMargem(
                                    produtoVinc.produto_id,
                                    parseFloat(e.target.value) || 0,
                                    produtoVinc.custo_novo
                                  )}
                                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-lg font-semibold focus:ring-2 focus:ring-purple-500"
                            />
                            <span className="text-lg">%</span>
                          </div>
                          <div className="mt-1 text-xs text-gray-500">
                            (Com o novo custo)
                          </div>
                        </div>
                      </div>

                      {/* Análise: Valores ANTERIORES com cores */}
                      <div className="p-4 bg-gradient-to-br from-gray-50 to-gray-100 border-2 border-gray-300 rounded-lg">
                        <div className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
                          📊 Análise Comparativa (Valores Anteriores)
                          <span className="text-xs font-normal text-gray-500">
                            - Comparação do cenário antigo vs novo
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-3 gap-3">
                          {/* Custo Anterior */}
                          {(() => {
                            const custoAnterior = parseFloat(item.custo_anterior) || 0;
                            const custoNovo = parseFloat(item.custo_novo) || 0;
                            const corInfo = getCorComparacao(custoNovo, custoAnterior, 'custo');
                            return (
                              <div className={`${corInfo.bg} border-2 ${corInfo.border} rounded-lg p-3`}>
                                <div className="text-xs text-gray-600 mb-1">💵 Custo Anterior</div>
                                <div className={`text-base font-bold ${corInfo.cor} flex items-center gap-1`}>
                                  <span>{corInfo.label}</span>
                                  <span>R$ {custoAnterior.toFixed(2)}</span>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Preço de Venda Anterior */}
                          {(() => {
                            const precoAtual = parseFloat(item.preco_venda_atual) || 0;
                            const precoNovo = parseFloat(precosAtuais.preco_venda) || 0;
                            const corInfo = getCorComparacao(precoNovo, precoAtual, 'preco');
                            return (
                              <div className={`${corInfo.bg} border-2 ${corInfo.border} rounded-lg p-3`}>
                                <div className="text-xs text-gray-600 mb-1">💰 Preço Anterior</div>
                                <div className={`text-base font-bold ${corInfo.cor} flex items-center gap-1`}>
                                  <span>{corInfo.label}</span>
                                  <span>R$ {precoAtual.toFixed(2)}</span>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Margem Anterior */}
                          {(() => {
                            const custoAnterior = parseFloat(item.custo_anterior) || 0;
                            const precoVendaAnterior = parseFloat(item.preco_venda_atual) || 0;
                            // Fórmula: (preço - custo) / preço * 100 (margem sobre venda)
                            const margemAnterior = precoVendaAnterior > 0 
                              ? ((precoVendaAnterior - custoAnterior) / precoVendaAnterior * 100)
                              : 0;
                            const margemNova = parseFloat(precosAtuais.margem) || 0;
                            const corInfo = getCorComparacao(margemNova, margemAnterior, 'margem');
                            return (
                              <div className={`${corInfo.bg} border-2 ${corInfo.border} rounded-lg p-3`}>
                                <div className="text-xs text-gray-600 mb-1">📈 Margem Anterior</div>
                                <div className={`text-base font-bold ${corInfo.cor} flex items-center gap-1`}>
                                  <span>{corInfo.label}</span>
                                  <span>{margemAnterior.toFixed(2)}%</span>
                                </div>
                              </div>
                            );
                          })()}
                        </div>

                        {/* Legenda de cores */}
                        <div className="mt-3 pt-3 border-t border-gray-300 flex items-center gap-4 text-xs">
                          <div className="flex items-center gap-1">
                            <span className="text-green-600 font-bold">↑</span>
                            <span className="text-gray-600">Vantagem</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-blue-600 font-bold">=</span>
                            <span className="text-gray-600">Igual</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-red-600 font-bold">↓</span>
                            <span className="text-gray-600">Desvantagem</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Footer */}
            <div className="border-t p-6 bg-gray-50 flex justify-between items-center">
              <button
                onClick={() => {
                  setMostrarRevisaoPrecos(false);
                  setPreviewProcessamento(null);
                }}
                className="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-semibold transition-colors"
              >
                ❌ Cancelar
              </button>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-sm text-gray-600">Valor Total da Nota</div>
                  <div className="text-2xl font-bold text-green-600">
                    R$ {previewProcessamento.valor_total.toFixed(2)}
                  </div>
                </div>
                <button
                  onClick={confirmarProcessamento}
                  disabled={loading}
                  className="px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-lg font-bold text-lg shadow-lg disabled:opacity-50 transition-all"
                >
                  {loading ? '⏳ Processando...' : '✅ Confirmar e Processar Nota'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Histórico de Preços */}
      {mostrarHistoricoPrecos && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6">
              <h2 className="text-2xl font-bold">📊 Histórico de Alterações de Preços</h2>
              {produtoHistorico && (
                <p className="mt-2 text-purple-100">
                  {produtoHistorico.nome}
                </p>
              )}
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto flex-1">
              {carregandoHistorico ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-600"></div>
                </div>
              ) : historicoPrecos.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500 text-lg">Nenhuma alteração de preço registrada</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {historicoPrecos.map((hist) => (
                    <div key={hist.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                      {/* Header do Item */}
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-2xl">
                              {hist.motivo === 'nfe_entrada' ? '📦' : 
                               hist.motivo === 'nfe_revisao_precos' ? '💰' : 
                               hist.motivo === 'manual' ? '✏️' : '📝'}
                            </span>
                            <span className="font-semibold text-gray-800">
                              {hist.motivo === 'nfe_entrada' ? 'Entrada NF-e' :
                               hist.motivo === 'nfe_revisao_precos' ? 'Revisão de Preços' :
                               hist.motivo === 'manual' ? 'Ajuste Manual' :
                               hist.motivo}
                            </span>
                          </div>
                          {hist.referencia && (
                            <p className="text-sm text-gray-600 mt-1">{hist.referencia}</p>
                          )}
                          {hist.nota_numero && (
                            <p className="text-sm text-blue-600 mt-1">Nota: {hist.nota_numero}</p>
                          )}
                        </div>
                        <div className="text-right text-sm text-gray-500">
                          {new Date(hist.data).toLocaleString('pt-BR')}
                          {hist.usuario && (
                            <div className="text-xs mt-1">{hist.usuario}</div>
                          )}
                        </div>
                      </div>

                      {/* Alterações de Preço */}
                      <div className="grid grid-cols-2 gap-4">
                        {/* Custo */}
                        {hist.preco_custo_anterior !== null && hist.preco_custo_novo !== null && (
                          <div className="bg-blue-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 font-semibold mb-2">💵 CUSTO</div>
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-sm text-gray-500">Anterior</div>
                                <div className="text-lg font-bold">R$ {hist.preco_custo_anterior.toFixed(2)}</div>
                              </div>
                              <div className="text-2xl">→</div>
                              <div>
                                <div className="text-sm text-gray-500">Novo</div>
                                <div className="text-lg font-bold text-blue-700">R$ {hist.preco_custo_novo.toFixed(2)}</div>
                              </div>
                            </div>
                            {hist.variacao_custo_percentual !== null && hist.variacao_custo_percentual !== 0 && (
                              <div className={`mt-2 text-sm font-semibold text-center ${
                                hist.variacao_custo_percentual > 0 ? 'text-red-600' : 'text-green-600'
                              }`}>
                                {hist.variacao_custo_percentual > 0 ? '↑' : '↓'} {Math.abs(hist.variacao_custo_percentual).toFixed(2)}%
                              </div>
                            )}
                          </div>
                        )}

                        {/* Preço de Venda */}
                        {hist.preco_venda_anterior !== null && hist.preco_venda_novo !== null && (
                          <div className="bg-green-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 font-semibold mb-2">💲 PREÇO DE VENDA</div>
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-sm text-gray-500">Anterior</div>
                                <div className="text-lg font-bold">R$ {hist.preco_venda_anterior.toFixed(2)}</div>
                              </div>
                              <div className="text-2xl">→</div>
                              <div>
                                <div className="text-sm text-gray-500">Novo</div>
                                <div className="text-lg font-bold text-green-700">R$ {hist.preco_venda_novo.toFixed(2)}</div>
                              </div>
                            </div>
                            {hist.variacao_venda_percentual !== null && hist.variacao_venda_percentual !== 0 && (
                              <div className={`mt-2 text-sm font-semibold text-center ${
                                hist.variacao_venda_percentual > 0 ? 'text-green-600' : 'text-red-600'
                              }`}>
                                {hist.variacao_venda_percentual > 0 ? '↑' : '↓'} {Math.abs(hist.variacao_venda_percentual).toFixed(2)}%
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Margens */}
                      {hist.margem_anterior !== null && hist.margem_nova !== null && (
                        <div className="mt-3 bg-purple-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 font-semibold mb-2">📈 MARGEM DE LUCRO</div>
                          <div className="flex items-center justify-around">
                            <div className="text-center">
                              <div className="text-sm text-gray-500">Anterior</div>
                              <div className="text-xl font-bold">{hist.margem_anterior.toFixed(1)}%</div>
                            </div>
                            <div className="text-2xl">→</div>
                            <div className="text-center">
                              <div className="text-sm text-gray-500">Nova</div>
                              <div className="text-xl font-bold text-purple-700">{hist.margem_nova.toFixed(1)}%</div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Observações */}
                      {hist.observacoes && (
                        <div className="mt-3 text-sm text-gray-600 italic bg-gray-50 rounded p-2">
                          {hist.observacoes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t p-6 bg-gray-50">
              <button
                onClick={() => {
                  setMostrarHistoricoPrecos(false);
                  setHistoricoPrecos([]);
                  setProdutoHistorico(null);
                }}
                className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Resultado do Lote */}
      {mostrarModalLote && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white p-6">
              <h2 className="text-2xl font-bold">
                📦 Resultado do Processamento em Lote
              </h2>
              {resultadoLote && (
                <p className="mt-2">
                  {resultadoLote.sucessos} sucesso(s) | {resultadoLote.erros} erro(s) | Total: {resultadoLote.total_arquivos}
                </p>
              )}
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto flex-1">
              {uploadingLote && !resultadoLote && (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-green-600 mb-4"></div>
                  <p className="text-lg text-gray-600">Processando arquivos...</p>
                </div>
              )}

              {resultadoLote && (
                <>
                  {/* Resumo */}
                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="bg-gray-100 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-blue-600">{resultadoLote.total_arquivos}</div>
                      <div className="text-sm text-gray-600">Total</div>
                    </div>
                    <div className="bg-green-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-green-600">{resultadoLote.sucessos}</div>
                      <div className="text-sm text-gray-600">Sucessos</div>
                    </div>
                    <div className="bg-red-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-red-600">{resultadoLote.erros}</div>
                      <div className="text-sm text-gray-600">Erros</div>
                    </div>
                  </div>

                  {/* Lista de Resultados */}
                  <div className="space-y-3">
                    {resultadoLote.resultados.map((resultado, idx) => (
                      <div
                        key={idx}
                        className={`border rounded-lg p-4 ${
                          resultado.sucesso
                            ? 'bg-green-50 border-green-200'
                            : 'bg-red-50 border-red-200'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-2xl">
                                {resultado.sucesso ? '✅' : '❌'}
                              </span>
                              <span className="font-semibold text-gray-800">
                                {resultado.arquivo}
                              </span>
                            </div>
                            
                            {resultado.sucesso ? (
                              <div className="text-sm space-y-1">
                                <p className="text-gray-700">
                                  <strong>Nota:</strong> {resultado.numero_nota}
                                </p>
                                <p className="text-gray-700">
                                  <strong>Fornecedor:</strong> {resultado.fornecedor}
                                </p>
                                <p className="text-gray-700">
                                  <strong>Valor:</strong> R$ {resultado.valor_total?.toFixed(2)}
                                </p>
                                <p className="text-gray-700">
                                  <strong>Produtos:</strong> {resultado.produtos_vinculados} vinculados, {resultado.produtos_nao_vinculados} não vinculados
                                </p>
                              </div>
                            ) : (
                              <p className="text-sm text-red-700">{resultado.mensagem}</p>
                            )}
                          </div>
                          <span className="text-sm text-gray-500 ml-4">#{resultado.ordem}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="border-t p-6 bg-gray-50">
              <button
                onClick={() => {
                  setMostrarModalLote(false);
                  setResultadoLote(null);
                }}
                disabled={uploadingLote}
                className="w-full px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold disabled:opacity-50 transition-colors"
              >
                {uploadingLote ? '⏳ Processando...' : 'Fechar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EntradaXML;
