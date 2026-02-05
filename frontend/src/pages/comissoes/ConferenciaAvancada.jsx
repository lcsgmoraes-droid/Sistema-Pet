/**
 * SPRINT 6 - PASSO 6: Componente de Conferência Avançada com Filtros
 * 
 * Funcionalidades:
 * - Filtros por grupo de produto, produto, período
 * - Rodapé com período selecionado e totais
 * - Modal para fechar com pagamento (parcial ou total)
 * - UX tipo ERP (SimpleVet)
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api';

const ConferenciaAvancada = () => {
  const { funcionario_id } = useParams();
  const navigate = useNavigate();

  // Estado de carregamento
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Dados gerais
  const [funcionario, setFuncionario] = useState(null);
  const [comissoes, setComissoes] = useState([]);
  const [resumo, setResumo] = useState(null);
  const [periodoSelecionado, setPeriodoSelecionado] = useState(null);

  // Filtros
  const [gruposProduto, setGruposProduto] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [formasPagamento, setFormasPagamento] = useState([]);

  const [filtroGrupo, setFiltroGrupo] = useState('');
  const [filtroProduto, setFiltroProduto] = useState('');
  const [filtroDataInicio, setFiltroDataInicio] = useState('');
  const [filtroDataFim, setFiltroDataFim] = useState('');

  // Modal de fechamento
  const [mostrarModalFechamento, setMostrarModalFechamento] = useState(false);
  const [comissoesSelecionadas, setComissoesSelecionadas] = useState(new Set());
  const [valorPago, setValorPago] = useState('');
  const [formaPagamentoSelecionada, setFormaPagamentoSelecionada] = useState('nao_informado');
  const [dataPagamento, setDataPagamento] = useState(new Date().toISOString().split('T')[0]);
  const [observacoes, setObservacoes] = useState('');
  const [loadingFechamento, setLoadingFechamento] = useState(false);
  const [erroFechamento, setErroFechamento] = useState(null);

  // Carregar dados iniciais
  useEffect(() => {
    carregarDados();
  }, [funcionario_id]);

  const carregarDados = async () => {
    try {
      setLoading(true);
      setError(null);

      // Carregar conferência (sem filtros inicialmente)
      const confRes = await api.get(`/comissoes/conferencia-avancada/${funcionario_id}`);
      if (confRes.data.success) {
        setFuncionario(confRes.data.funcionario);
        setComissoes(confRes.data.comissoes);
        setResumo(confRes.data.resumo);
        setPeriodoSelecionado(confRes.data.periodo_selecionado);
      }

      // Carregar formas de pagamento
      const formasRes = await api.get('/comissoes/formas-pagamento');
      if (formasRes.data.success) {
        setFormasPagamento(formasRes.data.formas);
      }

      // Carregar grupos de produto (categorias)
      const categoriasRes = await api.get('/produtos/categorias');
      if (categoriasRes.data.data) {
        setGruposProduto(categoriasRes.data.data);
      }

    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao carregar dados');
      console.error('Erro:', err);
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = async () => {
    try {
      setLoading(true);
      
      const params = {
        grupo_produto: filtroGrupo ? parseInt(filtroGrupo) : undefined,
        produto_id: filtroProduto ? parseInt(filtroProduto) : undefined,
        data_inicio: filtroDataInicio || undefined,
        data_fim: filtroDataFim || undefined,
      };

      const confRes = await api.get(
        `/comissoes/conferencia-avancada/${funcionario_id}`,
        { params: Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== undefined)) }
      );

      if (confRes.data.success) {
        setComissoes(confRes.data.comissoes);
        setResumo(confRes.data.resumo);
        setPeriodoSelecionado(confRes.data.periodo_selecionado);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao aplicar filtros');
    } finally {
      setLoading(false);
    }
  };

  const limparFiltros = () => {
    setFiltroGrupo('');
    setFiltroProduto('');
    setFiltroDataInicio('');
    setFiltroDataFim('');
    setTimeout(() => carregarDados(), 100);
  };

  const toggleComissaoSelecionada = (id) => {
    const nova = new Set(comissoesSelecionadas);
    if (nova.has(id)) {
      nova.delete(id);
    } else {
      nova.add(id);
    }
    setComissoesSelecionadas(nova);
  };

  const selecionarTodas = () => {
    if (comissoesSelecionadas.size === comissoes.length) {
      setComissoesSelecionadas(new Set());
    } else {
      setComissoesSelecionadas(new Set(comissoes.map(c => c.id)));
    }
  };

  const handleAbrirModalFechamento = () => {
    if (comissoesSelecionadas.size === 0) {
      alert('Selecione pelo menos uma comissão');
      return;
    }

    setDataPagamento(new Date().toISOString().split('T')[0]);
    setValorPago('');
    setFormaPagamentoSelecionada('nao_informado');
    setObservacoes('');
    setErroFechamento(null);
    setMostrarModalFechamento(true);
  };

  const handleConfirmarFechamento = async () => {
    try {
      if (!valorPago || parseFloat(valorPago) <= 0) {
        setErroFechamento('Valor a pagar deve ser maior que zero');
        return;
      }

      setLoadingFechamento(true);
      setErroFechamento(null);

      const payload = {
        comissoes_ids: Array.from(comissoesSelecionadas),
        valor_pago: parseFloat(valorPago),
        forma_pagamento: formaPagamentoSelecionada,
        data_pagamento: dataPagamento,
        observacoes: observacoes || null,
      };

      const response = await api.post('/comissoes/fechar-com-pagamento', payload);

      if (response.data.success) {
        alert(
          `✅ Fechamento realizado com sucesso!\n\n` +
          `Processadas: ${response.data.total_processadas}\n` +
          `Valor total: R$ ${response.data.valor_total_fechado.toFixed(2)}\n` +
          `Valor pago: R$ ${response.data.valor_total_pago.toFixed(2)}\n` +
          `Saldo restante: R$ ${response.data.saldo_total_restante.toFixed(2)}\n` +
          `Comissões com saldo: ${response.data.comissoes_com_saldo}`
        );

        setMostrarModalFechamento(false);
        setComissoesSelecionadas(new Set());
        carregarDados();
      }
    } catch (err) {
      setErroFechamento(err.response?.data?.detail || 'Erro ao fechar comissões');
    } finally {
      setLoadingFechamento(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Calcular valores da seleção
  const valorTotalSelecionado = Array.from(comissoesSelecionadas).reduce((sum, id) => {
    const comissao = comissoes.find(c => c.id === id);
    return sum + (comissao ? comissao.valor_comissao : 0);
  }, 0);

  const saldoRestanteCalculado = valorTotalSelecionado - (parseFloat(valorPago) || 0);

  return (
    <div className="p-6">
      {/* ============ HEADER ============ */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Conferência de Comissões</h1>
            <p className="text-gray-600 mt-1">
              {funcionario ? `${funcionario.nome} (ID: ${funcionario.id})` : 'Carregando...'}
            </p>
          </div>
          <button
            onClick={() => navigate('/comissoes/abertas')}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            ← Voltar
          </button>
        </div>
      </div>

      {/* ============ FILTROS ============ */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-4 text-gray-700">Filtros Avançados</h2>
        
        <div className="grid grid-cols-4 gap-4">
          {/* Filtro: Grupo de Produto */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Grupo de Produto</label>
            <select
              value={filtroGrupo}
              onChange={(e) => setFiltroGrupo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">Todos</option>
              {gruposProduto.map(grupo => (
                <option key={grupo.id} value={grupo.id}>{grupo.nome}</option>
              ))}
            </select>
          </div>

          {/* Filtro: Produto */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Produto</label>
            <input
              type="text"
              placeholder="Buscar produto..."
              value={filtroProduto}
              onChange={(e) => setFiltroProduto(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* Filtro: Data Início */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Data Início</label>
            <input
              type="date"
              value={filtroDataInicio}
              onChange={(e) => setFiltroDataInicio(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* Filtro: Data Fim */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Data Fim</label>
            <input
              type="date"
              value={filtroDataFim}
              onChange={(e) => setFiltroDataFim(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
        </div>

        {/* Botões de Ação */}
        <div className="mt-4 flex gap-2">
          <button
            onClick={aplicarFiltros}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Aplicar Filtros
          </button>
          <button
            onClick={limparFiltros}
            className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
          >
            Limpar
          </button>
        </div>
      </div>

      {/* ============ PERÍODO E RESUMO ============ */}
      {periodoSelecionado && resumo && (
        <div className="bg-blue-50 rounded-lg p-4 mb-6 border border-blue-200">
          <div className="grid grid-cols-2 gap-6">
            {/* Período */}
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">Período Selecionado</h3>
              <p className="text-gray-600">
                {periodoSelecionado.data_inicio && periodoSelecionado.data_fim
                  ? `${new Date(periodoSelecionado.data_inicio).toLocaleDateString('pt-BR')} até ${new Date(periodoSelecionado.data_fim).toLocaleDateString('pt-BR')}`
                  : 'Sem período específico'}
              </p>
              {periodoSelecionado.grupo_produto_nome && (
                <p className="text-gray-600 text-sm">Grupo: {periodoSelecionado.grupo_produto_nome}</p>
              )}
              {periodoSelecionado.produto_nome && (
                <p className="text-gray-600 text-sm">Produto: {periodoSelecionado.produto_nome}</p>
              )}
            </div>

            {/* Resumo Financeiro */}
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">Resumo do Período</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Quantidade</p>
                  <p className="text-xl font-bold text-gray-800">{resumo.quantidade_comissoes}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Total</p>
                  <p className="text-xl font-bold text-green-600">
                    R$ {resumo.valor_total.toFixed(2)}
                  </p>
                </div>
                {resumo.valor_pago_total > 0 && (
                  <>
                    <div>
                      <p className="text-sm text-gray-600">Pago</p>
                      <p className="text-lg font-semibold text-blue-600">
                        R$ {resumo.valor_pago_total.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Saldo</p>
                      <p className="text-lg font-semibold text-orange-600">
                        R$ {resumo.saldo_restante_total.toFixed(2)}
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============ TABELA DE COMISSÕES ============ */}
      <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={comissoesSelecionadas.size === comissoes.length && comissoes.length > 0}
                    onChange={selecionarTodas}
                  />
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Data</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Produto</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Cliente</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Quantidade</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Base</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">%</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Valor</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Pago</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Saldo</th>
              </tr>
            </thead>
            <tbody>
              {comissoes.map((comissao) => (
                <tr key={comissao.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={comissoesSelecionadas.has(comissao.id)}
                      onChange={() => toggleComissaoSelecionada(comissao.id)}
                    />
                  </td>
                  <td className="px-4 py-3 text-sm">{new Date(comissao.data_venda).toLocaleDateString('pt-BR')}</td>
                  <td className="px-4 py-3 text-sm">{comissao.nome_produto}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{comissao.cliente_nome}</td>
                  <td className="px-4 py-3 text-sm text-right">{comissao.quantidade.toFixed(2)}</td>
                  <td className="px-4 py-3 text-sm text-right">R$ {comissao.valor_base_calculo.toFixed(2)}</td>
                  <td className="px-4 py-3 text-sm text-right">{comissao.percentual_comissao.toFixed(2)}%</td>
                  <td className="px-4 py-3 text-sm text-right font-semibold text-green-600">
                    R$ {comissao.valor_comissao.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-blue-600">
                    {comissao.valor_pago ? `R$ ${comissao.valor_pago.toFixed(2)}` : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-orange-600">
                    {comissao.saldo_restante ? `R$ ${comissao.saldo_restante.toFixed(2)}` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ============ RODAPÉ COM TOTAIS DA SELEÇÃO ============ */}
      <div className="bg-gray-900 text-white rounded-lg p-4 mb-6">
        <div className="flex justify-between items-center">
          <div>
            <p className="text-sm text-gray-300">
              {comissoesSelecionadas.size} de {comissoes.length} comissões selecionadas
            </p>
          </div>
          <div className="flex gap-6">
            <div>
              <p className="text-sm text-gray-300">Total Selecionado</p>
              <p className="text-2xl font-bold text-green-400">
                R$ {valorTotalSelecionado.toFixed(2)}
              </p>
            </div>
            {parseFloat(valorPago) > 0 && (
              <>
                <div>
                  <p className="text-sm text-gray-300">Será Pago</p>
                  <p className="text-2xl font-bold text-blue-400">
                    R$ {parseFloat(valorPago).toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-300">Saldo Restante</p>
                  <p className={`text-2xl font-bold ${saldoRestanteCalculado > 0 ? 'text-orange-400' : 'text-green-400'}`}>
                    R$ {saldoRestanteCalculado.toFixed(2)}
                  </p>
                </div>
              </>
            )}
            <button
              onClick={handleAbrirModalFechamento}
              disabled={comissoesSelecionadas.size === 0}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 rounded-lg font-semibold transition"
            >
              Fechar e Pagar
            </button>
          </div>
        </div>
      </div>

      {/* ============ MODAL DE FECHAMENTO ============ */}
      {mostrarModalFechamento && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg w-full max-w-2xl p-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Fechamento com Pagamento</h2>

            {erroFechamento && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                {erroFechamento}
              </div>
            )}

            <div className="space-y-4">
              {/* Resumo do que será fechado */}
              <div className="bg-blue-50 p-4 rounded border border-blue-200">
                <p className="text-sm text-gray-600">Comissões a processar: {comissoesSelecionadas.size}</p>
                <p className="text-lg font-bold text-gray-800">
                  Valor Total: R$ {valorTotalSelecionado.toFixed(2)}
                </p>
              </div>

              {/* Forma de Pagamento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Forma de Pagamento *</label>
                <select
                  value={formaPagamentoSelecionada}
                  onChange={(e) => setFormaPagamentoSelecionada(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  {formasPagamento.map(forma => (
                    <option key={forma.id} value={forma.nome}>{forma.descricao}</option>
                  ))}
                </select>
              </div>

              {/* Valor a Pagar */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Valor a Pagar *</label>
                <div className="flex gap-2">
                  <span className="flex items-center bg-gray-100 px-3 py-2 rounded-lg border border-gray-300">R$</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={valorTotalSelecionado}
                    value={valorPago}
                    onChange={(e) => setValorPago(e.target.value)}
                    placeholder="0.00"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Máximo: R$ {valorTotalSelecionado.toFixed(2)}
                  {parseFloat(valorPago) < valorTotalSelecionado && parseFloat(valorPago) > 0 && (
                    <span className="text-orange-600 font-semibold ml-2">
                      (Pagamento Parcial - Saldo: R$ {(valorTotalSelecionado - parseFloat(valorPago)).toFixed(2)})
                    </span>
                  )}
                </p>
              </div>

              {/* Data de Pagamento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Data de Pagamento *</label>
                <input
                  type="date"
                  value={dataPagamento}
                  onChange={(e) => setDataPagamento(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              {/* Observações */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Observações</label>
                <textarea
                  value={observacoes}
                  onChange={(e) => setObservacoes(e.target.value)}
                  placeholder="Observações opcionais..."
                  rows="3"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
            </div>

            {/* Botões */}
            <div className="mt-6 flex gap-3 justify-end">
              <button
                onClick={() => setMostrarModalFechamento(false)}
                disabled={loadingFechamento}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmarFechamento}
                disabled={loadingFechamento}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loadingFechamento ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Processando...
                  </>
                ) : (
                  'Confirmar Fechamento'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConferenciaAvancada;
