/**
 * SPRINT 6 - PASSO 4/5: HISTÓRICO DE FECHAMENTOS
 * 
 * Tela de auditoria que exibe histórico de fechamentos realizados.
 * SOMENTE LEITURA - sem possibilidade de edição ou reversão.
 * 
 * Criado em: 22/01/2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';

const ComissoesHistoricoFechamentos = () => {
  const navigate = useNavigate();
  
  // Estados
  const [fechamentos, setFechamentos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [resumo, setResumo] = useState(null);
  
  // Estados de filtro
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  const [funcionarioId, setFuncionarioId] = useState('');

  // Carregar histórico ao montar componente
  useEffect(() => {
    carregarHistorico();
  }, []);

  const carregarHistorico = async () => {
    try {
      setLoading(true);
      setErro(null);
      
      // Construir query params
      const params = new URLSearchParams();
      if (dataInicio) params.append('data_inicio', dataInicio);
      if (dataFim) params.append('data_fim', dataFim);
      if (funcionarioId) params.append('funcionario_id', funcionarioId);
      
      const url = `/comissoes/fechamentos${params.toString() ? '?' + params.toString() : ''}`;
      const response = await api.get(url);
      
      if (response.data.success) {
        setFechamentos(response.data.fechamentos || []);
        setResumo(response.data.resumo);
      } else {
        setErro('Erro ao carregar histórico');
      }
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
      setErro(error.response?.data?.detail || 'Erro ao carregar histórico de fechamentos');
    } finally {
      setLoading(false);
    }
  };

  const handleAplicarFiltro = () => {
    carregarHistorico();
  };

  const handleLimparFiltro = () => {
    setDataInicio('');
    setDataFim('');
    setFuncionarioId('');
    setTimeout(() => carregarHistorico(), 100);
  };

  const handleVerDetalhes = (fechamento) => {
    // Navegar para tela de detalhes
    navigate(
      `/comissoes/fechamentos/detalhe?funcionario_id=${fechamento.funcionario_id}&data_pagamento=${fechamento.data_pagamento}`
    );
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

  const formatarDataHora = (dataHora) => {
    if (!dataHora) return '-';
    const dataObj = new Date(dataHora);
    return dataObj.toLocaleString('pt-BR');
  };

  // Loading
  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white shadow-md rounded-lg p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600">Carregando histórico...</span>
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
          <button
            onClick={carregarHistorico}
            className="mt-4 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors"
          >
            Tentar Novamente
          </button>
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
          <h1 className="text-3xl font-bold text-gray-800">Histórico de Fechamentos</h1>
          <p className="text-gray-600 mt-1">
            Auditoria de comissões fechadas - somente leitura
          </p>
        </div>

        {/* Filtros */}
        <div className="mb-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Filtros</h3>
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[180px]">
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
            <div className="flex-1 min-w-[180px]">
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
            <div className="flex-1 min-w-[180px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ID do Funcionário
              </label>
              <input
                type="number"
                value={funcionarioId}
                onChange={(e) => setFuncionarioId(e.target.value)}
                placeholder="Deixe vazio para todos"
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

        {/* Resumo Geral */}
        {resumo && (
          <div className="mb-6 bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-purple-600 font-medium">Total de Fechamentos</p>
                <p className="text-2xl font-bold text-purple-800">{resumo.total_fechamentos}</p>
              </div>
              <div>
                <p className="text-sm text-purple-600 font-medium">Valor Total Pago</p>
                <p className="text-2xl font-bold text-purple-800">
                  {formatarMoeda(resumo.valor_total_geral)}
                </p>
              </div>
              <div>
                <p className="text-sm text-purple-600 font-medium">Total de Comissões</p>
                <p className="text-2xl font-bold text-purple-800">{resumo.quantidade_total_geral}</p>
              </div>
            </div>
          </div>
        )}

        {/* Lista vazia */}
        {fechamentos.length === 0 ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
            <svg className="h-16 w-16 text-yellow-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-xl font-semibold text-yellow-800 mb-2">
              Nenhum fechamento encontrado
            </h3>
            <p className="text-yellow-600">
              Não há fechamentos registrados no período selecionado.
            </p>
          </div>
        ) : (
          <>
            {/* Tabela de Fechamentos */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Funcionário
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Data Fechamento
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Data Pagamento
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Qtde
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Valor Total
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Ação
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {fechamentos.map((fechamento, index) => (
                    <tr 
                      key={`${fechamento.funcionario_id}_${fechamento.data_pagamento}_${index}`}
                      className="hover:bg-gray-50 transition-colors cursor-pointer"
                      onClick={() => handleVerDetalhes(fechamento)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10 bg-purple-100 rounded-full flex items-center justify-center">
                            <span className="text-purple-600 font-semibold text-sm">
                              {fechamento.nome_funcionario.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div className="ml-3">
                            <div className="text-sm font-medium text-gray-900">
                              {fechamento.nome_funcionario}
                            </div>
                            <div className="text-sm text-gray-500">
                              ID: {fechamento.funcionario_id}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center text-sm text-gray-600">
                        {formatarDataHora(fechamento.data_fechamento)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center text-sm font-medium text-gray-900">
                        {formatarData(fechamento.data_pagamento)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
                          {fechamento.quantidade_comissoes}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-semibold text-green-600">
                        {formatarMoeda(fechamento.valor_total)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleVerDetalhes(fechamento);
                          }}
                          className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
                        >
                          Ver Detalhes
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Rodapé com info */}
            <div className="mt-6 pt-4 border-t border-gray-200">
              <p className="text-sm text-gray-500 text-center">
                💡 Clique em uma linha para ver os detalhes do fechamento
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ComissoesHistoricoFechamentos;
