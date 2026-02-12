/**
 * Página de Movimentações de Estoque por Produto
 * Modelo inspirado no Bling
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import toast from 'react-hot-toast';

export default function MovimentacoesProduto() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [produto, setProduto] = useState(null);
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [editingMovimentacao, setEditingMovimentacao] = useState(null);
  
  // Modal de lançamento
  const [tipoLancamento, setTipoLancamento] = useState('entrada'); // entrada, saida, balanco
  const [formData, setFormData] = useState({
    quantidade: '',
    custo_unitario: '',
    observacao: '',
    lote: '',
    data_validade: '',
    data_fabricacao: ''
  });

  useEffect(() => {
    carregarDados();
  }, [id]);

  const carregarDados = async () => {
    try {
      setLoading(true);
            console.log('Carregando produto ID:', id);
      
      // Carregar produto
      const produtoRes = await api.get(`http://127.0.0.1:8000/produtos/${id}`);
      console.log('Produto carregado:', produtoRes.data);
      setProduto(produtoRes.data);
      
      // Carregar movimentações
      const movRes = await api.get(`http://127.0.0.1:8000/estoque/movimentacoes/produto/${id}`);
      console.log('Movimentações carregadas:', movRes.data);
      setMovimentacoes(movRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      console.error('Detalhes do erro:', error.response?.data);
      toast.error(error.response?.data?.detail || 'Erro ao carregar dados do produto');
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (tipo, movimentacao = null) => {
    // ========== VALIDAÇÃO: KIT VIRTUAL não permite movimentação manual ==========
    if (produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'VIRTUAL' && !movimentacao) {
      toast.error(
        `❌ KIT VIRTUAL não permite movimentação manual de estoque.\n\n` +
        `O estoque deste kit é calculado automaticamente com base nos componentes.\n\n` +
        `Para alterar o estoque, movimente os produtos componentes individualmente.`,
        { duration: 6000 }
      );
      return;
    }
    
    setTipoLancamento(tipo);
    setEditingMovimentacao(movimentacao);
    
    if (movimentacao) {
      // Modo edição
      setFormData({
        quantidade: movimentacao.quantidade?.toString() || '',
        custo_unitario: movimentacao.custo_unitario?.toString() || '',
        observacao: movimentacao.observacao || '',
        lote: movimentacao.lote_id || '',
        data_validade: '',
        data_fabricacao: ''
      });
    } else {
      // Modo novo
      setFormData({
        quantidade: '',
        custo_unitario: tipo === 'entrada' ? (produto?.preco_custo || '') : '',
        observacao: '',
        lote: '',
        data_validade: '',
        data_fabricacao: '',
        retornar_componentes: false  // Padrão: não retornar componentes
      });
    }
    setShowModal(true);
  };

  const handleSelectAll = () => {
    if (selectedIds.length === movimentacoes.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(movimentacoes.map(m => m.id));
    }
  };

  const handleSelectOne = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(sid => sid !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleDelete = async () => {
    if (selectedIds.length === 0) {
      toast.error('Selecione pelo menos um lançamento');
      return;
    }

    if (!confirm(`Deseja realmente excluir ${selectedIds.length} lançamento(s)?`)) {
      return;
    }

    try {
            const responses = await Promise.all(
        selectedIds.map(id => 
          api.delete(`http://127.0.0.1:8000/estoque/movimentacoes/${id}`)
        )
      );

      // Verificar se algum teve componentes estornados
      const componentesEstornados = responses.flatMap(r => r.data.componentes_estornados || []);
      
      if (componentesEstornados.length > 0) {
        toast.success(
          `${selectedIds.length} lançamento(s) excluído(s)!\n✅ ${componentesEstornados.length} componente(s) estornado(s)`,
          { duration: 5000 }
        );
      } else {
        toast.success(`${selectedIds.length} lançamento(s) excluído(s)`);
      }
      
      setSelectedIds([]);
      carregarDados();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      toast.error(error.response?.data?.detail || 'Erro ao excluir lançamentos');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
            // Se está editando, usar endpoint PATCH
      if (editingMovimentacao) {
        const payload = {
          quantidade: parseFloat(formData.quantidade),
          custo_unitario: formData.custo_unitario ? parseFloat(formData.custo_unitario) : null,
          observacao: formData.observacao || null,
        };

        await api.patch(
          `http://127.0.0.1:8000/estoque/movimentacoes/${editingMovimentacao.id}`,
          payload
        );

        toast.success('Lançamento atualizado com sucesso!');
        setShowModal(false);
        setEditingMovimentacao(null);
        carregarDados();
        return;
      }
      
      // Criando novo lançamento
      let endpoint = '/estoque/';
      let payload = {
        produto_id: parseInt(id),
        quantidade: parseFloat(formData.quantidade),
        custo_unitario: formData.custo_unitario ? parseFloat(formData.custo_unitario) : null,
        observacao: formData.observacao || null,
      };

      // Configurar endpoint e payload conforme tipo
      if (tipoLancamento === 'entrada') {
        endpoint += 'entrada';
        payload.tipo = 'entrada';
        payload.motivo = 'compra';
        payload.numero_lote = formData.lote || null;
        payload.data_validade = formData.data_validade || null;
        payload.data_fabricacao = formData.data_fabricacao || null;
      } else if (tipoLancamento === 'saida') {
        endpoint += 'saida';
        payload.tipo = 'saida';
        payload.motivo = 'saida_manual';
        payload.numero_lote = formData.lote || null;
        payload.data_validade = formData.data_validade || null;
        // Adicionar campo retornar_componentes para KIT FÍSICO
        if (produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'FISICO') {
          payload.retornar_componentes = formData.retornar_componentes === true;
        }
      } else if (tipoLancamento === 'balanco') {
        // Balanço: definir estoque para o valor exato
        const novaQuantidade = parseFloat(formData.quantidade);
        const estoqueAtual = produto?.estoque_atual || 0;
        const diferenca = novaQuantidade - estoqueAtual;
        
        endpoint += diferenca >= 0 ? 'entrada' : 'saida';
        payload.tipo = diferenca >= 0 ? 'entrada' : 'saida';
        payload.quantidade = Math.abs(diferenca);
        payload.motivo = 'balanco';
      }

      const response = await api.post(endpoint, payload);

      console.log('Response da entrada:', response.data);

      // Mostrar indicador de variação de preço se for entrada
      if (tipoLancamento === 'entrada' && response.data) {
        const { custo_anterior, custo_unitario, variacao_preco } = response.data;
        
        if (variacao_preco && custo_anterior !== null && custo_anterior !== undefined) {
          let mensagem = 'Lançamento registrado!';
          
          if (variacao_preco === 'aumento') {
            mensagem += ` ⬆️ Custo aumentou de R$ ${custo_anterior?.toFixed(2)} para R$ ${custo_unitario?.toFixed(2)}`;
            toast.error(mensagem, { duration: 5000 });
          } else if (variacao_preco === 'reducao') {
            mensagem += ` ⬇️ Custo reduziu de R$ ${custo_anterior?.toFixed(2)} para R$ ${custo_unitario?.toFixed(2)}`;
            toast.success(mensagem, { duration: 5000 });
          } else if (variacao_preco === 'estavel') {
            mensagem += ` Custo mantido em R$ ${custo_unitario?.toFixed(2)}`;
            toast(mensagem, { icon: '➖', duration: 3000 });
          }
        } else if (custo_unitario) {
          // Primeira entrada
          toast.success(`Lançamento registrado! Custo: R$ ${custo_unitario?.toFixed(2)}`, { duration: 3000 });
        } else {
          toast.success('Lançamento registrado com sucesso!');
        }
      } else {
        // Mostrar mensagem sobre componentes sensibilizados se houver
        if (response.data?.componentes_sensibilizados && response.data.componentes_sensibilizados.length > 0) {
          const qtdComponentes = response.data.componentes_sensibilizados.length;
          toast.success(
            `Lançamento registrado com sucesso!\n✅ ${qtdComponentes} componente(s) sensibilizado(s)`,
            { duration: 4000 }
          );
        } else {
          toast.success('Lançamento registrado com sucesso!');
        }
      }

      setShowModal(false);
      carregarDados();
    } catch (error) {
      console.error('Erro ao registrar lançamento:', error);
      toast.error(error.response?.data?.detail || 'Erro ao registrar lançamento');
    }
  };

  const formatarData = (data) => {
    if (!data) return '-';
    // Converter para horário de Brasília (UTC-3)
    const dataUTC = new Date(data);
    const dataBrasilia = new Date(dataUTC.getTime() - (3 * 60 * 60 * 1000));
    return dataBrasilia.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'America/Sao_Paulo'
    });
  };

  const getTipoLabel = (tipo) => {
    const labels = {
      entrada: 'Entrada',
      saida: 'Saída',
      ajuste: 'Ajuste',
      transferencia: 'Transferência'
    };
    return labels[tipo] || tipo;
  };

  const getMotivoLabel = (motivo) => {
    const labels = {
      compra: 'Compra',
      venda: 'Venda',
      venda_online: 'Venda Online',
      ajuste: 'Ajuste',
      saida_manual: 'Saída Manual',
      devolucao: 'Devolução',
      perda: 'Perda',
      transferencia: 'Transferência',
      balanco: 'Balanço'
    };
    return labels[motivo] || motivo;
  };

  const getOrigem = (mov) => {
    // Se for venda
    if (mov.referencia_tipo === 'venda') {
      // Verificar se tem NF (documento com padrão de chave NFe ou número NF)
      if (mov.documento && (mov.documento.length === 44 || mov.documento.startsWith('NF'))) {
        return { texto: `NF ${mov.documento}`, icone: 'nf-venda', cor: 'text-red-600' };
      }
      // Senão, é apenas pedido
      return { texto: `Pedido #${mov.referencia_id}`, icone: 'pedido', cor: 'text-orange-600' };
    }
    // Se for balanço
    if (mov.motivo === 'balanco') {
      return { texto: 'Balanço', icone: 'balanco', cor: 'text-blue-600' };
    }
    // Se for SAÍDA Manual - vermelho
    if (mov.tipo === 'saida') {
      return { texto: 'Saída Manual', icone: 'manual', cor: 'text-red-600' };
    }
    // Se for entrada por XML (chave NFe com 44 dígitos)
    if (mov.tipo === 'entrada' && mov.documento && mov.documento.length === 44) {
      return { texto: `NF ${mov.documento.substring(25, 34)}`, icone: 'nf-entrada', cor: 'text-green-600' };
    }
    // Se for entrada manual com documento
    if (mov.tipo === 'entrada' && mov.documento) {
      return { texto: `Doc ${mov.documento}`, icone: 'documento', cor: 'text-blue-600' };
    }
    // Entrada manual sem documento - verde
    if (mov.tipo === 'entrada') {
      return { texto: 'Entrada Manual', icone: 'manual', cor: 'text-green-600' };
    }
    return { texto: 'Manual', icone: 'manual', cor: 'text-gray-500' };
  };

  // Calcular totalizadores
  const totalEntradas = movimentacoes
    .filter(m => m.tipo === 'entrada')
    .reduce((sum, m) => sum + parseFloat(m.quantidade || 0), 0);
  
  const totalSaidas = movimentacoes
    .filter(m => m.tipo === 'saida')
    .reduce((sum, m) => sum + parseFloat(m.quantidade || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Carregando...</div>
      </div>
    );
  }

  if (!produto) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Produto não encontrado</div>
      </div>
    );
  }

  const estoqueAtual = produto.estoque_atual || 0;
  const estoqueMinimo = produto.estoque_minimo || 0;
  const corEstoque = estoqueAtual > estoqueMinimo ? 'text-green-600' : 
                     estoqueAtual === 0 ? 'text-red-600' : 'text-yellow-600';

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Aviso para KIT VIRTUAL */}
      {produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'VIRTUAL' && (
        <div className="mb-6 bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-indigo-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="font-semibold text-indigo-900 mb-1">
                🧩 KIT VIRTUAL - Estoque Calculado Automaticamente
              </h3>
              <p className="text-sm text-indigo-800">
                Este é um produto do tipo <strong>KIT VIRTUAL</strong>. O estoque é calculado automaticamente com base nos componentes que o compõem.
                <br />
                <strong>Não é possível movimentar o estoque do kit diretamente.</strong> Para alterar o estoque, movimente os produtos componentes individualmente.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Aviso para KIT FÍSICO */}
      {produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'FISICO' && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="font-semibold text-green-900 mb-1">
                📦 KIT FÍSICO - Estoque Próprio com Sensibilização
              </h3>
              <p className="text-sm text-green-800">
                Este é um produto do tipo <strong>KIT FÍSICO</strong>. Possui estoque próprio e independente.
                <br />
                <strong>Importante:</strong> Ao movimentar o estoque do kit, os estoques dos componentes também serão automaticamente sensibilizados na mesma proporção.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Header com informações do produto */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            {/* Indicador de estoque */}
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
              estoqueAtual > estoqueMinimo ? 'bg-green-100' : 
              estoqueAtual === 0 ? 'bg-red-100' : 'bg-yellow-100'
            }`}>
              <svg className={`w-6 h-6 ${corEstoque}`} fill="currentColor" viewBox="0 0 20 20">
                <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </div>
            
            <div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate('/produtos')}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <h1 className="text-2xl font-bold text-gray-900">{produto.nome}</h1>
              </div>
              <div className="mt-2 text-sm text-gray-600 space-y-1">
                <div>Código: <span className="font-mono">{produto.codigo || produto.sku}</span></div>
                {produto.codigo_barras && (
                  <div>EAN: <span className="font-mono">{produto.codigo_barras}</span></div>
                )}
              </div>
            </div>
          </div>

          {/* Totalizadores */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-200">
            <div className="bg-green-50 rounded-lg p-3">
              <div className="text-xs text-green-600 font-medium mb-1">Total Entradas</div>
              <div className="text-2xl font-bold text-green-700">{totalEntradas.toFixed(2)}</div>
            </div>
            <div className="bg-red-50 rounded-lg p-3">
              <div className="text-xs text-red-600 font-medium mb-1">Total Saídas</div>
              <div className="text-2xl font-bold text-red-700">{totalSaidas.toFixed(2)}</div>
            </div>
            <div className={`rounded-lg p-3 ${
              estoqueAtual > estoqueMinimo ? 'bg-blue-50' : 
              estoqueAtual === 0 ? 'bg-red-50' : 'bg-yellow-50'
            }`}>
              <div className={`text-xs font-medium mb-1 ${
                estoqueAtual > estoqueMinimo ? 'text-blue-600' : 
                estoqueAtual === 0 ? 'text-red-600' : 'text-yellow-600'
              }`}>Saldo Atual</div>
              <div className={`text-2xl font-bold ${
                estoqueAtual > estoqueMinimo ? 'text-blue-700' : 
                estoqueAtual === 0 ? 'text-red-700' : 'text-yellow-700'
              }`}>{estoqueAtual.toFixed(2)} {produto.unidade || 'UN'}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-600 font-medium mb-1">Estoque Mín/Máx</div>
              <div className="text-lg font-bold text-gray-700">
                {estoqueMinimo.toFixed(0)} / {(produto.estoque_maximo || 0).toFixed(0)}
              </div>
            </div>
          </div>

          {/* Botão Incluir Lançamento */}
          <div className="relative group">
            <button
              onClick={() => {
                if (produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'VIRTUAL') {
                  toast.error(
                    'KIT VIRTUAL não permite movimentação manual.\n\n' +
                    'Movimente os componentes individualmente.',
                    { duration: 4000 }
                  );
                } else {
                  setShowModal(true);
                }
              }}
              disabled={produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'VIRTUAL'}
              className={`px-6 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'VIRTUAL'
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Incluir lançamento
            </button>
          </div>
        </div>
      </div>

      {/* Tabela de movimentações */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">Lançamentos</h2>
          
          {selectedIds.length > 0 && (
            <button
              onClick={handleDelete}
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Excluir ({selectedIds.length})
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 w-12">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === movimentacoes.length && movimentacoes.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data e Hora
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Entrada
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Saída
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Preço Venda
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Preço Compra
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Lote
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Origem
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Observação
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {movimentacoes.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-6 py-8 text-center text-gray-500">
                    Nenhuma movimentação registrada
                  </td>
                </tr>
              ) : (
                movimentacoes.map((mov, index) => {
                  const origem = getOrigem(mov);
                  
                  // Verificar se é o mesmo pedido/venda que o anterior
                  const movAnterior = index > 0 ? movimentacoes[index - 1] : null;
                  const mesmaVenda = movAnterior && 
                    mov.referencia_tipo === 'venda' && 
                    movAnterior.referencia_tipo === 'venda' &&
                    mov.referencia_id === movAnterior.referencia_id;
                  
                  return (
                    <tr 
                      key={mov.id} 
                      className={`hover:bg-gray-50 cursor-pointer ${
                        mesmaVenda ? 'border-l-4 border-l-blue-500 bg-blue-50' : ''
                      }`}
                      onClick={() => abrirModal(mov.tipo, mov)}
                    >
                      <td className="px-4 py-3 w-12" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(mov.id)}
                          onChange={() => handleSelectOne(mov.id)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {formatarData(mov.created_at)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                        {mov.tipo === 'entrada' ? (
                          <span className="text-green-600 font-semibold">{parseFloat(mov.quantidade).toFixed(2)}</span>
                        ) : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                        {mov.tipo === 'saida' ? (
                          <span className="text-red-600 font-semibold">{parseFloat(mov.quantidade).toFixed(2)}</span>
                        ) : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                        {produto.preco_venda ? `R$ ${produto.preco_venda.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                        {mov.custo_unitario ? (
                          mov.variacao_custo ? (
                            <div
                              className="relative group inline-block"
                              title={`Custo anterior: R$ ${mov.variacao_custo.custo_anterior.toFixed(2)}\nCusto atual: R$ ${mov.variacao_custo.custo_atual.toFixed(2)}\nDiferença: R$ ${mov.variacao_custo.diferenca_valor.toFixed(2)} (${mov.variacao_custo.diferenca_percentual > 0 ? '+' : ''}${mov.variacao_custo.diferenca_percentual.toFixed(1)}%)`}
                            >
                              <span className={`font-semibold ${
                                mov.variacao_custo.tipo === 'aumento' ? 'text-red-600' :
                                mov.variacao_custo.tipo === 'reducao' ? 'text-green-600' :
                                'text-gray-900'
                              }`}>
                                R$ {mov.custo_unitario.toFixed(2)}
                              </span>
                              {/* Tooltip */}
                              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-50">
                                <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg">
                                  <div className="font-semibold mb-1">Variação de Custo</div>
                                  <div className="space-y-1">
                                    <div>Anterior: R$ {mov.variacao_custo.custo_anterior.toFixed(2)}</div>
                                    <div>Atual: R$ {mov.variacao_custo.custo_atual.toFixed(2)}</div>
                                    <div className={mov.variacao_custo.tipo === 'aumento' ? 'text-red-400' : 'text-green-400'}>
                                      {mov.variacao_custo.tipo === 'aumento' ? '▲' : '▼'} R$ {Math.abs(mov.variacao_custo.diferenca_valor).toFixed(2)} ({mov.variacao_custo.diferenca_percentual > 0 ? '+' : ''}{mov.variacao_custo.diferenca_percentual.toFixed(1)}%)
                                    </div>
                                  </div>
                                  {/* Seta do tooltip */}
                                  <div className="absolute top-full left-1/2 transform -translate-x-1/2">
                                    <div className="border-4 border-transparent border-t-gray-900"></div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-900">R$ {mov.custo_unitario.toFixed(2)}</span>
                          )
                        ) : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {mov.lote_info ? (
                          <div className="flex flex-col">
                            <span className="font-medium">{mov.lote_info.nome}</span>
                            {mov.lote_info.consumido_acumulado !== undefined && (
                              <span className="text-xs text-gray-500">
                                ({mov.lote_info.consumido_acumulado.toFixed(0)}/{mov.lote_info.total_lote.toFixed(0)})
                              </span>
                            )}
                          </div>
                        ) : mov.lote_nome ? (
                          mov.lote_nome
                        ) : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        <div className="flex items-center gap-2">
                          {mesmaVenda && (
                            <span className="text-blue-600" title="Mesmo pedido/venda">↪</span>
                          )}
                          <span className={`${origem.cor} font-medium`}>
                            {origem.texto}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        <div className="flex items-center gap-2">
                          {mov.motivo && mov.motivo !== 'compra' && mov.motivo !== 'venda' && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                              {getMotivoLabel(mov.motivo)}
                            </span>
                          )}
                          {mov.observacao}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Lançamento */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">
                {editingMovimentacao ? 'Editar Lançamento' : 'Novo Lançamento'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {/* Tipo de Lançamento (apenas para novo) */}
              {!editingMovimentacao && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tipo *
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setTipoLancamento('entrada')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        tipoLancamento === 'entrada'
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Entrada
                    </button>
                    <button
                      type="button"
                      onClick={() => setTipoLancamento('saida')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        tipoLancamento === 'saida'
                          ? 'bg-red-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Saída
                    </button>
                    <button
                      type="button"
                      onClick={() => setTipoLancamento('balanco')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        tipoLancamento === 'balanco'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Balanço
                    </button>
                  </div>
                </div>
              )}

              {/* Quantidade */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {tipoLancamento === 'balanco' ? 'Saldo Total *' : 'Quantidade *'}
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.quantidade}
                  onChange={(e) => setFormData({ ...formData, quantidade: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
                {tipoLancamento === 'balanco' && (
                  <p className="mt-1 text-xs text-gray-500">
                    Estoque atual: {estoqueAtual}. Digite o novo saldo total.
                  </p>
                )}
              </div>

              {/* Preço de Compra (apenas para entrada) */}
              {tipoLancamento === 'entrada' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Preço de Compra
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.custo_unitario}
                      onChange={(e) => setFormData({ ...formData, custo_unitario: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="0.00"
                    />
                  </div>

                  {/* Número do Lote (opcional) */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Número do Lote <span className="text-gray-400">(opcional)</span>
                    </label>
                    <input
                      type="text"
                      value={formData.lote}
                      onChange={(e) => setFormData({ ...formData, lote: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Ex: LOTE-001"
                    />
                  </div>

                  {/* Data de Validade (opcional) */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Data de Validade <span className="text-gray-400">(opcional)</span>
                    </label>
                    <input
                      type="date"
                      value={formData.data_validade}
                      onChange={(e) => setFormData({ ...formData, data_validade: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Data de Fabricação (opcional) */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Data de Fabricação <span className="text-gray-400">(opcional)</span>
                    </label>
                    <input
                      type="date"
                      value={formData.data_fabricacao}
                      onChange={(e) => setFormData({ ...formData, data_fabricacao: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </>
              )}

              {/* Campos de lote para saída (opcional) */}
              {tipoLancamento === 'saida' && (
                <>
                  {/* Checkbox para KIT FÍSICO: retornar componentes */}
                  {produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'FISICO' && (
                    <div className="p-4 bg-yellow-50 border-2 border-yellow-300 rounded-lg">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          id="retornar_componentes"
                          checked={formData.retornar_componentes === true}
                          onChange={(e) => setFormData({ ...formData, retornar_componentes: e.target.checked })}
                          className="mt-1 h-5 w-5 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                        />
                        <div className="flex-1">
                          <label htmlFor="retornar_componentes" className="block text-sm font-semibold text-gray-900 cursor-pointer">
                            🔄 Desmontar kit e retornar componentes ao estoque
                          </label>
                          <p className="text-xs text-gray-700 mt-1">
                            <strong>Marque esta opção</strong> se você desmontou o kit e quer devolver os produtos unitários ao estoque.
                          </p>
                          <p className="text-xs text-gray-600 mt-1">
                            <strong>Deixe desmarcado</strong> se houve perda, roubo ou venda do kit montado.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Número do Lote <span className="text-gray-400">(opcional)</span>
                    </label>
                    <input
                      type="text"
                      value={formData.lote}
                      onChange={(e) => setFormData({ ...formData, lote: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Ex: LOTE-001"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Deixe vazio para usar FIFO automático
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Data de Validade <span className="text-gray-400">(opcional)</span>
                    </label>
                    <input
                      type="date"
                      value={formData.data_validade}
                      onChange={(e) => setFormData({ ...formData, data_validade: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </>
              )}

              {/* Observação */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Observação
                </label>
                <textarea
                  value={formData.observacao}
                  onChange={(e) => setFormData({ ...formData, observacao: e.target.value })}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Observações sobre este lançamento..."
                />
              </div>

              {/* Botões */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Incluir
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
