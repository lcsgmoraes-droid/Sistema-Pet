/**
 * SPRINT 6 - PASSO 1/5: COMISSÕES EM ABERTO
 * 
 * Tela inicial do fluxo de fechamento de comissões.
 * Lista funcionários com comissões pendentes e resumo financeiro.
 * 
 * Criado em: 22/01/2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';

const ComissoesAbertas = () => {
  const navigate = useNavigate();
  
  // Estados
  const [funcionarios, setFuncionarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  // Carregar funcionários com comissões em aberto
  useEffect(() => {
    carregarComissoesAbertas();
  }, []);

  const carregarComissoesAbertas = async () => {
    try {
      setLoading(true);
      setErro(null);
      
      const response = await api.get('/comissoes/abertas');
      
      if (response.data.success) {
        setFuncionarios(response.data.funcionarios || []);
      } else {
        setErro('Erro ao carregar comissões em aberto');
      }
    } catch (error) {
      console.error('Erro ao carregar comissões abertas:', error);
      setErro(error.response?.data?.detail || 'Erro ao carregar comissões em aberto');
    } finally {
      setLoading(false);
    }
  };

  const handleConferir = (funcionarioId) => {
    navigate(`/comissoes/fechamento/${funcionarioId}`);
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
            <span className="ml-3 text-gray-600">Carregando comissões em aberto...</span>
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
            onClick={carregarComissoesAbertas}
            className="mt-4 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors"
          >
            Tentar Novamente
          </button>
        </div>
      </div>
    );
  }

  // Lista vazia
  if (funcionarios.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white shadow-md rounded-lg p-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Comissões em Aberto</h1>
          
          <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
            <svg className="h-16 w-16 text-green-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-xl font-semibold text-green-800 mb-2">
              Nenhuma comissão pendente
            </h3>
            <p className="text-green-600">
              Não há funcionários com comissões em aberto no momento.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Tabela com funcionários
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white shadow-md rounded-lg p-8">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Comissões em Aberto</h1>
            <p className="text-gray-600">
              Funcionários com comissões pendentes de pagamento
            </p>
          </div>
          <button
            onClick={() => navigate('/comissoes/fechamentos')}
            className="inline-flex items-center px-4 py-2 border border-purple-300 rounded-md shadow-sm text-sm font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
          >
            <svg className="mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Ver Histórico
          </button>
        </div>

        {/* Resumo Geral */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-600 font-medium">Total de Funcionários</p>
              <p className="text-2xl font-bold text-blue-800">{funcionarios.length}</p>
            </div>
            <div>
              <p className="text-sm text-blue-600 font-medium">Total Pendente</p>
              <p className="text-2xl font-bold text-blue-800">
                {formatarMoeda(
                  funcionarios.reduce((acc, f) => acc + f.total_pendente, 0)
                )}
              </p>
            </div>
            <div>
              <p className="text-sm text-blue-600 font-medium">Total de Comissões</p>
              <p className="text-2xl font-bold text-blue-800">
                {funcionarios.reduce((acc, f) => acc + f.quantidade_comissoes, 0)}
              </p>
            </div>
          </div>
        </div>

        {/* Tabela */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Funcionário
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Pendente
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Qtde de Comissões
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Última Venda
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ação
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {funcionarios.map((funcionario) => (
                <tr key={funcionario.funcionario_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 font-semibold text-sm">
                          {funcionario.nome_funcionario.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {funcionario.nome_funcionario}
                        </div>
                        <div className="text-sm text-gray-500">
                          ID: {funcionario.funcionario_id}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="text-sm font-semibold text-green-600">
                      {formatarMoeda(funcionario.total_pendente)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                      {funcionario.quantidade_comissoes}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    {formatarData(funcionario.data_ultima_venda)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <button
                      onClick={() => handleConferir(funcionario.funcionario_id)}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                    >
                      <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      Conferir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Rodapé */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-500 text-center">
            Clique em "Conferir" para visualizar os detalhes das comissões de cada funcionário
          </p>
        </div>
      </div>
    </div>
  );
};

export default ComissoesAbertas;
