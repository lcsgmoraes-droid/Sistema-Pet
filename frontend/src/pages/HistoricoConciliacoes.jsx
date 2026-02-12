import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

/**
 * Componente: Histórico de Conciliações
 * 
 * Exibe lista de conciliações já realizadas com filtros e status.
 * Permite consultar quais datas/operadoras já foram processadas.
 */
export default function HistoricoConciliacoes() {
  const navigate = useNavigate();
  const [historico, setHistorico] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filtros, setFiltros] = useState({
    operadora: '',
    status: '',
    data_inicio: '',
    data_fim: ''
  });

  useEffect(() => {
    carregarHistorico();
  }, []);

  const carregarHistorico = async () => {
    setLoading(true);
    try {
      // Construir query params
      const params = new URLSearchParams();
      if (filtros.operadora) params.append('operadora', filtros.operadora);
      if (filtros.status) params.append('status', filtros.status);
      if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
      if (filtros.data_fim) params.append('data_fim', filtros.data_fim);

      const response = await api.get(`/api/conciliacao/historico?${params.toString()}`);
      
      if (response.data && response.data.items) {
        setHistorico(response.data.items);
      }
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatarData = (dataISO) => {
    if (!dataISO) return '-';
    // Usar split para evitar problema de timezone
    const [ano, mes, dia] = dataISO.split('T')[0].split('-');
    return `${dia}/${mes}/${ano}`;
  };

  const formatarDataHora = (dataISO) => {
    if (!dataISO) return '-';
    // Usar split para evitar problema de timezone
    const [ano, mes, dia] = dataISO.split('T')[0].split('-');
    return `${dia}/${mes}/${ano}`;
  };

  const getStatusBadge = (status, item) => {
    // Se Aba 2 concluída, mostrar isso em vez do status geral
    if (item?.abas?.aba2?.concluida && status === 'em_andamento') {
      return (
        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
          ✓ Aba 2 Concluída
        </span>
      );
    }

    const badges = {
      'concluida': { cor: 'bg-green-100 text-green-800', texto: '✓ Concluída' },
      'em_andamento': { cor: 'bg-yellow-100 text-yellow-800', texto: '⏳ Em Andamento' },
      'reprocessada': { cor: 'bg-blue-100 text-blue-800', texto: '↻ Reprocessada' },
      'cancelada': { cor: 'bg-gray-100 text-gray-800', texto: '✕ Cancelada' }
    };

    const badge = badges[status] || { cor: 'bg-gray-100 text-gray-800', texto: status };

    return (
      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${badge.cor}`}>
        {badge.texto}
      </span>
    );
  };

  const getProgressoAbas = (item) => {
    const abas = [
      { nome: 'Aba 1', concluida: item.abas?.aba1?.concluida },
      { nome: 'Aba 2', concluida: item.abas?.aba2?.concluida },
      { nome: 'Aba 3', concluida: item.abas?.aba3?.concluida }
    ];

    return (
      <div className="flex gap-1">
        {abas.map(aba => (
          <div
            key={aba.nome}
            className={`w-20 h-2 rounded ${
              aba.concluida ? 'bg-green-500' : 'bg-gray-300'
            }`}
            title={`${aba.nome}: ${aba.concluida ? 'Concluída' : 'Pendente'}`}
          />
        ))}
      </div>
    );
  };
  const formatarValor = (valor) => {
    if (!valor) return '-';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };
  return (
    <div className="container mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">
              📋 Histórico de Conciliações
            </h1>
            <p className="text-gray-600">
              Consulte todas as conciliações já realizadas
            </p>
          </div>
          
          {/* Botões de Navegação */}
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/financeiro/conciliacao-3abas')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium transition-colors flex items-center gap-2"
              title="Voltar para Conciliação"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              <span>Voltar para Conciliação</span>
            </button>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-4">Filtros</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Operadora
            </label>
            <select
              value={filtros.operadora}
              onChange={(e) => setFiltros({ ...filtros, operadora: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todas</option>
              <option value="Stone">Stone</option>
              <option value="PagSeguro">PagSeguro</option>
              <option value="Rede">Rede</option>
              <option value="Cielo">Cielo</option>
              <option value="Getnet">Getnet</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={filtros.status}
              onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todos</option>
              <option value="concluida">Concluída</option>
              <option value="em_andamento">Em Andamento</option>
              <option value="reprocessada">Reprocessada</option>
              <option value="cancelada">Cancelada</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data Início
            </label>
            <input
              type="date"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({ ...filtros, data_inicio: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data Fim
            </label>
            <input
              type="date"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({ ...filtros, data_fim: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          <button
            onClick={carregarHistorico}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
          >
            🔍 Filtrar
          </button>
          <button
            onClick={() => {
              setFiltros({ operadora: '', status: '', data_inicio: '', data_fim: '' });
              carregarHistorico();
            }}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium"
          >
            ✕ Limpar Filtros
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Tabela de Histórico */}
      {!loading && historico.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {/* Header */}
          <div
            className="text-xs font-semibold text-gray-500 uppercase tracking-wider"
            style={{
              display: 'grid',
              gridTemplateColumns:
                'minmax(48px, 0.6fr) minmax(90px, 1fr) minmax(100px, 1.1fr) minmax(140px, 1.6fr) minmax(120px, 1.4fr) minmax(130px, 1.5fr) minmax(180px, 2.4fr)',
              columnGap: '8px',
              background: '#f9fafb',
              borderBottom: '2px solid #e5e7eb',
            }}
          >
            <span style={{ padding: '8px 10px' }}>ID</span>
            <span style={{ padding: '8px 10px' }}>Data</span>
            <span style={{ padding: '8px 10px' }}>Operadora</span>
            <span style={{ padding: '8px 10px' }}>Status</span>
            <span style={{ padding: '8px 10px', textAlign: 'right' }}>Valor</span>
            <span style={{ padding: '8px 10px' }}>Processado</span>
            <span style={{ padding: '8px 10px' }}>Usuário</span>
          </div>

          {/* Rows */}
          {historico.map((item, idx) => (
            <div
              key={item.id}
              className="hover:bg-blue-50 transition-colors"
              style={{
                display: 'grid',
                gridTemplateColumns:
                  'minmax(48px, 0.6fr) minmax(90px, 1fr) minmax(100px, 1.1fr) minmax(140px, 1.6fr) minmax(120px, 1.4fr) minmax(130px, 1.5fr) minmax(180px, 2.4fr)',
                columnGap: '8px',
                alignItems: 'center',
                borderBottom: '1px solid #f0f0f0',
                background: idx % 2 === 0 ? '#fff' : '#fafbfc',
              }}
            >
              <span style={{ padding: '8px 10px' }} className="text-sm font-mono text-gray-400">#{item.id}</span>
              <span style={{ padding: '8px 10px' }} className="text-sm font-medium text-gray-900">{formatarData(item.data_referencia)}</span>
              <span style={{ padding: '8px 10px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} className="text-sm text-gray-700" title={item.operadora}>{item.operadora}</span>
              <span style={{ padding: '8px 10px' }}>{getStatusBadge(item.status, item)}</span>
              <span style={{ padding: '8px 10px', textAlign: 'right' }}>
                <div className="text-sm font-bold text-gray-900">{formatarValor(item.totais?.recebimentos?.valor_total)}</div>
                {item.totais?.recebimentos?.quantidade && (
                  <div className="text-xs text-gray-400">{item.totais.recebimentos.quantidade} trans.</div>
                )}
              </span>
              <span style={{ padding: '8px 10px' }}>
                <div className="text-sm text-gray-700">{formatarData(item.created_at?.split('T')[0])}</div>
                <div className="text-xs text-gray-400">
                  {item.created_at ? new Date(item.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '-'}
                </div>
              </span>
              <span style={{ padding: '8px 10px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} className="text-sm text-gray-700" title={item.usuario_responsavel}>
                {item.usuario_responsavel || '-'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && historico.length === 0 && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-gray-400 text-6xl mb-4">📋</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Nenhuma conciliação encontrada
          </h3>
          <p className="text-gray-500">
            Não há conciliações registradas com os filtros selecionados.
          </p>
        </div>
      )}
    </div>
  );
}
