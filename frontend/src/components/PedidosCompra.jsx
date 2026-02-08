import React, { useState, useEffect } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';

const PedidosCompra = () => {
  const [pedidos, setPedidos] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [modoEdicao, setModoEdicao] = useState(false);
  const [pedidoEditando, setPedidoEditando] = useState(null);
  const [pedidoSelecionado, setPedidoSelecionado] = useState(null);
  const [mostrarRecebimento, setMostrarRecebimento] = useState(false);
  
  // Modal de envio
  const [mostrarModalEnvio, setMostrarModalEnvio] = useState(false);
  const [pedidoParaEnviar, setPedidoParaEnviar] = useState(null);
  const [dadosEnvio, setDadosEnvio] = useState({
    email: '',
    whatsapp: '',
    formatos: {
      pdf: true,
      excel: false
    }
  });

  // 💡 Modal de Sugestão Inteligente
  const [mostrarSugestao, setMostrarSugestao] = useState(false);
  const [sugestoes, setSugestoes] = useState([]);
  const [loadingSugestao, setLoadingSugestao] = useState(false);
  const [periodoSugestao, setPeriodoSugestao] = useState(90);
  const [diasCobertura, setDiasCobertura] = useState(30);
  const [apenasCriticos, setApenasCriticos] = useState(false);
  const [incluirAlerta, setIncluirAlerta] = useState(true);
  const [produtosSelecionados, setProdutosSelecionados] = useState([]);
  const [quantidadesEditadas, setQuantidadesEditadas] = useState({});

  const [formData, setFormData] = useState({
    fornecedor_id: '',
    data_prevista_entrega: '',
    valor_frete: '0',
    valor_desconto: '0',
    observacoes: '',
    itens: []
  });

  const [itemForm, setItemForm] = useState({
    produto_id: '',
    quantidade_pedida: '',
    preco_unitario: ''
  });

  // Estados para inputs digitáveis
  const [fornecedorTexto, setFornecedorTexto] = useState('');
  const [produtoTexto, setProdutoTexto] = useState('');

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    try {
      const [pedidosRes, fornecedoresRes] = await Promise.all([
        api.get('/pedidos-compra/'),
        api.get('/clientes/?tipo_cadastro=fornecedor&apenas_ativos=true')
      ]);

      // Tratar resposta dos pedidos (pode ser array direto ou objeto paginado)
      const pedidosData = Array.isArray(pedidosRes.data) 
        ? pedidosRes.data 
        : (pedidosRes.data.items || pedidosRes.data.pedidos || []);
      
      // Tratar resposta dos fornecedores
      const fornecedoresData = Array.isArray(fornecedoresRes.data) 
        ? fornecedoresRes.data 
        : (fornecedoresRes.data.items || fornecedoresRes.data.clientes || []);

      setPedidos(pedidosData);
      setFornecedores(fornecedoresData);
      // NÃO carregar produtos aqui - apenas quando fornecedor for selecionado
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar dados');
    }
  };

  const carregarProdutosFornecedor = async (fornecedorId) => {
    if (!fornecedorId) {
      setProdutos([]);
      return;
    }
    try {
      const response = await api.get(
        `/produtos/?fornecedor_id=${fornecedorId}`
      );
      
      // API pode retornar array direto ou objeto paginado
      let produtosData;
      if (Array.isArray(response.data)) {
        produtosData = response.data;
      } else if (response.data.items) {
        produtosData = response.data.items;
      } else if (response.data.produtos) {
        produtosData = response.data.produtos;
      } else {
        produtosData = [];
      }
      
      if (produtosData.length === 0) {
        toast.warning('⚠️ Este fornecedor não possui produtos vinculados. Edite os produtos para vincular ao fornecedor.');
      }
      
      setProdutos(produtosData);
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
      toast.error('Erro ao carregar produtos do fornecedor');
    }
  };

  const preencherPreco = (produtoId) => {
    const produto = produtos.find(p => p.id === parseInt(produtoId));
    if (produto) {
      setProdutoTexto(produto.nome);
      if (produto.preco_custo) {
        setItemForm({
          ...itemForm,
          produto_id: produtoId,
          preco_unitario: produto.preco_custo.toFixed(2)
        });
      } else {
        setItemForm({ ...itemForm, produto_id: produtoId });
      }
    }
  };

  const adicionarItem = () => {
    if (!itemForm.produto_id || !itemForm.quantidade_pedida || !itemForm.preco_unitario) {
      toast.error('Preencha todos os campos do item');
      return;
    }

    const produto = produtos.find(p => p.id === parseInt(itemForm.produto_id));
    const quantidade = parseFloat(itemForm.quantidade_pedida);
    const preco = parseFloat(itemForm.preco_unitario);
    const produtoId = parseInt(itemForm.produto_id);

    // Verificar se produto já existe no pedido
    const itemExistenteIndex = formData.itens.findIndex(item => item.produto_id === produtoId);
    
    if (itemExistenteIndex !== -1) {
      // Produto já existe - perguntar ao usuário
      const itemExistente = formData.itens[itemExistenteIndex];
      const confirmar = window.confirm(
        `⚠️ O produto "${produto.nome}" já está no pedido!\n\n` +
        `Quantidade atual: ${itemExistente.quantidade_pedida}\n` +
        `Preço atual: R$ ${itemExistente.preco_unitario.toFixed(2)}\n\n` +
        `Nova quantidade: ${quantidade}\n` +
        `Novo preço: R$ ${preco.toFixed(2)}\n\n` +
        `Deseja SOMAR a quantidade ao item existente?\n\n` +
        `✅ OK = Somar quantidade (${itemExistente.quantidade_pedida} + ${quantidade} = ${itemExistente.quantidade_pedida + quantidade})\n` +
        `❌ CANCELAR = Não adicionar`
      );

      if (confirmar) {
        // Somar quantidade ao item existente
        const novosItens = [...formData.itens];
        novosItens[itemExistenteIndex] = {
          ...itemExistente,
          quantidade_pedida: itemExistente.quantidade_pedida + quantidade,
          preco_unitario: preco, // Atualiza com o novo preço
          total: (itemExistente.quantidade_pedida + quantidade) * preco
        };

        setFormData({
          ...formData,
          itens: novosItens
        });

        toast.success(`✅ Quantidade somada! Total: ${itemExistente.quantidade_pedida + quantidade}`);
      } else {
        toast.info('Adição cancelada');
      }

      // Limpar form
      setProdutoTexto('');
      setItemForm({
        produto_id: '',
        quantidade_pedida: '',
        preco_unitario: ''
      });
      return;
    }

    // Produto novo - adicionar normalmente
    setFormData({
      ...formData,
      itens: [
        ...formData.itens,
        {
          produto_id: produtoId,
          produto_nome: produto.nome,
          quantidade_pedida: quantidade,
          preco_unitario: preco,
          desconto_item: 0,
          total: quantidade * preco
        }
      ]
    });

    // Limpar apenas os campos do item, mantendo o texto do produto limpo
    setProdutoTexto('');
    setItemForm({
      produto_id: '',
      quantidade_pedida: '',
      preco_unitario: ''
    });
  };

  const removerItem = (index) => {
    setFormData({
      ...formData,
      itens: formData.itens.filter((_, i) => i !== index)
    });
  };

  const calcularTotal = () => {
    const subtotal = formData.itens.reduce((sum, item) => sum + item.total, 0);
    const frete = parseFloat(formData.valor_frete || 0);
    const desconto = parseFloat(formData.valor_desconto || 0);
    return subtotal + frete - desconto;
  };

  // 💡 FUNÇÕES DE SUGESTÃO INTELIGENTE
  const buscarSugestoes = async () => {
    if (!formData.fornecedor_id) {
      toast.error('Selecione um fornecedor primeiro');
      return;
    }

    setLoadingSugestao(true);
    try {
      const response = await api.get(
        `/pedidos-compra/sugestao/${formData.fornecedor_id}`,
        {
          params: {
            periodo_dias: periodoSugestao,
            dias_cobertura: diasCobertura,
            apenas_criticos: apenasCriticos,
            incluir_alerta: incluirAlerta
          }
        }
      );

      setSugestoes(response.data.sugestoes || []);
      setProdutosSelecionados([]);
      setQuantidadesEditadas({});

      if (response.data.sugestoes.length === 0) {
        toast.info('Nenhuma sugestão encontrada com os filtros aplicados');
      } else {
        toast.success(`${response.data.sugestoes.length} produtos analisados`);
      }
    } catch (error) {
      console.error('Erro ao buscar sugestões:', error);
      toast.error('Erro ao gerar sugestões');
    } finally {
      setLoadingSugestao(false);
    }
  };

  const toggleSelecionarProduto = (produtoId) => {
    setProdutosSelecionados(prev => 
      prev.includes(produtoId)
        ? prev.filter(id => id !== produtoId)
        : [...prev, produtoId]
    );
  };

  const atualizarQuantidadeSugerida = (produtoId, novaQuantidade) => {
    setQuantidadesEditadas(prev => ({
      ...prev,
      [produtoId]: parseFloat(novaQuantidade) || 0
    }));
  };

  const obterQuantidadeFinal = (sugestao) => {
    return quantidadesEditadas[sugestao.produto_id] !== undefined 
      ? quantidadesEditadas[sugestao.produto_id] 
      : sugestao.quantidade_sugerida;
  };

  const fecharModalSugestao = () => {
    setMostrarSugestao(false);
    setProdutosSelecionados([]);
    setQuantidadesEditadas({});
  };

  const selecionarTodosCriticos = () => {
    const criticos = sugestoes
      .filter(s => s.prioridade === 'CRÍTICO' && s.quantidade_sugerida > 0)
      .map(s => s.produto_id);
    setProdutosSelecionados(criticos);
  };

  const adicionarSugestoesAoPedido = () => {
    if (produtosSelecionados.length === 0) {
      toast.error('Selecione pelo menos um produto');
      return;
    }

    const produtosParaAdicionar = sugestoes.filter(s => 
      produtosSelecionados.includes(s.produto_id)
    );

    const novosItens = produtosParaAdicionar.map(sugestao => {
      const quantidade = obterQuantidadeFinal(sugestao);
      return {
        produto_id: sugestao.produto_id,
        produto_nome: sugestao.produto_nome,
        quantidade_pedida: Math.ceil(quantidade),
        preco_unitario: sugestao.preco_unitario,
        desconto_item: 0,
        total: Math.ceil(quantidade) * sugestao.preco_unitario
      };
    });

    setFormData({
      ...formData,
      itens: [...formData.itens, ...novosItens]
    });

    toast.success(`${novosItens.length} produtos adicionados ao pedido`);
    fecharModalSugestao();
  };


  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.itens.length === 0) {
      toast.error('Adicione pelo menos 1 item ao pedido');
      return;
    }

    setLoading(true);
    try {
      const dadosEnvio = {
        ...formData,
        data_prevista_entrega: formData.data_prevista_entrega ? `${formData.data_prevista_entrega}T12:00:00` : null
      };
      await api.post('/pedidos-compra/', dadosEnvio);

      toast.success('✅ Pedido criado com sucesso!');
      setMostrarForm(false);
      setFormData({
        fornecedor_id: '',
        data_prevista_entrega: '',
        valor_frete: '0',
        valor_desconto: '0',
        observacoes: '',
        itens: []
      });
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao criar pedido');
    } finally {
      setLoading(false);
    }
  };

  const enviarPedido = async (id) => {
    // Abrir modal de envio ao invés de enviar direto
    setPedidoParaEnviar(id);
    setDadosEnvio({
      email: '',
      whatsapp: '',
      formatos: {
        pdf: true,
        excel: false
      }
    });
    setMostrarModalEnvio(true);
  };
  
  const confirmarEnvioPedido = async () => {
    if (!dadosEnvio.email && !dadosEnvio.whatsapp) {
      toast.error('Informe um e-mail ou WhatsApp');
      return;
    }
    
    if (!dadosEnvio.formatos.pdf && !dadosEnvio.formatos.excel) {
      toast.error('Selecione pelo menos um formato (PDF ou Excel)');
      return;
    }
    
    try {
            // Aqui você pode implementar o envio real por e-mail/WhatsApp no futuro
      // Por enquanto, apenas marca como enviado
      await api.post(`/pedidos-compra/${pedidoParaEnviar}/enviar`, {
        email: dadosEnvio.email,
        whatsapp: dadosEnvio.whatsapp,
        formatos: dadosEnvio.formatos
      });
      
      toast.success('✅ Pedido marcado como enviado!');
      setMostrarModalEnvio(false);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao enviar pedido');
    }
  };
  
  const marcarComoEnviadoManualmente = async () => {
    try {
      await api.post(`/pedidos-compra/${pedidoParaEnviar}/enviar`, {
        envio_manual: true
      });
      
      toast.success('✅ Pedido marcado como enviado manualmente!');
      setMostrarModalEnvio(false);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao marcar pedido');
    }
  };

  const confirmarPedido = async (id) => {
    try {
      await api.post(`/pedidos-compra/${id}/confirmar`, {});
      toast.success('✅ Pedido confirmado!');
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao confirmar pedido');
    }
  };

  const exportarPDF = async (id) => {
    try {
      const response = await api.get(
        `/pedidos-compra/${id}/export/pdf`,
        {
          responseType: 'blob'
        }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pedido_${id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('📄 PDF exportado com sucesso!');
    } catch (error) {
      toast.error('Erro ao exportar PDF');
    }
  };

  const exportarExcel = async (id) => {
    try {
      const response = await api.get(
        `/pedidos-compra/${id}/export/excel`,
        {
          responseType: 'blob'
        }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pedido_${id}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('📊 Excel exportado com sucesso!');
    } catch (error) {
      toast.error('Erro ao exportar Excel');
    }
  };

  const verDetalhes = async (pedido) => {
    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      setPedidoSelecionado(response.data);
      setMostrarRecebimento(true);
    } catch (error) {
      toast.error('Erro ao carregar detalhes do pedido');
    }
  };

  const reverterStatus = async (id) => {
    if (!confirm('⚠️ Deseja reverter o status deste pedido para a etapa anterior?')) {
      return;
    }
    try {
      const response = await api.post(
        `/pedidos-compra/${id}/reverter`,
        {}
      );
      toast.success(`⏪ Status revertido: ${response.data.status_anterior} → ${response.data.status_atual}`);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao reverter status');
    }
  };

  const abrirEdicao = async (pedido) => {
    if (pedido.status !== 'rascunho') {
      toast.error('⚠️ Apenas pedidos em rascunho podem ser editados');
      return;
    }

    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      
      const pedidoCompleto = response.data;
      
      setModoEdicao(true);
      setPedidoEditando(pedidoCompleto);
      setFormData({
        fornecedor_id: pedidoCompleto.fornecedor_id?.toString() || '',
        data_prevista_entrega: pedidoCompleto.data_prevista_entrega 
          ? new Date(pedidoCompleto.data_prevista_entrega).toISOString().split('T')[0] 
          : '',
        valor_frete: pedidoCompleto.valor_frete?.toString() || '0',
        valor_desconto: pedidoCompleto.valor_desconto?.toString() || '0',
        observacoes: pedidoCompleto.observacoes || '',
        itens: pedidoCompleto.itens.map(item => ({
          produto_id: item.produto_id,
          produto_nome: item.produto_nome || `Produto ${item.produto_id}`,
          quantidade_pedida: item.quantidade_pedida,
          preco_unitario: item.preco_unitario,
          desconto_item: item.desconto_item || 0,
          total: (item.quantidade_pedida * item.preco_unitario) - (item.desconto_item || 0)
        }))
      });
      
      // Carregar produtos do fornecedor
      if (pedidoCompleto.fornecedor_id) {
        carregarProdutosFornecedor(pedidoCompleto.fornecedor_id);
      }
      
      setMostrarForm(true);
      toast.success('📝 Modo de edição ativado');
    } catch (error) {
      toast.error('Erro ao carregar pedido para edição');
    }
  };

  const editarPedido = async (e) => {
    e.preventDefault();
    
    if (formData.itens.length === 0) {
      toast.error('⚠️ Adicione pelo menos um item ao pedido');
      return;
    }

    try {
      setLoading(true);
      
      const dadosEnvio = {
        ...formData,
        fornecedor_id: parseInt(formData.fornecedor_id),
        valor_frete: parseFloat(formData.valor_frete),
        valor_desconto: parseFloat(formData.valor_desconto),
        data_prevista_entrega: formData.data_prevista_entrega 
          ? `${formData.data_prevista_entrega}T12:00:00` 
          : null,
        itens: formData.itens.map(item => ({
          produto_id: item.produto_id,
          quantidade_pedida: parseFloat(item.quantidade_pedida),
          preco_unitario: parseFloat(item.preco_unitario),
          desconto_item: parseFloat(item.desconto_item || 0)
        }))
      };

      await api.put(
        `/pedidos-compra/${pedidoEditando.id}`, 
        dadosEnvio
      );

      toast.success('✏️ Pedido atualizado com sucesso!');
      setMostrarForm(false);
      setModoEdicao(false);
      setPedidoEditando(null);
      setFormData({
        fornecedor_id: '',
        data_prevista_entrega: '',
        valor_frete: '0',
        valor_desconto: '0',
        observacoes: '',
        itens: []
      });
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar pedido');
    } finally {
      setLoading(false);
    }
  };

  const abrirRecebimento = async (pedido) => {
    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      setPedidoSelecionado(response.data);
      setMostrarRecebimento(true);
    } catch (error) {
      toast.error('Erro ao carregar detalhes do pedido');
    }
  };

  const receberPedido = async (itensRecebimento) => {
    try {
      await api.post(
        `/pedidos-compra/${pedidoSelecionado.id}/receber`,
        { itens: itensRecebimento }
      );
      toast.success('✅ Recebimento processado com sucesso!');
      setMostrarRecebimento(false);
      setPedidoSelecionado(null);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao processar recebimento');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      rascunho: 'bg-gray-200 text-gray-800',
      enviado: 'bg-blue-200 text-blue-800',
      confirmado: 'bg-green-200 text-green-800',
      recebido_parcial: 'bg-yellow-200 text-yellow-800',
      recebido_total: 'bg-green-500 text-white',
      cancelado: 'bg-red-200 text-red-800'
    };
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${styles[status] || 'bg-gray-200'}`}>
        {status.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">🛒 Pedidos de Compra</h1>
          <p className="text-gray-600">Gerencie seus pedidos aos fornecedores</p>
        </div>
        <button
          onClick={() => setMostrarForm(!mostrarForm)}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
        >
          {mostrarForm ? '❌ Cancelar' : '➕ Novo Pedido'}
        </button>
      </div>

      {/* Formulário de Novo/Editar Pedido */}
      {mostrarForm && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">
              {modoEdicao ? '✏️ Editar Pedido' : 'Novo Pedido de Compra'}
            </h2>
            <button
              type="button"
              onClick={() => {
                setMostrarForm(false);
                setModoEdicao(false);
                setPedidoEditando(null);
              }}
              className="text-gray-500 hover:text-gray-700"
            >
              ✖️
            </button>
          </div>
          <form onSubmit={modoEdicao ? editarPedido : handleSubmit} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Fornecedor *
                </label>
                <input
                  list="fornecedores-list"
                  value={fornecedorTexto}
                  onChange={(e) => {
                    const valor = e.target.value;
                    setFornecedorTexto(valor);
                    
                    // Buscar fornecedor que corresponda exatamente
                    const fornecedor = fornecedores.find(f => f.nome === valor);
                    if (fornecedor) {
                      setFormData({ ...formData, fornecedor_id: fornecedor.id.toString(), itens: [] });
                      setItemForm({ produto_id: '', quantidade_pedida: '', preco_unitario: '' });
                      carregarProdutosFornecedor(fornecedor.id);
                    } else {
                      setFormData({ ...formData, fornecedor_id: '', itens: [] });
                      setProdutos([]);
                    }
                  }}
                  placeholder="Digite ou selecione o fornecedor"
                  required={!!formData.fornecedor_id}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <datalist id="fornecedores-list">
                  {fornecedores.map(f => (
                    <option key={f.id} value={f.nome}>
                      {f.cpf_cnpj ? `- ${f.cpf_cnpj}` : ''}
                    </option>
                  ))}
                </datalist>
                <p className="text-xs text-gray-500 mt-1">Digite ou selecione um fornecedor para carregar seus produtos</p>
                {formData.fornecedor_id && (
                  <button
                    type="button"
                    onClick={() => {
                      setMostrarSugestao(true);
                      buscarSugestoes();
                    }}
                    className="mt-2 w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2"
                  >
                    💡 Sugestão Inteligente de Pedido
                  </button>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Data Prevista Entrega
                </label>
                <input
                  type="date"
                  value={formData.data_prevista_entrega}
                  onChange={(e) => setFormData({ ...formData, data_prevista_entrega: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Adicionar Itens */}
            <div className="border-t pt-4">
              <h3 className="font-semibold mb-4">Itens do Pedido</h3>
              <div className="grid grid-cols-4 gap-4 mb-4">
                <input
                  list="produtos-list"
                  value={produtoTexto}
                  onChange={(e) => {
                    const valor = e.target.value;
                    setProdutoTexto(valor);
                    
                    // Buscar produto que corresponda exatamente
                    const produto = produtos.find(p => p.nome === valor);
                    if (produto) {
                      preencherPreco(produto.id.toString());
                    } else {
                      setItemForm({ ...itemForm, produto_id: '' });
                    }
                  }}
                  placeholder={!formData.fornecedor_id ? 'Selecione um fornecedor primeiro' : 'Digite ou selecione o produto'}
                  disabled={!formData.fornecedor_id}
                  className="col-span-2 px-4 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100 focus:ring-2 focus:ring-blue-500"
                />
                <datalist id="produtos-list">
                  {produtos.map(p => (
                    <option key={p.id} value={p.nome}>
                      {`SKU: ${p.sku || p.codigo || 'N/A'} | Barras: ${p.codigo_barras || 'N/A'} | Estoque: ${p.estoque_atual || 0}`}
                    </option>
                  ))}
                </datalist>
                <input
                  type="number"
                  step="0.01"
                  placeholder="Quantidade"
                  value={itemForm.quantidade_pedida}
                  onChange={(e) => setItemForm({ ...itemForm, quantidade_pedida: e.target.value })}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                />
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Preço"
                    value={itemForm.preco_unitario}
                    onChange={(e) => setItemForm({ ...itemForm, preco_unitario: e.target.value })}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
                  />
                  <button
                    type="button"
                    onClick={adicionarItem}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                  >
                    ➕
                  </button>
                </div>
              </div>

              {/* Lista de Itens */}
              {formData.itens.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Produto</th>
                        <th className="px-4 py-2 text-right text-sm font-semibold">Qtd</th>
                        <th className="px-4 py-2 text-right text-sm font-semibold">Preço</th>
                        <th className="px-4 py-2 text-right text-sm font-semibold">Total</th>
                        <th className="px-4 py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {formData.itens.map((item, index) => (
                        <tr key={index} className="border-t">
                          <td className="px-4 py-2">{item.produto_nome}</td>
                          <td className="px-4 py-2 text-right">{item.quantidade_pedida}</td>
                          <td className="px-4 py-2 text-right">R$ {item.preco_unitario.toFixed(2)}</td>
                          <td className="px-4 py-2 text-right font-semibold">R$ {item.total.toFixed(2)}</td>
                          <td className="px-4 py-2 text-right">
                            <button
                              type="button"
                              onClick={() => removerItem(index)}
                              className="text-red-600 hover:text-red-800"
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

            {/* Totais */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Frete (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.valor_frete}
                  onChange={(e) => setFormData({ ...formData, valor_frete: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Desconto (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.valor_desconto}
                  onChange={(e) => setFormData({ ...formData, valor_desconto: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Total</label>
                <div className="text-2xl font-bold text-green-600">
                  R$ {calcularTotal().toFixed(2)}
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading 
                ? '⏳ Processando...' 
                : modoEdicao 
                  ? '✏️ Salvar Alterações' 
                  : '✅ Criar Pedido'
              }
            </button>
          </form>
        </div>
      )}

      {/* Lista de Pedidos */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold">Número</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Fornecedor</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Data</th>
              <th className="px-4 py-3 text-right text-sm font-semibold">Valor</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Status</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody>
            {pedidos.map(pedido => (
              <tr 
                key={pedido.id} 
                className={`border-t hover:bg-gray-50 ${
                  pedido.status === 'rascunho' ? 'cursor-pointer' : ''
                }`}
                onClick={() => pedido.status === 'rascunho' && abrirEdicao(pedido)}
                title={pedido.status === 'rascunho' ? 'Clique para editar' : ''}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {pedido.numero_pedido}
                    {pedido.foi_alterado_apos_envio && (
                      <span className="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded font-semibold" title="Este pedido foi alterado após o envio">
                        ⚠️ Alterado
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">{pedido.fornecedor_id}</td>
                <td className="px-4 py-3">{new Date(pedido.data_pedido).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-right font-semibold">R$ {pedido.valor_final.toFixed(2)}</td>
                <td className="px-4 py-3 text-center">{getStatusBadge(pedido.status)}</td>
                <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                  <div className="flex justify-center gap-2">
                    {/* Botão Ver Detalhes */}
                    <button
                      onClick={() => verDetalhes(pedido)}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-xs font-semibold"
                      title="Ver detalhes completos do pedido"
                    >
                      🔍 Ver
                    </button>

                    {/* Botões de exportação - sempre disponíveis */}
                    <button
                      onClick={() => exportarPDF(pedido.id)}
                      className="px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-xs font-semibold"
                      title="Exportar PDF"
                    >
                      📄 PDF
                    </button>
                    <button
                      onClick={() => exportarExcel(pedido.id)}
                      className="px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-xs font-semibold"
                      title="Exportar Excel"
                    >
                      📊 Excel
                    </button>
                    
                    {/* Ações por status */}
                    {pedido.status === 'rascunho' && (
                      <button
                        onClick={() => enviarPedido(pedido.id)}
                        className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs font-semibold"
                        title="Enviar pedido ao fornecedor"
                      >
                        📤 Enviar
                      </button>
                    )}
                    {pedido.status === 'enviado' && (
                      <button
                        onClick={() => confirmarPedido(pedido.id)}
                        className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-xs font-semibold"
                        title="Confirmar recebimento do pedido pelo fornecedor"
                      >
                        ✅ Confirmar
                      </button>
                    )}
                    {(pedido.status === 'confirmado' || pedido.status === 'recebido_parcial') && (
                      <button
                        onClick={() => abrirRecebimento(pedido)}
                        className="px-3 py-1 bg-purple-600 text-white rounded hover:bg-purple-700 text-xs font-semibold"
                        title="Registrar entrada de produtos no estoque"
                      >
                        📦 Receber
                      </button>
                    )}

                    {/* Botão Reverter - exceto para rascunho */}
                    {pedido.status !== 'rascunho' && pedido.status !== 'recebido_total' && (
                      <button
                        onClick={() => reverterStatus(pedido.id)}
                        className="px-2 py-1 bg-orange-100 text-orange-700 rounded hover:bg-orange-200 text-xs font-semibold"
                        title="Reverter para status anterior"
                      >
                        ⏪ Reverter
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal de Recebimento */}
      {mostrarRecebimento && pedidoSelecionado && (
        <ModalRecebimento
          pedido={pedidoSelecionado}
          onClose={() => {
            setMostrarRecebimento(false);
            setPedidoSelecionado(null);
          }}
          onReceber={receberPedido}
        />
      )}
      
      {/* Modal de Envio */}
      {mostrarModalEnvio && (
        <ModalEnvioPedido
          pedidoId={pedidoParaEnviar}
          onClose={() => setMostrarModalEnvio(false)}
          onEnviar={confirmarEnvioPedido}
          onEnvioManual={marcarComoEnviadoManualmente}
          dadosEnvio={dadosEnvio}
          setDadosEnvio={setDadosEnvio}
        />
      )}

      {/* 💡 MODAL DE SUGESTÃO INTELIGENTE */}
      {mostrarSugestao && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold mb-2">💡 Sugestão Inteligente de Pedido</h2>
                  <p className="text-purple-100">Análise baseada em vendas e estoque atual</p>
                </div>
                <button
                  onClick={fecharModalSugestao}
                  className="text-white hover:bg-white hover:bg-opacity-20 rounded-lg p-2"
                >
                  ✖️
                </button>
              </div>

              {/* Filtros */}
              <div className="mt-4 grid grid-cols-5 gap-4">
                <div>
                  <label className="block text-sm text-purple-100 mb-1">Período de Análise</label>
                  <select
                    value={periodoSugestao}
                    onChange={(e) => setPeriodoSugestao(parseInt(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg text-gray-800 focus:ring-2 focus:ring-purple-300"
                  >
                    <option value={30}>Últimos 30 dias</option>
                    <option value={60}>Últimos 60 dias</option>
                    <option value={90}>Últimos 90 dias</option>
                    <option value={180}>Últimos 180 dias</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-purple-100 mb-1">Cobertura de Estoque</label>
                  <select
                    value={diasCobertura}
                    onChange={(e) => setDiasCobertura(parseInt(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg text-gray-800 focus:ring-2 focus:ring-purple-300"
                  >
                    <option value={15}>15 dias</option>
                    <option value={30}>30 dias</option>
                    <option value={45}>45 dias</option>
                    <option value={60}>60 dias</option>
                    <option value={90}>90 dias</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-white cursor-pointer">
                    <input
                      type="checkbox"
                      checked={apenasCriticos}
                      onChange={(e) => setApenasCriticos(e.target.checked)}
                      className="w-4 h-4 rounded"
                    />
                    <span>Apenas Críticos</span>
                  </label>
                </div>

                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-white cursor-pointer">
                    <input
                      type="checkbox"
                      checked={incluirAlerta}
                      onChange={(e) => setIncluirAlerta(e.target.checked)}
                      className="w-4 h-4 rounded"
                    />
                    <span>Incluir Alertas</span>
                  </label>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={buscarSugestoes}
                    disabled={loadingSugestao}
                    className="w-full bg-white text-purple-600 px-4 py-2 rounded-lg font-semibold hover:bg-purple-50 disabled:opacity-50"
                  >
                    {loadingSugestao ? '🔄 Analisando...' : '🔍 Atualizar'}
                  </button>
                </div>
              </div>
            </div>

            {/* Tabela de Sugestões */}
            <div className="flex-1 overflow-auto p-6">
              {loadingSugestao ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Analisando produtos e calculando sugestões...</p>
                  </div>
                </div>
              ) : sugestoes.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500 text-lg">Nenhuma sugestão encontrada com os filtros aplicados</p>
                  <p className="text-gray-400 text-sm mt-2">Tente ajustar os filtros acima</p>
                </div>
              ) : (
                <>
                  {/* Ações Rápidas */}
                  <div className="mb-4 flex gap-3">
                    <button
                      onClick={selecionarTodosCriticos}
                      className="bg-red-100 text-red-700 px-4 py-2 rounded-lg font-semibold hover:bg-red-200"
                    >
                      🔴 Selecionar Todos Críticos
                    </button>
                    <div className="flex-1"></div>
                    <span className="text-gray-600">
                      {produtosSelecionados.length} de {sugestoes.length} produtos selecionados
                    </span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                            <input
                              type="checkbox"
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setProdutosSelecionados(sugestoes.map(s => s.produto_id));
                                } else {
                                  setProdutosSelecionados([]);
                                }
                              }}
                              checked={produtosSelecionados.length === sugestoes.length}
                              className="w-4 h-4 rounded"
                            />
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Prioridade</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Produto</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Estoque</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Consumo/dia</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Dias Restantes</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Qtd Sugerida</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Preço Unit.</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Total</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Tendência</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {sugestoes.map((sugestao) => (
                          <tr
                            key={sugestao.produto_id}
                            className={`hover:bg-gray-50 ${
                              produtosSelecionados.includes(sugestao.produto_id) ? 'bg-purple-50' : ''
                            }`}
                          >
                            <td className="px-4 py-3">
                              <input
                                type="checkbox"
                                checked={produtosSelecionados.includes(sugestao.produto_id)}
                                onChange={() => toggleSelecionarProduto(sugestao.produto_id)}
                                className="w-4 h-4 rounded"
                              />
                            </td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                sugestao.prioridade === 'CRÍTICO' ? 'bg-red-100 text-red-700' :
                                sugestao.prioridade === 'ALERTA' ? 'bg-yellow-100 text-yellow-700' :
                                sugestao.prioridade === 'ATENÇÃO' ? 'bg-orange-100 text-orange-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {sugestao.prioridade}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <div>
                                <div className="font-medium text-gray-900">{sugestao.produto_nome}</div>
                                <div className="text-xs text-gray-500">
                                  SKU: {sugestao.produto_sku || 'N/A'} | 
                                  Barras: {sugestao.produto_codigo_barras || 'N/A'}
                                </div>
                                {sugestao.observacao && (
                                  <div className="text-xs text-gray-600 mt-1 italic">{sugestao.observacao}</div>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <div className="font-medium">{sugestao.estoque_atual}</div>
                              <div className="text-xs text-gray-500">Mín: {sugestao.estoque_minimo}</div>
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {sugestao.consumo_diario.toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className={`font-semibold ${
                                sugestao.dias_estoque && sugestao.dias_estoque < 7 ? 'text-red-600' :
                                sugestao.dias_estoque && sugestao.dias_estoque < 14 ? 'text-yellow-600' :
                                'text-green-600'
                              }`}>
                                {sugestao.dias_estoque ? `${sugestao.dias_estoque} dias` : '∞'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <input
                                type="number"
                                min="0"
                                step="1"
                                value={Math.ceil(obterQuantidadeFinal(sugestao))}
                                onChange={(e) => atualizarQuantidadeSugerida(sugestao.produto_id, e.target.value)}
                                className="w-20 px-2 py-1 text-right font-bold text-purple-600 border rounded focus:ring-2 focus:ring-purple-300"
                              />
                            </td>
                            <td className="px-4 py-3 text-right">
                              R$ {sugestao.preco_unitario.toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-right font-semibold">
                              R$ {(obterQuantidadeFinal(sugestao) * sugestao.preco_unitario).toFixed(2)}
                            </td>
                            <td className="px-4 py-3">
                              <span className={`text-xs ${
                                sugestao.tendencia === 'CRESCIMENTO' ? 'text-green-600' :
                                sugestao.tendencia === 'QUEDA' ? 'text-red-600' :
                                'text-gray-600'
                              }`}>
                                {sugestao.tendencia === 'CRESCIMENTO' ? '📈' :
                                 sugestao.tendencia === 'QUEDA' ? '📉' :
                                 sugestao.tendencia === 'ESTÁVEL' ? '➡️' : '—'}
                                {sugestao.tendencia}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>

            {/* Footer com Ações */}
            {!loadingSugestao && sugestoes.length > 0 && (
              <div className="border-t p-6 bg-gray-50">
                <div className="flex justify-between items-center">
                  <div className="text-sm text-gray-600">
                    <div className="font-semibold mb-1">Resumo da Sugestão:</div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        🔴 <strong>{sugestoes.filter(s => s.prioridade === 'CRÍTICO').length}</strong> críticos
                      </div>
                      <div>
                        ⚠️ <strong>{sugestoes.filter(s => s.prioridade === 'ALERTA').length}</strong> em alerta
                      </div>
                      <div>
                        💰 Total: <strong>R$ {sugestoes
                          .filter(s => produtosSelecionados.includes(s.produto_id))
                          .reduce((sum, s) => sum + (obterQuantidadeFinal(s) * s.preco_unitario), 0)
                          .toFixed(2)}</strong>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={fecharModalSugestao}
                      className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-100"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={adicionarSugestoesAoPedido}
                      disabled={produtosSelecionados.length === 0}
                      className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      ✅ Adicionar {produtosSelecionados.length} Produtos ao Pedido
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Modal de Recebimento
const ModalRecebimento = ({ pedido, onClose, onReceber }) => {
  const [itensRecebimento, setItensRecebimento] = useState(
    pedido.itens.map(item => ({
      item_id: item.id,
      quantidade_recebida: item.quantidade_pedida - item.quantidade_recebida,
      max: item.quantidade_pedida - item.quantidade_recebida
    }))
  );

  const handleReceber = () => {
    const itens = itensRecebimento
      .filter(i => i.quantidade_recebida > 0)
      .map(i => ({
        item_id: i.item_id,
        quantidade_recebida: parseFloat(i.quantidade_recebida)
      }));

    if (itens.length === 0) {
      toast.error('Informe a quantidade recebida de pelo menos 1 item');
      return;
    }

    onReceber(itens);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">📦 Receber Pedido {pedido.numero_pedido}</h2>
        
        <div className="space-y-4">
          {pedido.itens.map((item, index) => (
            <div key={item.id} className="border rounded-lg p-4">
              <div className="font-semibold mb-2">{item.produto_nome}</div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Pedido:</span>
                  <span className="ml-2 font-semibold">{item.quantidade_pedida}</span>
                </div>
                <div>
                  <span className="text-gray-600">Já Recebido:</span>
                  <span className="ml-2 font-semibold">{item.quantidade_recebida}</span>
                </div>
                <div>
                  <span className="text-gray-600">Pendente:</span>
                  <span className="ml-2 font-semibold text-orange-600">
                    {item.quantidade_pedida - item.quantidade_recebida}
                  </span>
                </div>
              </div>
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantidade a Receber
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max={itensRecebimento[index].max}
                  value={itensRecebimento[index].quantidade_recebida}
                  onChange={(e) => {
                    const novoValor = parseFloat(e.target.value) || 0;
                    const novaLista = [...itensRecebimento];
                    novaLista[index].quantidade_recebida = Math.min(novoValor, novaLista[index].max);
                    setItensRecebimento(novaLista);
                  }}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="flex gap-4 mt-6">
          <button
            onClick={handleReceber}
            className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700"
          >
            ✅ Confirmar Recebimento
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
          >
            ❌ Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

// Modal de Envio de Pedido
const ModalEnvioPedido = ({ pedidoId, onClose, onEnviar, onEnvioManual, dadosEnvio, setDadosEnvio }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-800">📤 Enviar Pedido ao Fornecedor</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Campo E-mail */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              E-mail do Fornecedor
            </label>
            <input
              type="email"
              value={dadosEnvio.email}
              onChange={(e) => setDadosEnvio({ ...dadosEnvio, email: e.target.value })}
              placeholder="fornecedor@exemplo.com"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Campo WhatsApp */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              WhatsApp (futuro)
              <span className="ml-2 text-xs text-gray-500">(Em breve)</span>
            </label>
            <input
              type="tel"
              value={dadosEnvio.whatsapp}
              onChange={(e) => setDadosEnvio({ ...dadosEnvio, whatsapp: e.target.value })}
              placeholder="(00) 00000-0000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
              disabled
            />
          </div>

          {/* Seleção de Formatos */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Formatos para Envio
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={dadosEnvio.formatos.pdf}
                  onChange={(e) => setDadosEnvio({
                    ...dadosEnvio,
                    formatos: { ...dadosEnvio.formatos, pdf: e.target.checked }
                  })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm">📄 PDF</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={dadosEnvio.formatos.excel}
                  onChange={(e) => setDadosEnvio({
                    ...dadosEnvio,
                    formatos: { ...dadosEnvio.formatos, excel: e.target.checked }
                  })}
                  className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <span className="ml-2 text-sm">📊 Excel</span>
              </label>
            </div>
          </div>

          {/* Botões de Ação */}
          <div className="flex flex-col gap-3 pt-4">
            <button
              onClick={onEnviar}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              📧 Enviar por E-mail
            </button>
            
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">ou</span>
              </div>
            </div>

            <button
              onClick={onEnvioManual}
              className="w-full bg-gray-600 text-white py-3 rounded-lg font-semibold hover:bg-gray-700 transition-colors"
            >
              ✅ Já enviei manualmente
            </button>

            <button
              onClick={onClose}
              className="w-full border border-gray-300 text-gray-700 py-2 rounded-lg font-semibold hover:bg-gray-50"
            >
              ❌ Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PedidosCompra;
