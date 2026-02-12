/**
 * SPRINT 6 - PASSO 2/5: CONFERÊNCIA DE COMISSÃO POR FUNCIONÁRIO
 * 
 * Tela de conferência das comissões pendentes de um funcionário específico.
 * Permite visualizar, filtrar e validar antes do fechamento.
 * 
 * Criado em: 22/01/2026
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api';

const ComissoesFechamentoFuncionario = () => {
  const { funcionario_id } = useParams();
  const navigate = useNavigate();
  
  // Estados
  const [comissoes, setComissoes] = useState([]);
  const [funcionario, setFuncionario] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [valorTotal, setValorTotal] = useState(0);
  
  // Estados de filtro
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  
  // Estados de modal e fechamento
  const [mostrarModalFechamento, setMostrarModalFechamento] = useState(false);
  const [dataPagamento, setDataPagamento] = useState('');
  const [observacaoFechamento, setObservacaoFechamento] = useState('');
  const [loadingFechamento, setLoadingFechamento] = useState(false);
  const [erroFechamento, setErroFechamento] = useState(null);

  // Carregar comissões ao montar componente ou alterar filtros
  useEffect(() => {
    carregarComissoes();
  }, [funcionario_id]);

  const carregarComissoes = async () => {
    try {
      setLoading(true);
      setErro(null);
      
      // Construir query params
      const params = new URLSearchParams();
      if (dataInicio) params.append('data_inicio', dataInicio);
      if (dataFim) params.append('data_fim', dataFim);
      
      const url = `/comissoes/fechamento/${funcionario_id}${params.toString() ? '?' + params.toString() : ''}`;
      const response = await api.get(url);
      
      if (response.data.success) {
        setComissoes(response.data.comissoes || []);
        setFuncionario(response.data.funcionario);
        setValorTotal(response.data.valor_total || 0);
      } else {
        setErro('Erro ao carregar comissões');
      }
    } catch (error) {
      console.error('Erro ao carregar comissões:', error);
      if (error.response?.status === 404) {
        setErro('Funcionário não encontrado');
      } else {
        setErro(error.response?.data?.detail || 'Erro ao carregar comissões');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAplicarFiltro = () => {
    carregarComissoes();
  };

  const handleLimparFiltro = () => {
    setDataInicio('');
    setDataFim('');
    setTimeout(() => carregarComissoes(), 100);
  };

  const handleVoltar = () => {
    navigate('/comissoes/abertas');
  };

  const handleAbrirModalFechamento = () => {
    // Inicializar com data de hoje
    const hoje = new Date().toISOString().split('T')[0];
    setDataPagamento(hoje);
    setObservacaoFechamento('');
    setErroFechamento(null);
    setMostrarModalFechamento(true);
  };

  const handleFecharModal = () => {
    if (!loadingFechamento) {
      setMostrarModalFechamento(false);
      setErroFechamento(null);
    }
  };

  const handleConfirmarFechamento = async () => {
    try {
      setLoadingFechamento(true);
      setErroFechamento(null);

      // Preparar payload
      const comissoesIds = comissoes.map(c => c.id);
      
      const payload = {
        comissoes_ids: comissoesIds,
        data_pagamento: dataPagamento,
        observacao: observacaoFechamento || null
      };

      // Executar fechamento
      const response = await api.post('/comissoes/fechar', payload);

      if (response.data.success) {
        // Sucesso - mostrar alert e redirecionar
        alert(
          `✅ Fechamento realizado com sucesso!\n\n` +
          `Comissões processadas: ${response.data.total_processadas}\n` +
          `Valor total: ${formatarMoeda(response.data.valor_total_fechamento)}\n` +
          `Data do pagamento: ${formatarData(dataPagamento)}`
        );
        
        // Redirecionar para lista de comissões abertas
        navigate('/comissoes/abertas');
      } else {
        setErroFechamento('Erro ao processar fechamento');
      }
    } catch (error) {
      console.error('Erro ao fechar comissões:', error);
      setErroFechamento(
        error.response?.data?.detail || 
        'Erro ao fechar comissões. Tente novamente.'
      );
    } finally {
      setLoadingFechamento(false);
    }
  };

  const handleAbrirVenda = (vendaId) => {
    window.open(`/pdv?venda_id=${vendaId}`, '_blank');
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const formatarData = (data) => {
    if (!data) return '-';
    const dataObj = new Date(data + 'T00:00:00');
    return dataObj.toLocaleDateString('pt-BR');
  };

  // Loading
  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white shadow-md rounded-lg p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600">Carregando comissões...</span>
          </div>
        </div>
      </div>
    );
  }

  // Erro
  if (erro) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center">
            <svg className="h-6 w-6 text-red-500 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="text-red-800 font-medium">Erro ao carregar dados</h3>
              <p className="text-red-600 text-sm mt-1">{erro}</p>
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              onClick={carregarComissoes}
              className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors"
            >
              Tentar Novamente
            </button>
            <button
              onClick={handleVoltar}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md transition-colors"
            >
              Voltar
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Tela principal
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white shadow-md rounded-lg p-8">
        {/* Header */}
        <div className="mb-6 border-b border-gray-200 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">
                Conferência de Comissões
              </h1>
              <p className="text-gray-600 mt-1">
                Funcionário: <span className="font-semibold text-gray-800">{funcionario?.nome}</span>
              </p>
            </div>
            <button
              onClick={handleVoltar}
              className="flex items-center px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
            >
              <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Voltar
            </button>
          </div>
        </div>

        {/* Filtros */}
        <div className="mb-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Filtros</h3>
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Início
              </label>
              <input
                type="date"
                value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Fim
              </label>
              <input
                type="date"
                value={dataFim}
                onChange={(e) => setDataFim(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleAplicarFiltro}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
              >
                Aplicar
              </button>
              <button
                onClick={handleLimparFiltro}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-md transition-colors"
              >
                Limpar
              </button>
            </div>
          </div>
        </div>

        {/* Resumo */}
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-600 font-medium">Total de Comissões</p>
              <p className="text-2xl font-bold text-blue-800">{comissoes.length}</p>
            </div>
            <div>
              <p className="text-sm text-blue-600 font-medium">Valor Total</p>
              <p className="text-2xl font-bold text-blue-800">{formatarMoeda(valorTotal)}</p>
            </div>
          </div>
        </div>

        {/* Lista vazia */}
        {comissoes.length === 0 ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
            <svg className="h-16 w-16 text-yellow-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-xl font-semibold text-yellow-800 mb-2">
              Nenhuma comissão encontrada
            </h3>
            <p className="text-yellow-600">
              Não há comissões pendentes para este funcionário no período selecionado.
            </p>
          </div>
        ) : (
          <>
            {/* Tabela de Comissões */}
            <div className="overflow-x-auto mb-6">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Venda
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Data
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Cliente
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Produto
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Qtde
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Base
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      %
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Comissão
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {comissoes.map((comissao) => (
                    <tr key={comissao.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <button
                          onClick={() => handleAbrirVenda(comissao.venda_id)}
                          className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                        >
                          #{comissao.venda_id}
                        </button>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {formatarData(comissao.data_venda)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {comissao.cliente_nome}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        <div className="max-w-xs truncate" title={comissao.nome_produto}>
                          {comissao.nome_produto}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-600">
                        {comissao.quantidade}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatarMoeda(comissao.valor_base_calculo)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                          {comissao.percentual_comissao}%
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-semibold text-green-600">
                        {formatarMoeda(comissao.valor_comissao_gerada)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Rodapé Fixo com Total */}
            <div className="border-t-2 border-gray-300 pt-4 mt-6">
              <div className="flex justify-between items-center">
                <div className="text-lg font-semibold text-gray-700">
                  Total Geral: <span className="text-2xl text-green-600">{formatarMoeda(valorTotal)}</span>
                </div>
                <button
                  onClick={handleAbrirModalFechamento}
                  disabled={comissoes.length === 0}
                  className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-md transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Fechar Comissões
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modal de Fechamento - FUNCIONAL */}
      {mostrarModalFechamento && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-800">Fechar Comissões</h3>
              <button
                onClick={handleFecharModal}
                disabled={loadingFechamento}
                className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Aviso */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="flex items-start">
                <svg className="h-5 w-5 text-blue-600 mt-0.5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-sm text-blue-800 font-medium">
                    Você está prestes a fechar {comissoes.length} comissão(ões)
                  </p>
                  <p className="text-sm text-blue-700 mt-1">
                    Total: {formatarMoeda(valorTotal)}
                  </p>
                </div>
              </div>
            </div>

            {/* Erro */}
            {erroFechamento && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-red-800">{erroFechamento}</p>
              </div>
            )}

            {/* Campos do formulário */}
            <div className="space-y-4 mb-6">
              {/* Data de Pagamento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Data do Pagamento <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={dataPagamento}
                  onChange={(e) => setDataPagamento(e.target.value)}
                  disabled={loadingFechamento}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>

              {/* Observação */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Observação (opcional)
                </label>
                <textarea
                  value={observacaoFechamento}
                  onChange={(e) => setObservacaoFechamento(e.target.value)}
                  disabled={loadingFechamento}
                  rows={3}
                  placeholder="Ex: Pagamento via PIX"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed resize-none"
                />
              </div>
            </div>

            {/* Botões */}
            <div className="flex justify-end gap-3">
              <button
                onClick={handleFecharModal}
                disabled={loadingFechamento}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmarFechamento}
                disabled={!dataPagamento || loadingFechamento}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-md transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
              >
                {loadingFechamento ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Processando...
                  </>
                ) : (
                  <>
                    <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Confirmar Fechamento
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComissoesFechamentoFuncionario;
