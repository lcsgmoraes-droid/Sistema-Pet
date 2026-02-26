import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { toast } from 'react-hot-toast';
import ModalNovaContaPagar from './ModalNovaContaPagar';
import { safeArray } from '../utils/safeArray';

const ContasPagar = () => {
  const navigate = useNavigate();
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    status: 'todos',
    fornecedor_id: null,
    data_inicio: '',
    data_fim: '',
    apenas_vencidas: false,
    apenas_vencer: false,
    numero_nf: ''
  });
  
  const [fornecedores, setFornecedores] = useState([]);
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [mostrarModalPagamento, setMostrarModalPagamento] = useState(false);
  const [mostrarModalNovaConta, setMostrarModalNovaConta] = useState(false);
  const [mostrarDetalhes, setMostrarDetalhes] = useState(false);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);
  const [mostrarModalNovaForma, setMostrarModalNovaForma] = useState(false);
  const [novaFormaData, setNovaFormaData] = useState({ nome: '', tipo: 'dinheiro', conta_bancaria_destino_id: null });
  
  const [dadosPagamento, setDadosPagamento] = useState({
    valor_pago: 0,
    data_pagamento: new Date().toISOString().split('T')[0],
    forma_pagamento_id: '',
    conta_bancaria_id: '',
    valor_juros: 0,
    valor_multa: 0,
    valor_desconto: 0,
    observacoes: ''
  });

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarFormasPagamento = async () => {
    const response = await api.get('/comissoes/formas-pagamento');
    const lista = response.data?.formas || [];
    return safeArray(lista).map((forma) => ({
      id: forma.id,
      nome: forma.nome,
      tipo: forma.nome?.toLowerCase()?.replace(/\s+/g, '_') || 'outro',
      icone: '💳',
      conta_bancaria_destino_id: null,
    }));
  };

  const carregarDados = async () => {
    try {
      const [contasRes, fornecedoresRes, formasRes, bancariasRes] = await Promise.allSettled([
        api.get(`/contas-pagar/?_t=${Date.now()}`),
        api.get(`/clientes/?tipo_cadastro=fornecedor`),
        carregarFormasPagamento(),
        api.get(`/contas-bancarias?apenas_ativas=true`)
      ]);

      if (contasRes.status === 'fulfilled') {
        setContas(safeArray(contasRes.value.data));
      } else {
        throw contasRes.reason;
      }

      if (fornecedoresRes.status === 'fulfilled') {
        setFornecedores(safeArray(fornecedoresRes.value.data));
      } else {
        throw fornecedoresRes.reason;
      }

      if (formasRes.status === 'fulfilled') {
        setFormasPagamento(safeArray(formasRes.value));
      } else {
        setFormasPagamento([]);
        console.warn('Nao foi possivel carregar formas de pagamento. Usando lista vazia.');
      }

      if (bancariasRes.status === 'fulfilled') {
        setContasBancarias(safeArray(bancariasRes.value.data));
      } else {
        throw bancariasRes.reason;
      }
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar contas a pagar');
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = async () => {
    try {
      setLoading(true);
            const params = new URLSearchParams();
      if (filtros.status !== 'todos') params.append('status', filtros.status);
      if (filtros.fornecedor_id) params.append('fornecedor_id', filtros.fornecedor_id);
      if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
      if (filtros.data_fim) params.append('data_fim', filtros.data_fim);
      if (filtros.apenas_vencidas) params.append('apenas_vencidas', 'true');
      if (filtros.apenas_vencer) params.append('apenas_vencer', 'true');
      if (filtros.numero_nf) params.append('numero_nf', filtros.numero_nf);
      
      const response = await api.get(`/contas-pagar/?${params}`);
      
      setContas(response.data);
    } catch (error) {
      console.error('Erro ao filtrar:', error);
      toast.error('Erro ao aplicar filtros');
    } finally {
      setLoading(false);
    }
  };

  const abrirModalPagamento = (conta) => {
    setContaSelecionada(conta);
    // Buscar conta padrão da forma de pagamento se houver
    const formaDefault = formasPagamento.find(f => f.id === conta.forma_pagamento_id);
    setDadosPagamento({
      valor_pago: conta.valor_final - conta.valor_pago,
      forma_pagamento_id: conta.forma_pagamento_id || '',
      conta_bancaria_id: formaDefault?.conta_bancaria_destino_id || '',
      valor_juros: 0,
      valor_multa: 0,
      valor_desconto: 0,
      observacoes: ''
    });
    setMostrarModalPagamento(true);
  };

  const abrirDetalhes = (conta) => {
    setContaSelecionada(conta);
    setMostrarDetalhes(true);
  };

  const abrirNotaFiscal = (conta) => {
    // Se tem nota_entrada_id, navegar para a página de compras/notas de entrada
    if (conta.nota_entrada_id) {
      navigate(`/compras?nota_id=${conta.nota_entrada_id}`);
    } else if (conta.nfe_numero) {
      // Se só tem o número, buscar por número
      navigate(`/compras?numero=${conta.nfe_numero}`);
    } else {
      toast.error('Nota fiscal não encontrada');
    }
  };

  const abrirFluxoDeCaixa = (conta) => {
    // Redireciona para o fluxo de caixa com filtros da conta
    const params = new URLSearchParams();
    if (conta.fornecedor_nome) {
      params.append('busca', conta.fornecedor_nome);
    }
    if (conta.documento) {
      params.append('documento', conta.documento);
    }
    navigate(`/financeiro/fluxo-caixa?${params.toString()}`);
    toast.success('Redirecionando para o Fluxo de Caixa...');
  };

  const handleFormaChange = (formaId) => {
    const forma = formasPagamento.find(f => f.id === parseInt(formaId));
    setDadosPagamento({
      ...dadosPagamento,
      forma_pagamento_id: parseInt(formaId) || '',
      conta_bancaria_id: forma?.conta_bancaria_destino_id || dadosPagamento.conta_bancaria_id || ''
    });
  };
  const salvarNovaForma = async () => {
    try {
            await api.post(`/financeiro/formas-pagamento`, {
        ...novaFormaData,
        taxa_percentual: 0,
        taxa_fixa: 0,
        prazo_dias: 0,
        ativo: true,
        permite_parcelamento: false,
        parcelas_maximas: 1
      });
      toast.success('Forma de pagamento criada!');
      setMostrarModalNovaForma(false);
      setNovaFormaData({ nome: '', tipo: 'dinheiro', conta_bancaria_destino_id: null });
      carregarDados(); // Recarregar formas
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao criar forma de pagamento');
    }
  };

  const registrarPagamento = async () => {
    try {
            await api.post(
        `/contas-pagar/${contaSelecionada.id}/pagar`,
        dadosPagamento
      );
      
      toast.success('Pagamento registrado com sucesso!');
      setMostrarModalPagamento(false);
      carregarDados();
    } catch (error) {
      console.error('Erro ao registrar pagamento:', error);
      toast.error(error.response?.data?.detail || 'Erro ao registrar pagamento');
    }
  };

  const formatarData = (data) => {
    if (!data) return '-';
    // Evita problemas de timezone ao criar data diretamente dos componentes
    const partes = data.split('T')[0].split('-');
    const dataLocal = new Date(parseInt(partes[0]), parseInt(partes[1]) - 1, parseInt(partes[2]));
    return dataLocal.toLocaleDateString('pt-BR');
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const getStatusBadge = (conta) => {
    const hoje = new Date();
    const vencimento = new Date(conta.data_vencimento);
    
    if (conta.status === 'pago') {
      return <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">✓ Pago</span>;
    }
    
    if (vencimento < hoje) {
      return <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-800">⚠ Vencida</span>;
    }
    
    if (conta.status === 'parcial') {
      return <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800">⚡ Parcial</span>;
    }
    
    return <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">⏱ Pendente</span>;
  };

  if (loading) {
    return <div className="text-center p-8">Carregando contas a pagar...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">💰 Contas a Pagar</h2>
        <button 
          onClick={() => setMostrarModalNovaConta(true)}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg"
        >
          ➕ Nova Conta
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <h5 className="text-lg font-semibold mb-4">🔍 Filtros</h5>
        <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.status}
              onChange={(e) => setFiltros({...filtros, status: e.target.value})}
            >
              <option value="todos">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="parcial">Parcial</option>
              <option value="pago">Pago</option>
              <option value="vencido">Vencido</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Fornecedor</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.fornecedor_id || ''}
              onChange={(e) => setFiltros({...filtros, fornecedor_id: e.target.value || null})}
            >
              <option value="">Todos</option>
              {safeArray(fornecedores).map(f => (
                <option key={f.id} value={f.id}>{f.nome}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Número NF</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded px-3 py-2"
              placeholder="Ex: 12345"
              value={filtros.numero_nf}
              onChange={(e) => setFiltros({...filtros, numero_nf: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Data Início</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({...filtros, data_inicio: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Data Fim</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({...filtros, data_fim: e.target.value})}
            />
          </div>

          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencidas}
                onChange={(e) => setFiltros({...filtros, apenas_vencidas: e.target.checked, apenas_vencer: false})}
              />
              <span className="text-sm">Só Vencidas</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencer}
                onChange={(e) => setFiltros({...filtros, apenas_vencer: e.target.checked, apenas_vencidas: false})}
              />
              <span className="text-sm">A Vencer</span>
            </label>
            <button 
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm"
              onClick={aplicarFiltros}
            >
              Filtrar
            </button>
          </div>
        </div>
      </div>

      {/* Tabela de Contas */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Descrição</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Fornecedor</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Vencimento</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Valor Original</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Valor Pago</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Saldo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {contas.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-4 py-8 text-center text-gray-500">
                    Nenhuma conta encontrada
                  </td>
                </tr>
              ) : (
                safeArray(contas).map(conta => (
                  <tr key={conta.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{conta.id}</td>
                    <td className="px-4 py-3 text-sm">
                      {conta.descricao}
                      {conta.eh_parcelado && (
                        <span className="ml-2 px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
                          {conta.numero_parcela}/{conta.total_parcelas}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">{conta.fornecedor_nome || '-'}</td>
                    <td className="px-4 py-3 text-sm">{formatarData(conta.data_vencimento)}</td>
                    <td className="px-4 py-3 text-sm">{formatarMoeda(conta.valor_original)}</td>
                    <td className="px-4 py-3 text-sm">{formatarMoeda(conta.valor_pago)}</td>
                    <td className="px-4 py-3 text-sm font-bold">{formatarMoeda(conta.valor_final - conta.valor_pago)}</td>
                    <td className="px-4 py-3 text-sm">{getStatusBadge(conta)}</td>
                    <td className="px-4 py-3 text-sm">
                      {conta.status !== 'pago' && (
                        <button
                          className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-xs mr-2"
                          onClick={() => abrirModalPagamento(conta)}
                          title="Registrar Pagamento"
                        >
                          💰 Pagar
                        </button>
                      )}
                      <button
                        className="bg-blue-50 hover:bg-blue-100 text-blue-600 px-3 py-1 rounded text-xs"
                        onClick={() => abrirDetalhes(conta)}
                        title="Ver Detalhes"
                      >
                        👁️
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {contas.length > 0 && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-3">
            <strong>Total:</strong> {contas.length} conta(s) | 
            <strong className="ml-3">Saldo a Pagar:</strong> {formatarMoeda(
              contas.reduce((sum, c) => sum + (c.valor_final - c.valor_pago), 0)
            )}
          </div>
        )}
      </div>

      {/* Modal de Pagamento */}
      {mostrarModalPagamento && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <h5 className="text-xl font-bold">💰 Registrar Pagamento</h5>
              <button
                className="text-gray-500 hover:text-gray-700 text-2xl"
                onClick={() => setMostrarModalPagamento(false)}
              >
                ×
              </button>
            </div>
            
            <div className="p-6">
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-sm">
                <strong>Conta:</strong> {contaSelecionada.descricao}<br/>
                <strong>Valor Total:</strong> {formatarMoeda(contaSelecionada.valor_final)}<br/>
                <strong>Já Pago:</strong> {formatarMoeda(contaSelecionada.valor_pago)}<br/>
                <strong>Saldo Restante:</strong> {formatarMoeda(contaSelecionada.valor_final - contaSelecionada.valor_pago)}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Valor a Pagar *</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_pago}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, valor_pago: parseFloat(e.target.value)})}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Data do Pagamento *</label>
                  <input
                    type="date"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosPagamento.data_pagamento}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, data_pagamento: e.target.value})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Forma de Pagamento</label>
                  <div className="flex gap-2">
                    <select
                      className="flex-1 border border-gray-300 rounded px-3 py-2"
                      value={dadosPagamento.forma_pagamento_id || ''}
                      onChange={(e) => handleFormaChange(e.target.value)}
                    >
                      <option value="">Selecione...</option>
                      {safeArray(formasPagamento).map(f => (
                        <option key={f.id} value={f.id}>{f.icone || '💳'} {f.nome}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                      onClick={() => setMostrarModalNovaForma(true)}
                      title="Adicionar nova forma de pagamento"
                    >
                      +
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Conta Bancária * 
                    {dadosPagamento.forma_pagamento_id && formasPagamento.find(f => f.id === dadosPagamento.forma_pagamento_id)?.conta_bancaria_destino_id && (
                      <span className="text-xs text-gray-500 ml-2">(Padrão da forma selecionada)</span>
                    )}
                  </label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosPagamento.conta_bancaria_id || ''}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, conta_bancaria_id: parseInt(e.target.value) || null})}
                  >
                    <option value="">Selecione a conta...</option>
                    {safeArray(contasBancarias).map(c => (
                      <option key={c.id} value={c.id}>
                        {c.nome} - {formatarMoeda(c.saldo_atual || 0)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Juros</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_juros}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, valor_juros: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Multa</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_multa}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, valor_multa: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Desconto</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_desconto}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, valor_desconto: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Observações</label>
                  <textarea
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    rows="3"
                    value={dadosPagamento.observacoes}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, observacoes: e.target.value})}
                  />
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded p-3 mt-4">
                <strong>Valor Final do Pagamento:</strong> {formatarMoeda(
                  (dadosPagamento.valor_pago || 0) +
                  (dadosPagamento.valor_juros || 0) +
                  (dadosPagamento.valor_multa || 0) -
                  (dadosPagamento.valor_desconto || 0)
                )}
              </div>
            </div>
            
            <div className="flex justify-end gap-3 border-t p-4">
              <button
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                onClick={() => setMostrarModalPagamento(false)}
              >
                Cancelar
              </button>
              <button
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                onClick={registrarPagamento}
              >
                ✓ Confirmar Pagamento
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Detalhes */}
      {mostrarDetalhes && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center sticky top-0">
              <h3 className="text-xl font-semibold">Detalhes da Conta</h3>
              <button
                onClick={() => setMostrarDetalhes(false)}
                className="text-white hover:bg-blue-700 px-3 py-1 rounded"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Parcela</label>
                  <p className="mt-1 text-lg">
                    {contaSelecionada.numero_parcela && contaSelecionada.total_parcelas 
                      ? `${contaSelecionada.numero_parcela}/${contaSelecionada.total_parcelas}`
                      : contaSelecionada.documento || 'Única'}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Fornecedor</label>
                  <p className="mt-1 text-lg">{contaSelecionada.fornecedor_nome || 'N/A'}</p>
                </div>
              </div>

              {contaSelecionada.nfe_numero && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Nota Fiscal</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => abrirNotaFiscal(contaSelecionada)}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg border border-blue-200 transition-colors"
                    >
                      <span className="text-xl">📄</span>
                      <span className="font-medium">{contaSelecionada.nfe_numero}</span>
                    </button>
                    <button
                      onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                      className="flex items-center gap-2 px-4 py-2 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg border border-green-200 transition-colors"
                      title="Ver no Fluxo de Caixa"
                    >
                      <span className="text-xl">📈</span>
                      <span className="text-sm">Fluxo</span>
                    </button>
                  </div>
                </div>
              )}

              {!contaSelecionada.nfe_numero && (
                <div>
                  <button
                    onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg border border-green-200 transition-colors"
                  >
                    <span className="text-xl">📈</span>
                    <span className="font-medium">Ver no Fluxo de Caixa</span>
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Data de Emissão</label>
                  <p className="mt-1">{formatarData(contaSelecionada.data_emissao)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Data de Vencimento</label>
                  <p className="mt-1">{formatarData(contaSelecionada.data_vencimento)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Valor Original</label>
                  <p className="mt-1 text-lg font-semibold text-blue-600">{formatarMoeda(contaSelecionada.valor_final || contaSelecionada.valor_total || 0)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Valor Pago</label>
                  <p className="mt-1 text-lg font-semibold text-green-600">{formatarMoeda(contaSelecionada.valor_pago || 0)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Saldo Restante</label>
                  <p className="mt-1 text-lg font-semibold text-red-600">
                    {formatarMoeda((contaSelecionada.valor_final || contaSelecionada.valor_total || 0) - (contaSelecionada.valor_pago || 0))}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Status</label>
                  <p className="mt-1">
                    <span className={`px-2 py-1 rounded text-sm ${
                      contaSelecionada.status === 'pago' ? 'bg-green-100 text-green-800' :
                      contaSelecionada.status === 'parcial' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {contaSelecionada.status === 'pago' ? 'Pago' :
                       contaSelecionada.status === 'parcial' ? 'Parcial' : 'Pendente'}
                    </span>
                  </p>
                </div>
              </div>

              {contaSelecionada.observacoes && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Observações</label>
                  <p className="mt-1 text-gray-600">{contaSelecionada.observacoes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal Nova Forma Rápida */}
      {mostrarModalNovaForma && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="bg-green-600 text-white px-6 py-4 flex justify-between items-center">
              <h3 className="text-xl font-semibold">Nova Forma de Pagamento</h3>
              <button
                onClick={() => setMostrarModalNovaForma(false)}
                className="text-white hover:bg-green-700 px-3 py-1 rounded"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Nome *</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.nome}
                  onChange={(e) => setNovaFormaData({...novaFormaData, nome: e.target.value})}
                  placeholder="Ex: PIX Santander, Dinheiro..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Tipo</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.tipo}
                  onChange={(e) => setNovaFormaData({...novaFormaData, tipo: e.target.value})}
                >
                  <option value="dinheiro">💵 Dinheiro</option>
                  <option value="pix">📱 PIX</option>
                  <option value="cartao_debito">💳 Cartão Débito</option>
                  <option value="cartao_credito">💳 Cartão Crédito</option>
                  <option value="transferencia">🏦 Transferência</option>
                  <option value="boleto">📄 Boleto</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Conta Bancária Padrão</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.conta_bancaria_destino_id || ''}
                  onChange={(e) => setNovaFormaData({...novaFormaData, conta_bancaria_destino_id: parseInt(e.target.value) || null})}
                >
                  <option value="">Nenhuma (selecionar manualmente)</option>
                  {safeArray(contasBancarias).map(c => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Esta conta será pré-selecionada automaticamente ao usar esta forma
                </p>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 border-t p-4">
              <button
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                onClick={() => setMostrarModalNovaForma(false)}
              >
                Cancelar
              </button>
              <button
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                onClick={salvarNovaForma}
              >
                ✓ Criar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Nova Conta */}
      <ModalNovaContaPagar
        isOpen={mostrarModalNovaConta}
        onClose={() => setMostrarModalNovaConta(false)}
        onSave={carregarDados}
      />
    </div>
  );
};

export default ContasPagar;
