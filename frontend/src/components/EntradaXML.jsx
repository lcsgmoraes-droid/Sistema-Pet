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
  
  // Estados para histÃ³rico de preÃ§os
  const [mostrarHistoricoPrecos, setMostrarHistoricoPrecos] = useState(false);
  const [historicoPrecos, setHistoricoPrecos] = useState([]);
  const [produtoHistorico, setProdutoHistorico] = useState(null);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  
  // Estados para revisÃ£o de preÃ§os
  const [mostrarRevisaoPrecos, setMostrarRevisaoPrecos] = useState(false);
  const [previewProcessamento, setPreviewProcessamento] = useState(null);
  const [precosAjustados, setPrecosAjustados] = useState({});
  const [filtroCusto, setFiltroCusto] = useState('todos'); // 'todos', 'aumentou', 'diminuiu', 'igual'
  
  // Estados para rateio (APENAS informativo - estoque Ã© UNIFICADO)
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
    console.log('ðŸ”„ [EntradaXML] Componente montado, iniciando carregamento...');
    carregarDados();
  }, []);

  const carregarDados = async () => {
    console.log('ðŸ“Š [EntradaXML] Carregando dados...');
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      console.log('ðŸ”‘ [EntradaXML] Token obtido:', token ? 'SIM' : 'NÃƒO');
      const headers = { Authorization: `Bearer ${token}` };

      console.log('ðŸŒ [EntradaXML] Fazendo requisiÃ§Ãµes para:', {
        notasEntrada: `/notas-entrada/`,
        produtos: `/produtos/` // Sem filtro de ativo para trazer todos os produtos
      });

      const [notasRes, produtosRes] = await Promise.all([
        api.get(`/notas-entrada/`, { headers }),
        api.get(`/produtos/`, { headers, params: { ativo: null } }) // null = todos os produtos
      ]);

      console.log('âœ… [EntradaXML] Dados carregados:', {
        notasEntrada: notasRes.data?.length || 0,
        produtos: produtosRes.data?.items?.length || produtosRes.data?.length || 0
      });

      const listaProdutos = produtosRes.data?.items || produtosRes.data;
      
      // Log para debug: contar produtos ativos vs inativos
      const produtosAtivos = listaProdutos.filter(p => p.ativo === true).length;
      const produtosInativos = listaProdutos.filter(p => p.ativo === false).length;
      
      console.log('ðŸ“Š [EntradaXML] Produtos por status:', {
        ativos: produtosAtivos,
        inativos: produtosInativos,
        total: listaProdutos.length
      });

      setNotasEntrada(notasRes.data);
      setProdutos(listaProdutos);
    } catch (error) {
      console.error('âŒ [EntradaXML] ERRO ao carregar dados:');
      console.error('  - Mensagem:', error.message);
      console.error('  - Response:', error.response?.data);
      console.error('  - Status:', error.response?.status);
      console.error('  - Stack:', error.stack);
      toast.error(`Erro ao carregar dados: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    console.log('ðŸ“¤ [EntradaXML] Upload iniciado');
    console.log('  - Arquivo selecionado:', file?.name);
    console.log('  - Tamanho:', file?.size, 'bytes');
    console.log('  - Tipo:', file?.type);
    
    if (!file) {
      console.warn('âš ï¸ [EntradaXML] Nenhum arquivo selecionado');
      return;
    }

    if (!file.name.toLowerCase().endsWith('.xml')) {
      console.error('âŒ [EntradaXML] Arquivo nÃ£o Ã© XML:', file.name);
      toast.error('âŒ Por favor, selecione um arquivo XML');
      return;
    }

    setUploadingFile(true);
    const formData = new FormData();
    formData.append('file', file);

    console.log('ðŸš€ [EntradaXML] Enviando arquivo para:', `/notas-entrada/upload`);
    console.log('ðŸ“¦ [EntradaXML] FormData preparado:', file.name, file.size, 'bytes');

    try {
      const response = await api.post(`/notas-entrada/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('âœ… [EntradaXML] Upload bem-sucedido!');
      console.log('  - Response data:', response.data);

      const itensVinculados = response.data.produtos_vinculados || 0;
      const totalItens = response.data.itens_total || 0;

      console.log(`ðŸ“Š [EntradaXML] Produtos vinculados: ${itensVinculados}/${totalItens}`);

      // Mensagem de fornecedor criado
      if (response.data.fornecedor_criado_automaticamente) {
        toast.success(
          `ðŸ¢ Novo fornecedor cadastrado: ${response.data.fornecedor}`,
          { duration: 4000 }
        );
      }

      // Mensagem de produtos reativados
      if (response.data.produtos_reativados > 0) {
        toast.success(
          `â™»ï¸ ${response.data.produtos_reativados} produto(s) inativo(s) reativado(s) automaticamente`,
          { duration: 4000 }
        );
      }

      toast.success(
        `âœ… NF-e ${response.data.numero_nota} processada! ${itensVinculados}/${totalItens} produtos vinculados automaticamente`,
        { duration: 5000 }
      );
      
      carregarDados();
      event.target.value = ''; // Limpar input
    } catch (error) {
      console.error('âŒ [EntradaXML] ERRO no upload:');
      console.error('  - Mensagem:', error.message);
      console.error('  - Response data:', error.response?.data);
      console.error('  - Status:', error.response?.status);
      console.error('  - Headers:', error.response?.headers);
      console.error('  - Stack completo:', error.stack);
      
      const errorMsg = error.response?.data?.detail || error.message || 'Erro ao processar XML da NF-e';
      console.error('  - Mensagem para usuÃ¡rio:', errorMsg);
      
      toast.error(`âŒ ${errorMsg}`);
    } finally {
      setUploadingFile(false);
      console.log('ðŸ [EntradaXML] Upload finalizado');
    }
  };

  const handleMultipleFilesUpload = async (event) => {
    const files = Array.from(event.target.files);
    console.log('ðŸ“¦ [EntradaXML] Upload em lote iniciado -', files.length, 'arquivos');
    
    if (files.length === 0) {
      console.warn('âš ï¸ [EntradaXML] Nenhum arquivo selecionado');
      return;
    }

    // Validar se todos sÃ£o XML
    const invalidFiles = files.filter(f => !f.name.toLowerCase().endsWith('.xml'));
    if (invalidFiles.length > 0) {
      toast.error(`âŒ ${invalidFiles.length} arquivo(s) nÃ£o sÃ£o XML: ${invalidFiles.map(f => f.name).join(', ')}`);
      return;
    }

    setUploadingLote(true);
    setMostrarModalLote(true);
    setResultadoLote(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    console.log('ðŸš€ [EntradaXML] Enviando', files.length, 'arquivos para:', `/notas-entrada/upload-lote`);

    try {
            const response = await api.post(`/notas-entrada/upload-lote`, formData);

      console.log('âœ… [EntradaXML] Upload em lote bem-sucedido!');
      console.log('  - Response:', response.data);

      setResultadoLote(response.data);
      
      if (response.data.sucessos > 0) {
        toast.success(
          `âœ… ${response.data.sucessos}/${response.data.total_arquivos} nota(s) processada(s) com sucesso!`,
          { duration: 5000 }
        );
      }
      
      if (response.data.erros > 0) {
        toast.error(
          `âš ï¸ ${response.data.erros}/${response.data.total_arquivos} nota(s) com erro`,
          { duration: 5000 }
        );
      }
      
      carregarDados();
      event.target.value = ''; // Limpar input
    } catch (error) {
      console.error('âŒ [EntradaXML] ERRO no upload em lote:', error);
      toast.error(`âŒ Erro ao processar lote: ${error.response?.data?.detail || error.message}`);
      setMostrarModalLote(false);
    } finally {
      setUploadingLote(false);
    }
  };

  const abrirDetalhes = async (notaId) => {
    try {
            const response = await api.get(`/notas-entrada/${notaId}`);
      // Ordenar itens por ID para manter ordem consistente
      if (response.data.itens) {
        response.data.itens.sort((a, b) => a.id - b.id);
      }
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
      
      toast.success('âœ… Produto vinculado com sucesso!');
      
      // Recarregar detalhes
      const response = await api.get(`/notas-entrada/${notaId}`);
      // Ordenar itens por ID para manter ordem consistente
      if (response.data.itens) {
        response.data.itens.sort((a, b) => a.id - b.id);
      }
      setNotaSelecionada(response.data);
    } catch (error) {
      console.error('âŒ Erro ao vincular produto:', error);
      toast.error(error.response?.data?.detail || 'Erro ao vincular produto');
    }
  };

  const salvarRateioItem = async (notaId, itemId, percentualOnline, percentualLoja) => {
    try {
      await api.post(`/notas-entrada/${notaId}/itens/${itemId}/rateio`, {
        percentual_online: parseFloat(percentualOnline),
        percentual_loja: parseFloat(percentualLoja)
      });
      
      toast.success('ðŸ“Š Rateio configurado com sucesso!');
      
      // Recarregar detalhes
      const response = await api.get(`/notas-entrada/${notaId}`);
      setNotaSelecionada(response.data);
    } catch (error) {
      console.error('âŒ Erro ao salvar rateio:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar rateio');
    }
  };

  const salvarTipoRateio = async (notaId, tipo) => {
    try {
      await api.post(`/notas-entrada/${notaId}/rateio`, {
        tipo_rateio: tipo
      });
      
      toast.success(`âœ… Nota configurada: ${tipo === 'online' ? '100% Online' : tipo === 'loja' ? '100% Loja FÃ­sica' : 'Rateio Parcial'}`);
      
      // Recarregar detalhes
      const response = await api.get(`/notas-entrada/${notaId}`);
      setNotaSelecionada(response.data);
      
      // Atualizar estado local para seleÃ§Ã£o visual
      setTipoRateio(tipo);
    } catch (error) {
      console.error('âŒ Erro ao salvar tipo de rateio:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar tipo de rateio');
    }
  };

  const salvarQuantidadeOnlineItem = async (notaId, itemId, quantidadeOnline) => {
    try {
      const response = await api.post(`/notas-entrada/${notaId}/itens/${itemId}/rateio`, {
        quantidade_online: parseFloat(quantidadeOnline) || 0  // Permitir 0
      });
      
      toast.success('ðŸ“Š Quantidade online configurada!');
      
      // Mostrar totais da nota
      const totais = response.data.nota_totais;
      toast.success(
        `Nota: ${totais.percentual_online.toFixed(1)}% Online (R$ ${totais.valor_online.toFixed(2)}) | ` +
        `${totais.percentual_loja.toFixed(1)}% Loja (R$ ${totais.valor_loja.toFixed(2)})`
      );
      
      // Atualizar apenas o item especÃ­fico e os totais da nota, sem recarregar tudo
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
      console.error('âŒ Erro ao salvar quantidade online:', error);
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
      
      // FECHAR o modal de detalhes quando abrir o de revisÃ£o
      setMostrarDetalhes(false);
      
      // Inicializar preÃ§os ajustados com valores atuais (adaptar para nova estrutura)
      const precosIniciais = {};
      response.data.itens.forEach(item => {
        if (item.produto_vinculado) {
          precosIniciais[item.produto_vinculado.produto_id] = {
            preco_venda: item.produto_vinculado.preco_venda_atual,
            margem: item.produto_vinculado.margem_atual
          };
        }
      });
      setPrecosAjustados(precosIniciais);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao carregar preview');
    }
  };

  // Alias para melhor semÃ¢ntica
  const carregarPreviewProcessamento = processarNota;

  const confirmarProcessamento = async () => {
    setLoading(true);
    try {
      // Atualizar preÃ§os se houver alteraÃ§Ãµes (adaptar para nova estrutura)
      const precosParaAtualizar = [];
      Object.entries(precosAjustados).forEach(([produtoId, dados]) => {
        const itemOriginal = previewProcessamento.itens.find(i => 
          i.produto_vinculado && i.produto_vinculado.produto_id == produtoId
        );
        if (itemOriginal && itemOriginal.produto_vinculado && 
            dados.preco_venda !== itemOriginal.produto_vinculado.preco_venda_atual) {
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
        `âœ… Nota processada! ${response.data.itens_processados} itens lanÃ§ados no estoque`,
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
    // Margem = (PreÃ§o Venda - Custo) / PreÃ§o Venda * 100
    // PreÃ§o Venda = Custo / (1 - Margem/100)
    if (margemDesejada >= 100) return custoNovo * 2;
    return custoNovo / (1 - margemDesejada / 100);
  };

  const calcularMargem = (precoVenda, custoNovo) => {
    // Margem = (PreÃ§o Venda - Custo) / PreÃ§o Venda * 100
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

      toast.success('ðŸ—‘ï¸ Nota excluÃ­da com sucesso!');
      
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
      toast.error('Erro ao carregar histÃ³rico de preÃ§os');
      setMostrarHistoricoPrecos(false);
    } finally {
      setCarregandoHistorico(false);
    }
  };

  const reverterNota = async (notaId, numeroNota) => {
    if (!confirm(`âš ï¸ Tem certeza que deseja REVERTER a entrada da nota ${numeroNota}?\n\nIsso irÃ¡:\nâ€¢ Remover as quantidades do estoque\nâ€¢ Excluir os lotes criados\nâ€¢ Estornar as contas a pagar lanÃ§adas\nâ€¢ Restaurar o status da nota para pendente`)) {
      return;
    }

    setLoading(true);
    try {
            const response = await api.post(
        `/notas-entrada/${notaId}/reverter`,
        {}
      );

      toast.success(
        `âœ… Entrada revertida! ${response.data.itens_revertidos} produtos ajustados`,
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

  const desvincularProduto = async (notaId, itemId) => {
    try {
      await api.post(`/notas-entrada/${notaId}/itens/${itemId}/desvincular`);
      
      toast.success('âœ… Produto desvinculado!');
      
      // Recarregar detalhes da nota
      const response = await api.get(`/notas-entrada/${notaId}`);
      // Ordenar itens por ID para manter ordem consistente
      if (response.data.itens) {
        response.data.itens.sort((a, b) => a.id - b.id);
      }
      setNotaSelecionada(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao desvincular produto');
    }
  };

  const abrirModalVincularProduto = (item) => {
    setItemSelecionado(item);
    setMostrarModalVincular(true);
  };

  // Detectar divergÃªncias entre NF e produto vinculado
  const detectarDivergencias = (item) => {
    // Verificar se tem produto vinculado (pode estar em produto_vinculado ou produto_nome)
    const produtoNome = item.produto_vinculado?.produto_nome || item.produto_nome;
    if (!produtoNome) return [];
    
    const divergencias = [];
    const descNF = item.descricao_nf || item.descricao || '';
    const descProd = produtoNome || '';
    
    if (!descNF || !descProd) return [];
    
    const descNFLower = descNF.toLowerCase();
    const descProdLower = descProd.toLowerCase();
    
    // Detectar peso/tamanho
    const regexPeso = /(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|un|und|unid)/gi;
    const pesosNF = [...descNFLower.matchAll(regexPeso)];
    const pesosProd = [...descProdLower.matchAll(regexPeso)];
    
    if (pesosNF.length > 0 && pesosProd.length > 0) {
      const pesoNF = pesosNF[0][0];
      const pesoProd = pesosProd[0][0];
      if (pesoNF !== pesoProd) {
        divergencias.push(`Peso/Tamanho diferente: NF="${pesoNF}" vs Produto="${pesoProd}"`);
      }
    }
    
    // Detectar cor
    const cores = ['preto', 'branco', 'vermelho', 'azul', 'verde', 'amarelo', 'rosa', 'roxo', 'laranja', 'marrom', 'cinza'];
    const corNF = cores.find(cor => descNFLower.includes(cor));
    const corProd = cores.find(cor => descProdLower.includes(cor));
    
    if (corNF && corProd && corNF !== corProd) {
      divergencias.push(`Cor diferente: NF="${corNF}" vs Produto="${corProd}"`);
    }
    
    // Detectar sabor (para raÃ§Ãµes)
    const sabores = ['frango', 'carne', 'peixe', 'cordeiro', 'salmao', 'salmÃ£o', 'atum', 'vegetais'];
    const saborNF = sabores.find(sabor => descNFLower.includes(sabor));
    const saborProd = sabores.find(sabor => descProdLower.includes(sabor));
    
    if (saborNF && saborProd && saborNF !== saborProd) {
      divergencias.push(`Sabor diferente: NF="${saborNF}" vs Produto="${saborProd}"`);
    }
    
    // Detectar animal (cachorro/gato)
    if ((descNFLower.includes('cao') || descNFLower.includes('cachorro') || descNFLower.includes('dog')) && 
        (descProdLower.includes('gato') || descProdLower.includes('cat'))) {
      divergencias.push('âš ï¸ Animal diferente: NF para CACHORRO mas produto Ã© para GATO');
    }
    
    if ((descNFLower.includes('gato') || descNFLower.includes('cat')) && 
        (descProdLower.includes('cao') || descProdLower.includes('cachorro') || descProdLower.includes('dog'))) {
      divergencias.push('âš ï¸ Animal diferente: NF para GATO mas produto Ã© para CACHORRO');
    }
    
    return divergencias;
  };

  const abrirModalCriarProduto = async (item) => {
    setItemSelecionadoParaCriar(item);
    setMostrarModalCriarProduto(true);
    setCarregandoSugestao(true);
    
    // Resetar formulÃ¡rio
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
      
      // Se o SKU jÃ¡ existe, usar a primeira sugestÃ£o alternativa (a recomendada com â­)
      if (response.data.ja_existe && response.data.sugestoes && response.data.sugestoes.length > 0) {
        const sugestaoRecomendada = response.data.sugestoes.find(s => s.padrao) || response.data.sugestoes[0];
        skuParaUsar = sugestaoRecomendada.sku;
      }
      
      // Preencher formulÃ¡rio com dados do item
      setFormProduto({
        sku: skuParaUsar,
        nome: item.descricao || item.descricao_produto || 'Produto sem nome',
        descricao: item.descricao || item.descricao_produto || '',
        preco_custo: item.valor_unitario.toString(),
        preco_venda: (item.valor_unitario * 1.5).toFixed(2), // SugestÃ£o de 50% de margem
        margem_lucro: '50',
        estoque_minimo: 10,
        estoque_maximo: 100
      });
      
      console.log('âœ… FormulÃ¡rio preenchido:', {
        sku: skuParaUsar,
        nome: item.descricao,
        preco_custo: item.valor_unitario
      });
      
    } catch (error) {
      toast.error('Erro ao buscar sugestÃµes de SKU');
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
            // Preparar dados convertendo strings para nÃºmeros
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
      
      toast.success(`âœ… Produto ${response.data.produto.codigo} criado e vinculado!`);
      
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
      toast.success('Todos os produtos jÃ¡ estÃ£o vinculados!');
      return;
    }
    
    const confirmacao = window.confirm(
      `Criar ${itensNaoVinculados.length} produto(s) automaticamente?\n\n` +
      `PadrÃµes aplicados:\n` +
      `â€¢ Estoque mÃ­nimo: 10\n` +
      `â€¢ Estoque mÃ¡ximo: 100\n` +
      `â€¢ Margem de lucro: 50%\n\n` +
      `VocÃª poderÃ¡ editar os produtos depois no cadastro.`
    );
    
    if (!confirmacao) return;
    
    try {
      setLoading(true);
      let sucessos = 0;
      let erros = 0;
      
      const loadingToast = toast.loading(`ðŸ“¦ Criando ${itensNaoVinculados.length} produtos...`);
      
      for (const item of itensNaoVinculados) {
        try {
          // Buscar SKU sugerido
          const skuResponse = await api.get(
            `/notas-entrada/${notaSelecionada.id}/itens/${item.id}/sugerir-sku`
          );
          
          let skuParaUsar = skuResponse.data.sku_proposto || item.codigo_produto || `PROD-${item.id}`;
          
          // Se jÃ¡ existe, usar primeira sugestÃ£o alternativa
          if (skuResponse.data.ja_existe && skuResponse.data.sugestoes?.length > 0) {
            const sugestaoRecomendada = skuResponse.data.sugestoes.find(s => s.padrao) || skuResponse.data.sugestoes[0];
            skuParaUsar = sugestaoRecomendada.sku;
          }
          
          // Criar produto com padrÃµes
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
        toast.success(`âœ… ${sucessos} produto(s) criado(s) com sucesso!`);
      }
      
      if (erros > 0) {
        toast.error(`âŒ ${erros} erro(s) ao criar produtos`);
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

  // FunÃ§Ãµes para determinar cores baseadas em comparaÃ§Ãµes
  const getCorComparacao = (valorNovo, valorAntigo, tipo) => {
    // ValidaÃ§Ãµes de seguranÃ§a
    const novo = parseFloat(valorNovo) || 0;
    const antigo = parseFloat(valorAntigo) || 0;
    
    if (novo === antigo) {
      return { cor: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-300', label: '=' };
    }
    
    // Para custo: menor Ã© melhor (verde), maior Ã© pior (vermelho)
    if (tipo === 'custo') {
      return novo < antigo 
        ? { cor: 'text-green-600', bg: 'bg-green-50', border: 'border-green-300', label: 'â†“' }
        : { cor: 'text-red-600', bg: 'bg-red-50', border: 'border-red-300', label: 'â†‘' };
    }
    
    // Para preÃ§o e margem: maior Ã© melhor (verde), menor Ã© pior (vermelho)
    return novo > antigo
      ? { cor: 'text-green-600', bg: 'bg-green-50', border: 'border-green-300', label: 'â†‘' }
      : { cor: 'text-red-600', bg: 'bg-red-50', border: 'border-red-300', label: 'â†“' };
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
    if (!confianca) return <span className="text-gray-400 text-sm">NÃ£o vinculado</span>;
    
    const nivel = confianca >= 90 ? 'alta' : confianca >= 70 ? 'media' : 'baixa';
    const styles = {
      alta: 'bg-green-100 text-green-800',
      media: 'bg-yellow-100 text-yellow-800',
      baixa: 'bg-orange-100 text-orange-800'
    };
    
    return (
      <span className={`px-2 py-1 rounded text-xs font-semibold ${styles[nivel]}`}>
        {confianca.toFixed(1)}% {nivel === 'alta' ? 'âœ…' : nivel === 'media' ? 'âš ï¸' : 'âš¡'}
      </span>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">ðŸ“„ Entrada por NF-e (XML)</h1>
        <p className="text-gray-600">Importe notas fiscais eletrÃ´nicas e vincule produtos automaticamente</p>
      </div>

      {/* Ãrea de Upload */}
      <div className="bg-white rounded-lg shadow-md p-8 mb-6">
        <div className="text-center">
          <div className="mb-4">
            <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2">
            {uploadingFile ? 'â³ Processando XML...' : 'Selecione o arquivo XML da NF-e'}
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            O sistema irÃ¡ processar automaticamente os dados da nota fiscal
          </p>
          
          {/* BotÃµes de Upload */}
          <div className="flex gap-3 justify-center">
            {/* Upload Ãšnico */}
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
                {uploadingFile ? 'â³ Processando...' : 'ðŸ“ Upload Ãšnico'}
              </span>
            </label>
            
            {/* Upload MÃºltiplo */}
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
                {uploadingLote ? 'â³ Processando Lote...' : 'ðŸ“¦ Upload MÃºltiplo'}
              </span>
            </label>
          </div>
          
          <p className="text-xs text-gray-500 mt-3">
            Formatos aceitos: XML de NF-e (padrÃ£o SEFAZ)
          </p>
        </div>
      </div>

      {/* EstatÃ­sticas */}
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
                <th className="px-4 py-3 text-left text-sm font-semibold">Data EmissÃ£o</th>
                <th className="px-4 py-3 text-right text-sm font-semibold">Valor</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">Itens</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">Status</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">AÃ§Ãµes</th>
              </tr>
            </thead>
            <tbody>
              {notasEntrada.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                    Nenhuma nota fiscal importada ainda. FaÃ§a o upload de um XML acima.
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
                            ðŸ”— Vincular
                          </button>
                        )}
                        {nota.entrada_estoque_realizada ? (
                          <button
                            onClick={() => reverterNota(nota.id, nota.numero_nota)}
                            className="text-orange-600 hover:text-orange-800 font-semibold text-sm"
                            title="Reverter entrada no estoque"
                          >
                            â†©ï¸ Reverter
                          </button>
                        ) : (
                          <button
                            onClick={() => excluirNota(nota.id, nota.numero_nota)}
                            className="text-red-600 hover:text-red-800 font-semibold text-sm"
                            title="Excluir nota"
                          >
                            ðŸ—‘ï¸ Excluir
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
            {/* CabeÃ§alho */}
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">ðŸ“„ Detalhes da NF-e</h2>
                <p className="text-sm text-gray-600">Chave: {notaSelecionada.chave_acesso}</p>
              </div>
              <button
                onClick={() => {
                  setMostrarDetalhes(false);
                  setNotaSelecionada(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                Ã—
              </button>
            </div>

            {/* InformaÃ§Ãµes da Nota */}
            <div className="px-6 py-4 border-b bg-gray-50">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Fornecedor:</span>
                  <div className="font-semibold">{notaSelecionada.fornecedor_nome}</div>
                  <div className="text-xs text-gray-500">{notaSelecionada.fornecedor_cnpj}</div>
                  {notaSelecionada.fornecedor_id && (
                    <div className="text-xs text-green-600 mt-1">âœ… Cadastrado</div>
                  )}
                </div>
                <div>
                  <span className="text-gray-600">Data EmissÃ£o:</span>
                  <div className="font-semibold">{new Date(notaSelecionada.data_emissao).toLocaleDateString()}</div>
                </div>
                <div>
                  <span className="text-gray-600">Valor Total:</span>
                  <div className="font-bold text-lg text-green-600">R$ {(notaSelecionada.valor_total || 0).toFixed(2)}</div>
                </div>
              </div>
            </div>

            {/* Alerta de Fornecedor Novo - VersÃ£o Compacta */}
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
                    ðŸ“ Completar Cadastro
                  </button>
                </div>
              </div>
            )}

            {/* Itens da Nota */}
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-xl text-gray-800">
                  ðŸ“¦ Produtos da Nota ({notaSelecionada.itens.length})
                </h3>
                
                {notaSelecionada.status === 'pendente' && 
                 notaSelecionada.itens.some(item => !item.produto_id) && (
                  <button
                    onClick={criarTodosProdutosNaoVinculados}
                    disabled={loading}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400 flex items-center gap-2 text-sm"
                    title="Cria automaticamente todos os produtos nÃ£o vinculados com os padrÃµes: Estoque mÃ­n: 10, mÃ¡x: 100, Margem: 50%"
                  >
                    <span>âœ¨ Criar Todos NÃ£o Vinculados</span>
                    <span className="text-xs bg-purple-800 px-2 py-0.5 rounded">
                      {notaSelecionada.itens.filter(i => !i.produto_id).length}
                    </span>
                  </button>
                )}
              </div>
              
              <div className="space-y-3">
                {notaSelecionada.itens.map(item => {
                  const divergencias = detectarDivergencias(item);
                  const temDivergencia = divergencias.length > 0;
                  
                  return (
                    <div key={item.id} className="border-2 border-gray-400 rounded-lg overflow-hidden bg-white shadow-sm">
                      {/* Grade de 2 Colunas: NF-e (esquerda) | ConexÃ£o | Produto Sistema (direita) */}
                      <div className="grid grid-cols-[1fr_auto_1fr] gap-0">
                        {/* COLUNA ESQUERDA: Dados da NF-e */}
                        <div className="bg-blue-50 border-r-2 border-gray-300 p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold">NF-e</div>
                            {getConfiancaBadge(item.confianca_vinculo)}
                          </div>
                          
                          <div className="font-semibold text-base mb-2 text-blue-900">{item.descricao}</div>
                          
                          <div className="space-y-1.5 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600">CÃ³digo:</span>
                              <span className="font-mono font-semibold">{item.codigo_produto}</span>
                            </div>
                            {item.ean && item.ean !== 'SEM GTIN' && (
                              <div className="flex justify-between">
                                <span className="text-gray-600">EAN:</span>
                                <span className="font-mono font-semibold">{item.ean}</span>
                              </div>
                            )}
                            <div className="flex justify-between">
                              <span className="text-gray-600">NCM:</span>
                              <span className="font-mono font-semibold">{item.ncm}</span>
                            </div>
                            <div className="flex justify-between border-t pt-1.5 mt-1.5">
                              <span className="text-gray-600">Qtd:</span>
                              <span className="font-semibold">{item.quantidade}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Valor Unit.:</span>
                              <span className="font-semibold">R$ {item.valor_unitario.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Total:</span>
                              <span className="font-semibold text-green-600">R$ {item.valor_total.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">CFOP:</span>
                              <span className="font-semibold">{item.cfop}</span>
                            </div>
                          </div>

                          {/* Lote e Validade */}
                          {(item.lote || item.data_validade) && (
                            <div className="mt-3 pt-3 border-t space-y-2">
                              {item.lote && (
                                <div className="text-xs">
                                  <span className="text-gray-600">ðŸ“¦ Lote:</span>
                                  <div className="font-semibold text-purple-800">{item.lote}</div>
                                </div>
                              )}
                              {item.data_validade && (
                                <div className="text-xs">
                                  <span className="text-gray-600">ðŸ“… Validade:</span>
                                  <div className="font-semibold text-orange-800">
                                    {new Date(item.data_validade).toLocaleDateString('pt-BR')}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* COLUNA CENTRAL: Ãcone de ConexÃ£o + Alerta de DivergÃªncia */}
                        <div className="flex flex-col items-center justify-center bg-gray-100 px-2 py-4">
                          {item.produto_id ? (
                            <>
                              <button
                                onClick={() => desvincularProduto(notaSelecionada.id, item.id)}
                                className="text-3xl text-green-600 hover:text-red-600 transition-colors mb-2"
                                title="âœ… Vinculado - Clique para desvincular"
                              >
                                âœ“
                              </button>
                              {temDivergencia && (
                                <div className="bg-red-100 border-2 border-red-500 rounded-lg p-2 max-w-[200px]">
                                  <div className="text-center">
                                    <div className="text-2xl mb-1">âš ï¸</div>
                                    <div className="font-bold text-red-700 text-xs mb-1">
                                      DIVERGÃŠNCIA!
                                    </div>
                                    <div className="text-[10px] text-red-600 space-y-0.5">
                                      {divergencias.map((div, idx) => (
                                        <div key={idx}>â€¢ {div}</div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </>
                          ) : (
                            <div className="text-3xl text-gray-400" title="âŒ NÃ£o vinculado">
                              âœ•
                            </div>
                          )}
                        </div>

                        {/* COLUNA DIREITA: Produto do Sistema */}
                        <div className={`p-4 ${item.produto_id ? 'bg-green-50' : 'bg-gray-50'}`}>

                        {/* COLUNA DIREITA: Produto do Sistema */}
                        <div className={`p-4 ${item.produto_id ? 'bg-green-50' : 'bg-gray-50'}`}>
                          {notaSelecionada.status === 'pendente' ? (
                            <>
                              {item.produto_id ? (
                                <>
                                  <div className="flex items-center gap-2 mb-3">
                                    <div className="bg-green-600 text-white px-2 py-1 rounded text-xs font-bold">
                                      âœ… PRODUTO SISTEMA
                                    </div>
                                  </div>
                                  
                                  <div className="font-semibold text-base mb-3 text-green-900">
                                    {item.produto_nome}
                                  </div>

                                  <div className="text-xs text-green-700 mb-3 italic">
                                    ðŸ’¡ Para alterar o vÃ­nculo, selecione outro produto ou clique no âœ“ para desvincular
                                  </div>

                                  {/* Select para trocar produto */}
                                  <select
                                    value={item.produto_id}
                                    onChange={(e) => {
                                      if (e.target.value && e.target.value != item.produto_id) {
                                        vincularProduto(notaSelecionada.id, item.id, e.target.value);
                                      }
                                    }}
                                    className="w-full px-3 py-2 border-2 border-green-400 rounded text-sm focus:ring-2 focus:ring-green-500"
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
                                </>
                              ) : (
                                <>
                                  <div className="flex items-center gap-2 mb-3">
                                    <div className="bg-orange-600 text-white px-2 py-1 rounded text-xs font-bold">
                                      âš ï¸ NÃƒO VINCULADO
                                    </div>
                                  </div>
                                  
                                  <div className="space-y-3">
                                    {/* Campo de pesquisa */}
                                    <div>
                                      <label className="block text-xs font-semibold text-gray-700 mb-1">
                                        ðŸ” Pesquisar produto existente:
                                      </label>
                                      <input
                                        type="text"
                                        placeholder="Digite nome ou SKU..."
                                        value={filtroProduto[item.id] || ''}
                                        onChange={(e) => setFiltroProduto({...filtroProduto, [item.id]: e.target.value})}
                                        className="w-full px-3 py-2 border-2 border-gray-400 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                                      />
                                    </div>
                                    
                                    {/* Lista de produtos filtrados */}
                                    {filtroProduto[item.id] && filtroProduto[item.id].length >= 2 && (
                                      <div className="border-2 border-gray-300 rounded max-h-48 overflow-y-auto bg-white">
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
                                            if (a.ativo === b.ativo) return 0;
                                            return a.ativo ? -1 : 1;
                                          })
                                          .slice(0, 15)
                                          .map(p => (
                                            <button
                                              key={`produto-${item.id}-${p.id}`}
                                              type="button"
                                              onClick={() => {
                                                vincularProduto(notaSelecionada.id, item.id, p.id);
                                                setFiltroProduto({...filtroProduto, [item.id]: ''});
                                              }}
                                              className={`w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-200 last:border-b-0 text-xs ${!p.ativo ? 'text-red-600 font-bold' : ''}`}
                                            >
                                              {!p.ativo && 'ðŸ”´ '}{p.codigo} - {p.nome}
                                              {!p.ativo && ' [INATIVO]'} 
                                              <span className="text-gray-500 ml-1">(Est: {p.estoque_atual || 0})</span>
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
                                          <div className="px-3 py-4 text-center text-gray-500 text-xs">
                                            âŒ Nenhum produto encontrado
                                          </div>
                                        )}
                                      </div>
                                    )}
                                    
                                    <div className="flex items-center gap-2">
                                      <div className="flex-1 border-t border-gray-300"></div>
                                      <span className="text-xs text-gray-500">ou</span>
                                      <div className="flex-1 border-t border-gray-300"></div>
                                    </div>

                                    <button
                                      onClick={() => abrirModalCriarProduto(item)}
                                      className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 text-sm"
                                    >
                                      âž• Criar Novo Produto
                                    </button>
                                  </div>
                                </>
                              )}
                            </>
                          ) : (
                            // Nota jÃ¡ processada - apenas visualizaÃ§Ã£o
                            <div>
                              {item.produto_id ? (
                                <>
                                  <div className="bg-green-600 text-white px-2 py-1 rounded text-xs font-bold inline-block mb-2">
                                    âœ… VINCULADO
                                  </div>
                                  <div className="font-semibold text-base text-green-900">
                                    {item.produto_nome}
                                  </div>
                                </>
                              ) : (
                                <div className="bg-gray-600 text-white px-2 py-1 rounded text-xs font-bold inline-block">
                                  âš ï¸ NÃƒO VINCULADO
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Rateio de Estoque (se modo PARCIAL) - Expande por toda a largura */}
                      {notaSelecionada.status === 'pendente' && 
                       tipoRateio === 'parcial' && 
                       item.produto_id && (
                        <div className="col-span-3 p-4 border-t-2 border-gray-300 bg-gradient-to-r from-blue-50 via-gray-50 to-green-50">
                          <h4 className="font-medium text-gray-700 mb-3 flex items-center text-sm">
                            ðŸ“¦ Quantidade destinada ao estoque online
                          </h4>
                          
                          <div className="grid grid-cols-3 gap-4">
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">
                                ðŸ“‹ Total NF
                              </label>
                              <input
                                type="number"
                                value={item.quantidade}
                                disabled
                                className="w-full px-3 py-2 border border-gray-300 rounded bg-gray-100 text-base font-semibold"
                              />
                            </div>
                            
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">
                                ðŸŒ Online
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
                                className="w-full px-3 py-2 border-2 border-blue-400 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-base font-semibold"
                                placeholder="0"
                              />
                            </div>
                            
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">
                                ðŸª Loja
                              </label>
                              <input
                                type="number"
                                value={(item.quantidade - (quantidadesOnline[item.id] ?? item.quantidade_online ?? 0)).toFixed(2)}
                                disabled
                                className="w-full px-3 py-2 border border-gray-300 rounded bg-gray-100 text-base font-semibold"
                              />
                            </div>
                          </div>
                          
                          <div className="mt-3 text-sm text-gray-700 bg-white rounded-lg p-3 border border-gray-300 font-medium">
                            ðŸ’µ Valor online: R$ {((quantidadesOnline[item.id] ?? item.quantidade_online ?? 0) * item.valor_unitario).toFixed(2)}
                          </div>
                          
                          {(quantidadesOnline[item.id] !== undefined && 
                            quantidadesOnline[item.id] !== item.quantidade_online) ? (
                            <button
                              onClick={() => salvarQuantidadeOnlineItem(
                                notaSelecionada.id, 
                                item.id, 
                                quantidadesOnline[item.id]
                              )}
                              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 mt-3 text-sm"
                            >
                              ðŸ’¾ Salvar DistribuiÃ§Ã£o
                            </button>
                          ) : (
                            item.quantidade_online !== null && item.quantidade_online !== undefined && (
                              <div className="mt-3 text-sm text-green-700 bg-green-50 rounded-lg p-3 border border-green-200 flex items-center justify-center font-medium">
                                âœ… Salvo: {item.quantidade_online} online / {(item.quantidade - item.quantidade_online).toFixed(2)} loja
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>

                    {notaSelecionada.status === 'processada' && item.produto_id && (
                      <div className="mt-3 pt-3 border-t bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <span className="text-blue-800 font-semibold">âœ… LanÃ§ado no estoque:</span>
                        <span className="ml-2">{item.produto_nome}</span>
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            </div>

            {/* RodapÃ© com AÃ§Ãµes */}
            {notaSelecionada.status === 'pendente' && (
              <div className="sticky bottom-0 bg-white border-t px-6 py-4 space-y-3">
                {/* SeÃ§Ã£o de Rateio - ANTES de processar */}
                <div className="bg-gray-50 border border-gray-200 rounded p-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-700">
                      ðŸ“Š DistribuiÃ§Ã£o (informativo para relatÃ³rios)
                    </h4>
                    <div className="text-xs text-gray-500">
                      Estoque unificado â€¢ ClassificaÃ§Ã£o apenas para anÃ¡lises
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
                      ðŸª Loja
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
                      ðŸŒ Online
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
                      ðŸ“Š Parcial
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
                      ðŸ’¡ Defina a quantidade destinada ao <strong>estoque online</strong> em cada produto acima. O sistema calcula automaticamente a % baseado nos valores.
                    </div>
                  )}
                </div>

                {/* Barra de Status e BotÃµes de AÃ§Ã£o */}
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
                        {loading ? 'â³ Revertendo...' : 'â†©ï¸ Reverter Entrada'}
                      </button>
                    ) : (
                      <>
                        {!notaSelecionada.entrada_estoque_realizada && (
                          <button
                            onClick={() => excluirNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                            disabled={loading}
                            className="px-6 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400"
                          >
                            ðŸ—‘ï¸ Excluir Nota
                          </button>
                        )}
                        {notaSelecionada.itens.some(i => i.produto_id) && (
                          <>
                            <button
                              onClick={() => carregarPreviewProcessamento(notaSelecionada.id)}
                              disabled={loading}
                              className="px-6 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400"
                            >
                              ðŸ’° Revisar PreÃ§os
                            </button>
                            <button
                              onClick={() => processarNota(notaSelecionada.id)}
                              disabled={loading}
                              className="px-6 py-2 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400"
                            >
                              {loading ? 'â³ Processando...' : 'âœ… Processar Nota'}
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
                <h2 className="text-xl font-bold">âž• Criar Novo Produto</h2>
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
                Ã—
              </button>
            </div>

            <div className="px-6 py-4">
              {carregandoSugestao ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-600">Gerando sugestÃµes de SKU...</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* InformaÃ§Ãµes do Item da NF-e */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="font-semibold text-blue-900 mb-2">ðŸ“„ Dados da NF-e:</div>
                    <div className="text-sm space-y-1 text-blue-800">
                      <div><strong>DescriÃ§Ã£o:</strong> {itemSelecionadoParaCriar.descricao}</div>
                      <div><strong>CÃ³digo Fornecedor:</strong> {itemSelecionadoParaCriar.codigo_produto}</div>
                      <div><strong>NCM:</strong> {itemSelecionadoParaCriar.ncm}</div>
                      {itemSelecionadoParaCriar.ean && (
                        <div><strong>EAN:</strong> {itemSelecionadoParaCriar.ean}</div>
                      )}
                      <div><strong>Valor UnitÃ¡rio:</strong> R$ {itemSelecionadoParaCriar.valor_unitario.toFixed(2)}</div>
                    </div>
                  </div>

                  {/* Alerta de SKU existente */}
                  {sugestaoSku?.ja_existe && (
                    <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <span className="text-2xl">âš ï¸</span>
                        <div className="flex-1">
                          <div className="font-semibold text-yellow-900 mb-2">
                            CÃ³digo do fornecedor "{sugestaoSku.sku_proposto}" jÃ¡ estÃ¡ em uso!
                          </div>
                          <div className="text-sm text-yellow-800 mb-3">
                            Produto existente: <strong>{sugestaoSku.produto_existente.nome}</strong><br/>
                            <span className="text-xs">Um SKU alternativo foi sugerido automaticamente. VocÃª pode alterar se preferir.</span>
                          </div>
                          <div className="text-sm text-yellow-800 mb-2 font-semibold">
                            Outras opÃ§Ãµes de SKU disponÃ­veis:
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
                                {sug.sku} {sug.padrao && 'â­'}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sucesso - SKU disponÃ­vel */}
                  {sugestaoSku && !sugestaoSku.ja_existe && (
                    <div className="bg-green-50 border border-green-300 rounded-lg p-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">âœ…</span>
                        <div className="text-sm text-green-800">
                          <strong>SKU disponÃ­vel!</strong> O cÃ³digo do fornecedor pode ser usado diretamente.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* FormulÃ¡rio */}
                  <div className="space-y-4">
                    {/* SKU */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        SKU / CÃ³digo do Produto *
                        <span className="text-xs text-gray-500 font-normal ml-2">(Baseado no cÃ³digo do fornecedor)</span>
                      </label>
                      <input
                        type="text"
                        value={formProduto.sku}
                        onChange={(e) => setFormProduto({ ...formProduto, sku: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono"
                        placeholder="Ex: MGZ-12345"
                      />
                      <p className="text-xs text-gray-500 mt-1">ðŸ’¡ VocÃª pode editar o SKU se preferir</p>
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

                    {/* DescriÃ§Ã£o */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        DescriÃ§Ã£o
                      </label>
                      <textarea
                        value={formProduto.descricao}
                        onChange={(e) => setFormProduto({ ...formProduto, descricao: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        rows="2"
                        placeholder="DescriÃ§Ã£o detalhada (opcional)"
                      />
                    </div>

                    {/* PreÃ§os */}
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">
                          PreÃ§o de Custo *
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
                          PreÃ§o de Venda *
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
                          Estoque MÃ­nimo
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
                          Estoque MÃ¡ximo
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

            {/* RodapÃ© */}
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
                {loading ? 'â³ Criando...' : 'âœ… Criar e Vincular Produto'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de VisualizaÃ§Ã£o da Nota */}
      {mostrarVisualizacao && notaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold">ðŸ“„ NF-e {notaSelecionada.numero_nota}</h2>
                  <p className="text-blue-100 mt-1">SÃ©rie: {notaSelecionada.serie}</p>
                </div>
                <button
                  onClick={() => {
                    setMostrarVisualizacao(false);
                    setNotaSelecionada(null);
                  }}
                  className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
                >
                  âœ•
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* InformaÃ§Ãµes da Nota */}
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                  <h3 className="font-semibold text-gray-700 mb-3">ðŸ“‹ Dados da Nota</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Data EmissÃ£o:</span>
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
                  <h3 className="font-semibold text-gray-700 mb-3">ðŸ¢ Fornecedor</h3>
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
                <div className="text-xs text-gray-600 mb-1">ðŸ”‘ Chave de Acesso</div>
                <div className="font-mono text-xs break-all">{notaSelecionada.chave_acesso}</div>
              </div>

              {/* Status de VinculaÃ§Ã£o */}
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
                  <div className="text-sm text-gray-600">NÃ£o Vinculados</div>
                </div>
              </div>

              {/* Itens da Nota */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">ðŸ“¦ Itens da Nota</h3>
                <div className="space-y-3">
                  {notaSelecionada.itens?.map((item, index) => (
                    <div key={item.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="font-semibold text-gray-800">{item.descricao}</div>
                          <div className="text-xs text-gray-500 mt-1">
                            CÃ³digo: {item.codigo_produto} | NCM: {item.ncm}
                          </div>
                        </div>
                        {item.vinculado ? (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">
                            âœ“ Vinculado
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-semibold rounded">
                            âš  NÃ£o Vinculado
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
                              <span className="text-gray-600">ðŸ“¦ Lote:</span>
                              <div className="font-semibold text-purple-800">{item.lote}</div>
                            </div>
                          )}
                          {item.data_validade && (
                            <div className="bg-orange-50 border border-orange-200 rounded p-2">
                              <span className="text-gray-600">ðŸ“… Validade:</span>
                              <div className="font-semibold text-orange-800">
                                {new Date(item.data_validade).toLocaleDateString('pt-BR')}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {item.vinculado && item.produto_nome && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <span className="text-xs text-gray-600">â†’ Produto vinculado: </span>
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
                  <span className="text-green-600 font-semibold">âœ… Entrada realizada no estoque</span>
                ) : (
                  <span className="text-orange-600 font-semibold">âš ï¸ Entrada ainda nÃ£o processada</span>
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
                      ðŸ’° Revisar PreÃ§os e Processar
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
                    ðŸ”— Vincular Produtos
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

      {/* Modal de RevisÃ£o de PreÃ§os */}
      {mostrarRevisaoPrecos && previewProcessamento && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6">
              <h2 className="text-2xl font-bold">ðŸ’° RevisÃ£o de PreÃ§os e Custos</h2>
              <p className="text-purple-100 mt-1">
                NF-e {previewProcessamento.numero_nota} - {previewProcessamento.fornecedor_nome}
              </p>
            </div>

            {/* Resumo de AlteraÃ§Ãµes */}
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-semibold text-gray-700">Filtrar:</span>
                {(() => {
                  // Adaptar para estrutura flat ou aninhada
                  const itensVinculados = previewProcessamento.itens.filter(i => 
                    i.produto_vinculado !== null || i.produto_id !== null
                  );
                  const aumentos = itensVinculados.filter(i => {
                    const variacao = i.produto_vinculado?.variacao_custo_percentual || i.variacao_custo_percentual || 0;
                    return variacao > 0;
                  }).length;
                  const reducoes = itensVinculados.filter(i => {
                    const variacao = i.produto_vinculado?.variacao_custo_percentual || i.variacao_custo_percentual || 0;
                    return variacao < 0;
                  }).length;
                  const iguais = itensVinculados.filter(i => {
                    const variacao = i.produto_vinculado?.variacao_custo_percentual || i.variacao_custo_percentual || 0;
                    return variacao === 0;
                  }).length;
                  const total = itensVinculados.length;
                  
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
                        <span className="text-base">ðŸ“‹</span>
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
                          <span className="text-base">ðŸ“ˆ</span>
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
                          <span className="text-base">ðŸ“‰</span>
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
                          <span className="text-base">âž¡ï¸</span>
                          {iguais} sem alteraÃ§Ã£o
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
                    // Verificar se tem produto vinculado (pode estar em produto_vinculado ou produto_id)
                    const vinculado = item.produto_vinculado !== null || item.produto_id !== null;
                    
                    if (!vinculado) return false;
                    
                    // Pegar variaÃ§Ã£o de custo (pode estar em produto_vinculado ou diretamente no item)
                    const custoVariacao = item.produto_vinculado?.variacao_custo_percentual || item.variacao_custo_percentual || 0;
                    
                    if (filtroCusto === 'todos') return true;
                    if (filtroCusto === 'aumentou') return custoVariacao > 0;
                    if (filtroCusto === 'diminuiu') return custoVariacao < 0;
                    if (filtroCusto === 'igual') return custoVariacao === 0;
                    return true;
                  })
                  .map((item) => {
                  // Adaptar para estrutura flat ou aninhada
                  const produtoVinc = item.produto_vinculado || {
                    produto_id: item.produto_id,
                    produto_nome: item.produto_nome,
                    produto_codigo: item.produto_codigo,
                    produto_ean: item.produto_ean,
                    custo_anterior: item.custo_anterior,
                    custo_novo: item.custo_novo,
                    variacao_custo_percentual: item.variacao_custo_percentual,
                    preco_venda_atual: item.preco_venda_atual,
                    margem_atual: item.margem_atual,
                    estoque_atual: item.estoque_atual
                  };
                  
                  if (!produtoVinc.produto_id) return null;
                  
                  if (!produtoVinc.produto_id) return null;
                  
                  const custoVariacao = produtoVinc.variacao_custo_percentual || 0;
                  const custoAumentou = custoVariacao > 0;
                  
                  const precosAtuais = precosAjustados[produtoVinc.produto_id] || {
                    preco_venda: produtoVinc.preco_venda_atual || 0,
                    margem: produtoVinc.margem_atual || 0
                  };

                  return (
                    <div key={item.item_id} className="border-2 border-gray-300 rounded-xl overflow-hidden shadow-md hover:shadow-xl transition-all">
                      {/* Header com nome do produto e quantidade */}
                      <div className="bg-gradient-to-r from-blue-600 to-blue-500 text-white p-4">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h3 className="font-bold text-xl mb-1">{produtoVinc.produto_nome}</h3>
                            <p className="text-sm text-blue-100">SKU: {produtoVinc.produto_codigo}</p>
                          </div>
                          <div className="text-right">
                            <button
                              onClick={() => buscarHistoricoPrecos(produtoVinc.produto_id, produtoVinc.produto_nome)}
                              className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-sm font-medium transition-colors"
                            >
                              ðŸ“Š HistÃ³rico
                            </button>
                            <div className="mt-1 text-sm">
                              Quantidade <strong>{item.quantidade || item.quantidade_nf || 0}</strong>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="p-5 bg-white space-y-4">
                        {/* ComparaÃ§Ã£o de Custos */}
                        <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                          <div>
                            <div className="text-xs text-gray-500 mb-1">ðŸ’µ Custo Anterior</div>
                            <div className="text-2xl font-bold text-gray-700">
                              R$ {(produtoVinc.custo_anterior || 0).toFixed(2)}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500 mb-1">ðŸ†• Custo Novo</div>
                            <div className="text-2xl font-bold text-blue-600">
                              R$ {(produtoVinc.custo_novo || 0).toFixed(2)}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500 mb-1">ðŸ“Š VariaÃ§Ã£o</div>
                            <div className={`text-2xl font-bold ${custoAumentou ? 'text-red-600' : custoVariacao < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                              {custoVariacao > 0 ? 'â†—' : custoVariacao < 0 ? 'â†˜' : 'âž¡'} {Math.abs(custoVariacao).toFixed(1)}%
                            </div>
                          </div>
                        </div>

                        {/* Campos de PreÃ§o e Margem */}
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-semibold text-gray-700 mb-2">
                              ðŸ’° PreÃ§o de Venda
                            </label>
                            <div className="relative">
                              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                              <input
                                type="number"
                                step="0.01"
                                value={precosAtuais.preco_venda}
                                onChange={(e) => atualizarPrecoVenda(
                                  produtoVinc.produto_id,
                                  parseFloat(e.target.value) || 0,
                                  produtoVinc.custo_novo
                                )}
                                className="w-full pl-10 pr-3 py-3 border-2 border-gray-300 rounded-lg text-xl font-bold focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              />
                            </div>
                            <div className="mt-1 text-xs text-gray-500">
                              Anterior: R$ {produtoVinc.preco_venda_atual.toFixed(2)}
                            </div>
                          </div>

                          <div>
                            <label className="block text-sm font-semibold text-gray-700 mb-2">
                              ðŸ“ˆ Margem de Lucro
                            </label>
                            <div className="relative">
                              <input
                                type="number"
                                step="0.1"
                                value={precosAtuais.margem}
                                onChange={(e) => atualizarMargem(
                                  produtoVinc.produto_id,
                                  parseFloat(e.target.value) || 0,
                                  produtoVinc.custo_novo
                                )}
                                className="w-full pr-10 pl-3 py-3 border-2 border-gray-300 rounded-lg text-xl font-bold focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              />
                              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">%</span>
                            </div>
                            <div className="mt-1 text-xs text-gray-500">
                              Com o novo custo
                            </div>
                          </div>
                        </div>

                        {/* AnÃ¡lise Comparativa */}
                        <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                          <h4 className="text-sm font-semibold text-purple-800 mb-3">ðŸ“Š AnÃ¡lise Comparativa (Valores Anteriores)</h4>
                          <div className="grid grid-cols-3 gap-4 text-center">
                            <div>
                              <div className="text-xs text-gray-600 mb-1">ðŸ’µ Custo Anterior</div>
                              <div className="text-lg font-bold text-gray-700">R$ {(produtoVinc.custo_anterior || 0).toFixed(2)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-600 mb-1">ðŸ’° PreÃ§o Anterior</div>
                              <div className="text-lg font-bold text-blue-700">R$ {(produtoVinc.preco_venda_atual || 0).toFixed(2)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-600 mb-1">ðŸ“ˆ Margem Anterior</div>
                              <div className="text-lg font-bold text-purple-700">{(produtoVinc.margem_atual || 0).toFixed(1)}%</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                }).filter(Boolean)}
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 p-6 bg-gray-50 flex justify-between items-center">
              <button
                onClick={() => {
                  setMostrarRevisaoPrecos(false);
                  setPreviewProcessamento(null);
                }}
                className="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-semibold transition-colors"
              >
                âŒ Cancelar
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
                  {loading ? 'â³ Processando...' : 'âœ… Confirmar e Processar Nota'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de HistÃ³rico de PreÃ§os */}
      {mostrarHistoricoPrecos && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6">
              <h2 className="text-2xl font-bold">ðŸ“Š HistÃ³rico de AlteraÃ§Ãµes de PreÃ§os</h2>
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
                  <p className="text-gray-500 text-lg">Nenhuma alteraÃ§Ã£o de preÃ§o registrada</p>
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
                              {hist.motivo === 'nfe_entrada' ? 'ðŸ“¦' : 
                               hist.motivo === 'nfe_revisao_precos' ? 'ðŸ’°' : 
                               hist.motivo === 'manual' ? 'âœï¸' : 'ðŸ“'}
                            </span>
                            <span className="font-semibold text-gray-800">
                              {hist.motivo === 'nfe_entrada' ? 'Entrada NF-e' :
                               hist.motivo === 'nfe_revisao_precos' ? 'RevisÃ£o de PreÃ§os' :
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

                      {/* AlteraÃ§Ãµes de PreÃ§o */}
                      <div className="grid grid-cols-2 gap-4">
                        {/* Custo */}
                        {hist.preco_custo_anterior !== null && hist.preco_custo_novo !== null && (
                          <div className="bg-blue-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 font-semibold mb-2">ðŸ’µ CUSTO</div>
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-sm text-gray-500">Anterior</div>
                                <div className="text-lg font-bold">R$ {hist.preco_custo_anterior.toFixed(2)}</div>
                              </div>
                              <div className="text-2xl">â†’</div>
                              <div>
                                <div className="text-sm text-gray-500">Novo</div>
                                <div className="text-lg font-bold text-blue-700">R$ {hist.preco_custo_novo.toFixed(2)}</div>
                              </div>
                            </div>
                            {hist.variacao_custo_percentual !== null && hist.variacao_custo_percentual !== 0 && (
                              <div className={`mt-2 text-sm font-semibold text-center ${
                                hist.variacao_custo_percentual > 0 ? 'text-red-600' : 'text-green-600'
                              }`}>
                                {hist.variacao_custo_percentual > 0 ? 'â†‘' : 'â†“'} {Math.abs(hist.variacao_custo_percentual).toFixed(2)}%
                              </div>
                            )}
                          </div>
                        )}

                        {/* PreÃ§o de Venda */}
                        {hist.preco_venda_anterior !== null && hist.preco_venda_novo !== null && (
                          <div className="bg-green-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 font-semibold mb-2">ðŸ’² PREÃ‡O DE VENDA</div>
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-sm text-gray-500">Anterior</div>
                                <div className="text-lg font-bold">R$ {hist.preco_venda_anterior.toFixed(2)}</div>
                              </div>
                              <div className="text-2xl">â†’</div>
                              <div>
                                <div className="text-sm text-gray-500">Novo</div>
                                <div className="text-lg font-bold text-green-700">R$ {hist.preco_venda_novo.toFixed(2)}</div>
                              </div>
                            </div>
                            {hist.variacao_venda_percentual !== null && hist.variacao_venda_percentual !== 0 && (
                              <div className={`mt-2 text-sm font-semibold text-center ${
                                hist.variacao_venda_percentual > 0 ? 'text-green-600' : 'text-red-600'
                              }`}>
                                {hist.variacao_venda_percentual > 0 ? 'â†‘' : 'â†“'} {Math.abs(hist.variacao_venda_percentual).toFixed(2)}%
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Margens */}
                      {hist.margem_anterior !== null && hist.margem_nova !== null && (
                        <div className="mt-3 bg-purple-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 font-semibold mb-2">ðŸ“ˆ MARGEM DE LUCRO</div>
                          <div className="flex items-center justify-around">
                            <div className="text-center">
                              <div className="text-sm text-gray-500">Anterior</div>
                              <div className="text-xl font-bold">{hist.margem_anterior.toFixed(1)}%</div>
                            </div>
                            <div className="text-2xl">â†’</div>
                            <div className="text-center">
                              <div className="text-sm text-gray-500">Nova</div>
                              <div className="text-xl font-bold text-purple-700">{hist.margem_nova.toFixed(1)}%</div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* ObservaÃ§Ãµes */}
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
                ðŸ“¦ Resultado do Processamento em Lote
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
                                {resultado.sucesso ? 'âœ…' : 'âŒ'}
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
                                  <strong>Produtos:</strong> {resultado.produtos_vinculados} vinculados, {resultado.produtos_nao_vinculados} nÃ£o vinculados
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
                {uploadingLote ? 'â³ Processando...' : 'Fechar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EntradaXML;

