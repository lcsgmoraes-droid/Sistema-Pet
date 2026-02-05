/**
 * SPRINT 6 - PASSO 4/5: DETALHES DO FECHAMENTO
 * 
 * Tela de auditoria que exibe os detalhes completos de um fechamento específico.
 * SOMENTE LEITURA - sem possibilidade de edição ou reversão.
 * 
 * Criado em: 22/01/2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../../api';

const ComissoesFechamentoDetalhe = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Parâmetros da URL
  const funcionarioId = searchParams.get('funcionario_id');
  const dataPagamento = searchParams.get('data_pagamento');
  
  // Estados
  const [detalhe, setDetalhe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  // Carregar detalhes ao montar
  useEffect(() => {
    if (!funcionarioId || !dataPagamento) {
      setErro('Parâmetros inválidos: funcionario_id e data_pagamento são obrigatórios');
      setLoading(false);
      return;
    }
    
    carregarDetalhe();
  }, [funcionarioId, dataPagamento]);

  const carregarDetalhe = async () => {
    try {
      setLoading(true);
      setErro(null);
      
      const response = await api.get('/comissoes/fechamentos/detalhe', {
        params: {
          funcionario_id: funcionarioId,
          data_pagamento: dataPagamento
        }
      });
      
      if (response.data.success) {
        setDetalhe(response.data);
      } else {
        setErro('Erro ao carregar detalhes do fechamento');
      }
    } catch (error) {
      console.error('Erro ao carregar detalhes:', error);
      setErro(error.response?.data?.detail || 'Erro ao carregar detalhes do fechamento');
    } finally {
      setLoading(false);
    }
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

  const handleVoltar = () => {
    navigate('/comissoes/fechamentos');
  };

  // Loading
  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white shadow-md rounded-lg p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
            <span className="ml-3 text-gray-600">Carregando detalhes...</span>
          </div>
        </div>
      </div>
    );
  }

  // Erro
  if (erro || !detalhe) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center">
            <svg className="h-6 w-6 text-red-500 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="text-red-800 font-medium">Erro ao carregar dados</h3>
              <p className="text-red-600 text-sm mt-1">{erro || 'Fechamento não encontrado'}</p>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={carregarDetalhe}
              className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors"
            >
              Tentar Novamente
            </button>
            <button
              onClick={handleVoltar}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-md transition-colors"
            >
              Voltar
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { fechamento, comissoes } = detalhe;

  // Tela principal
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white shadow-md rounded-lg p-8">
        {/* Header com botão voltar */}
        <div className="mb-6 border-b border-gray-200 pb-4">
          <button
            onClick={handleVoltar}
            className="mb-4 inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
          >
            <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Voltar
          </button>
          
          <h1 className="text-3xl font-bold text-gray-800">Detalhes do Fechamento</h1>
          <p className="text-gray-600 mt-1">
            Visualização completa das comissões incluídas neste fechamento
          </p>
          
          {/* Badge de SOMENTE LEITURA */}
          <div className="mt-3 inline-flex items-center px-3 py-1 rounded-full bg-yellow-100 border border-yellow-300">
            <svg className="h-4 w-4 text-yellow-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span className="text-sm font-medium text-yellow-800">Somente Leitura - Registro de Auditoria</span>
          </div>
        </div>

        {/* Informações do Fechamento */}
        <div className="mb-6 bg-purple-50 border border-purple-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-purple-800 mb-4">Informações do Fechamento</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Funcionário */}
            <div>
              <p className="text-sm text-gray-600 mb-1">Funcionário</p>
              <div className="flex items-center">
                <div className="flex-shrink-0 h-10 w-10 bg-purple-200 rounded-full flex items-center justify-center">
                  <span className="text-purple-700 font-semibold text-sm">
                    {fechamento.nome_funcionario.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-900">{fechamento.nome_funcionario}</p>
                  <p className="text-xs text-gray-500">ID: {fechamento.funcionario_id}</p>
                </div>
              </div>
            </div>

            {/* Data de Fechamento */}
            <div>
              <p className="text-sm text-gray-600 mb-1">Data do Fechamento</p>
              <p className="text-base font-semibold text-gray-900">{formatarDataHora(fechamento.data_fechamento)}</p>
            </div>

            {/* Data de Pagamento */}
            <div>
              <p className="text-sm text-gray-600 mb-1">Data de Pagamento</p>
              <p className="text-base font-semibold text-gray-900">{formatarData(fechamento.data_pagamento)}</p>
            </div>

            {/* Quantidade */}
            <div>
              <p className="text-sm text-gray-600 mb-1">Quantidade de Comissões</p>
              <p className="text-2xl font-bold text-purple-600">{fechamento.quantidade_comissoes}</p>
            </div>

            {/* Valor Total */}
            <div>
              <p className="text-sm text-gray-600 mb-1">Valor Total</p>
              <p className="text-2xl font-bold text-green-600">{formatarMoeda(fechamento.valor_total)}</p>
            </div>

            {/* Período de Vendas */}
            <div>
              <p className="text-sm text-gray-600 mb-1">Período das Vendas</p>
              <p className="text-base font-semibold text-gray-900">{fechamento.periodo_vendas}</p>
            </div>
          </div>

          {/* Observações */}
          {fechamento.observacao_pagamento && (
            <div className="mt-4 pt-4 border-t border-purple-200">
              <p className="text-sm text-gray-600 mb-1">Observações</p>
              <p className="text-sm text-gray-800 italic">{fechamento.observacao_pagamento}</p>
            </div>
          )}
        </div>

        {/* Tabela de Comissões */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Comissões Incluídas</h2>
          
          {comissoes && comissoes.length > 0 ? (
            <div className="overflow-x-auto border border-gray-200 rounded-lg">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Cliente
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Produto
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Data Venda
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Qtde
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Valor Venda
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      % Comissão
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Comissão
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {comissoes.map((comissao, index) => (
                    <tr key={comissao.id || index} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {comissao.nome_cliente || 'Cliente não identificado'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {comissao.nome_produto || 'Produto não identificado'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center text-sm text-gray-600">
                        {formatarData(comissao.data_venda)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center text-sm text-gray-600">
                        {comissao.quantidade}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatarMoeda(comissao.valor_venda_snapshot)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center text-sm text-gray-600">
                        {comissao.percentual_snapshot}%
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-semibold text-green-600">
                        {formatarMoeda(comissao.valor_comissao)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-gray-50 border-t-2 border-gray-300">
                  <tr>
                    <td colSpan="6" className="px-4 py-3 text-right text-sm font-semibold text-gray-700">
                      TOTAL:
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-base font-bold text-green-700">
                      {formatarMoeda(fechamento.valor_total)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
              <p className="text-yellow-800">Nenhuma comissão encontrada para este fechamento.</p>
            </div>
          )}
        </div>

        {/* Rodapé com informações */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <svg className="h-5 w-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="text-sm font-medium text-blue-800 mb-1">Informações Importantes</h3>
              <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
                <li>Este é um registro imutável de auditoria</li>
                <li>Não é possível editar ou reverter fechamentos realizados</li>
                <li>Os valores foram capturados no momento do fechamento (snapshot)</li>
                <li>Para questões sobre este fechamento, entre em contato com a administração</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComissoesFechamentoDetalhe;
