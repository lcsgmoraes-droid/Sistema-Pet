/**
 * Relatório de Movimentações de Estoque
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  getRelatorioMovimentacoes,
  getProdutos,
  formatarMoeda,
  formatarData,
  formatarDataHora
} from '../api/produtos';

export default function ProdutosRelatorio() {
  const navigate = useNavigate();
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totais, setTotais] = useState({
    totalEntradas: 0,
    totalSaidas: 0,
    valorTotal: 0
  });

  // Filtros
  const [filtros, setFiltros] = useState({
    data_inicio: getDataInicio('mes'),
    data_fim: getDataFim(),
    produto_id: '',
    tipo_movimentacao: '',
  });

  // Período selecionado
  const [periodoSelecionado, setPeriodoSelecionado] = useState('mes');

  useEffect(() => {
    carregarProdutos();
  }, []);

  useEffect(() => {
    carregarRelatorio();
  }, [filtros]);

  // Funções auxiliares de data
  function getDataInicio(periodo) {
    const hoje = new Date();
    const data = new Date(hoje);
    
    switch (periodo) {
      case 'mes':
        data.setDate(1);
        break;
      case '3meses':
        data.setMonth(hoje.getMonth() - 3);
        break;
      case '6meses':
        data.setMonth(hoje.getMonth() - 6);
        break;
      case 'ano':
        data.setMonth(0);
        data.setDate(1);
        break;
      default:
        return '';
    }
    
    return data.toISOString().split('T')[0];
  }

  function getDataFim() {
    return new Date().toISOString().split('T')[0];
  }

  const carregarProdutos = async () => {
    try {
      const response = await getProdutos();
      // Garantir que sempre seja um array
      if (Array.isArray(response.data)) {
        setProdutos(response.data);
      } else {
        console.warn('Resposta de produtos não é um array:', response.data);
        setProdutos([]);
      }
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
      setProdutos([]); // Garantir array vazio em caso de erro
    }
  };

  const carregarRelatorio = async () => {
    try {
      setLoading(true);
      const response = await getRelatorioMovimentacoes(filtros);
      const dados = response.data;
      
      // Garantir que dados seja sempre um array
      if (Array.isArray(dados)) {
        setMovimentacoes(dados);
        
        // Calcular totais
        const totais = dados.reduce((acc, mov) => {
          acc.totalEntradas += mov.quantidade_entrada || 0;
          acc.totalSaidas += mov.quantidade_saida || 0;
          acc.valorTotal += mov.valor_total || 0;
          return acc;
        }, { totalEntradas: 0, totalSaidas: 0, valorTotal: 0 });
        
        setTotais(totais);
      } else {
        console.warn('Resposta de movimentações não é um array:', dados);
        setMovimentacoes([]);
      }
    } catch (error) {
      console.error('Erro ao carregar relatório:', error);
      console.error('Detalhes do erro:', error.response?.data);
      alert(`Erro ao carregar relatório: ${error.response?.data?.detail || error.message}`);
      setMovimentacoes([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodoChange = (periodo) => {
    setPeriodoSelecionado(periodo);
    if (periodo === 'personalizado') {
      // Não altera as datas, deixa o usuário escolher
    } else {
      setFiltros({
        ...filtros,
        data_inicio: getDataInicio(periodo),
        data_fim: getDataFim(),
      });
    }
  };

  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({ ...prev, [campo]: valor }));
  };

  const exportarExcel = () => {
    // Criar CSV
    const headers = ['Data', 'Produto', 'Código', 'Entrada', 'Saída', 'Estoque', 'Tipo', 'Valor', 'Usuário', 'Nº Pedido', 'Lançamento'];
    const rows = movimentacoes.map(mov => [
      formatarData(mov.data_movimentacao),
      mov.produto_nome || '',
      mov.produto_codigo || '',
      mov.quantidade_entrada || 0,
      mov.quantidade_saida || 0,
      mov.estoque_atual || 0,
      mov.tipo_movimentacao || '',
      formatarMoeda(mov.valor_total || 0),
      mov.usuario_nome || '',
      mov.numero_pedido || '',
      formatarDataHora(mov.data_criacao),
    ]);

    let csv = headers.join(';') + '\n';
    rows.forEach(row => {
      csv += row.join(';') + '\n';
    });

    // Download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `relatorio_movimentacoes_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  // Agrupar por mês
  const movimentacoesPorMes = movimentacoes.reduce((acc, mov) => {
    const data = new Date(mov.data_movimentacao);
    const mesAno = data.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });
    
    if (!acc[mesAno]) {
      acc[mesAno] = [];
    }
    acc[mesAno].push(mov);
    
    return acc;
  }, {});

  const getTipoBadge = (tipo) => {
    const cores = {
      entrada: 'bg-green-100 text-green-800',
      saida: 'bg-red-100 text-red-800',
      ajuste: 'bg-yellow-100 text-yellow-800',
      transferencia: 'bg-blue-100 text-blue-800',
    };
    
    return cores[tipo] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Relatório de Movimentações</h1>
          <p className="text-gray-600 mt-1">Histórico completo de entradas e saídas de estoque</p>
        </div>
        <button
          onClick={() => navigate('/produtos')}
          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Voltar
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="space-y-4">
          {/* Linha 1: Período */}
          <div className="flex gap-2 flex-wrap">
            {[
              { label: 'Último Mês', value: 'mes' },
              { label: '3 Meses', value: '3meses' },
              { label: '6 Meses', value: '6meses' },
              { label: 'Este Ano', value: 'ano' },
              { label: 'Personalizado', value: 'personalizado' },
            ].map((periodo) => (
              <button
                key={periodo.value}
                onClick={() => handlePeriodoChange(periodo.value)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  periodoSelecionado === periodo.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {periodo.label}
              </button>
            ))}
          </div>

          {/* Linha 2: Filtros Detalhados */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Início
              </label>
              <input
                type="date"
                value={filtros.data_inicio}
                onChange={(e) => handleFiltroChange('data_inicio', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Fim
              </label>
              <input
                type="date"
                value={filtros.data_fim}
                onChange={(e) => handleFiltroChange('data_fim', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Produto
              </label>
              <select
                value={filtros.produto_id}
                onChange={(e) => handleFiltroChange('produto_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Todos os Produtos</option>
                {produtos.map(prod => (
                  <option key={prod.id} value={prod.id}>
                    {prod.codigo || prod.sku} - {prod.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo
              </label>
              <select
                value={filtros.tipo_movimentacao}
                onChange={(e) => handleFiltroChange('tipo_movimentacao', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Todos os Tipos</option>
                <option value="entrada">Entrada</option>
                <option value="saida">Saída</option>
                <option value="ajuste">Ajuste</option>
                <option value="transferencia">Transferência</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Cards de Totais */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total de Entradas</p>
              <p className="text-2xl font-bold text-green-600">{totais.totalEntradas.toFixed(2)}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total de Saídas</p>
              <p className="text-2xl font-bold text-red-600">{totais.totalSaidas.toFixed(2)}</p>
            </div>
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 13l-5 5m0 0l-5-5m5 5V6" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Valor Total</p>
              <p className="text-2xl font-bold text-blue-600">{formatarMoeda(totais.valorTotal)}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Botão Exportar */}
      <div className="mb-4 flex justify-end">
        <button
          onClick={exportarExcel}
          disabled={movimentacoes.length === 0}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:bg-gray-400 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Exportar CSV
        </button>
      </div>

      {/* Tabela de Movimentações */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Carregando relatório...</div>
        ) : movimentacoes.length === 0 ? (
          <div className="p-8 text-center text-gray-500">Nenhuma movimentação encontrada no período selecionado</div>
        ) : (
          <div className="overflow-x-auto">
            {Object.entries(movimentacoesPorMes).map(([mesAno, movs]) => (
              <div key={mesAno}>
                {/* Cabeçalho do Mês */}
                <div className="bg-gray-100 px-4 py-2 font-semibold text-gray-700 border-b border-gray-200">
                  {mesAno.charAt(0).toUpperCase() + mesAno.slice(1)} ({movs.length} movimentações)
                </div>

                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produto</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Código</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Entrada</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Saída</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Estoque</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Valor</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usuário</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Nº Pedido</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {movs.map((mov, idx) => (
                      <tr key={idx} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                          {formatarData(mov.data_movimentacao)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {mov.produto_nome || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-center text-gray-700 font-mono">
                          {mov.produto_codigo || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-right font-semibold text-green-600">
                          {mov.quantidade_entrada > 0 ? mov.quantidade_entrada : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-right font-semibold text-red-600">
                          {mov.quantidade_saida > 0 ? mov.quantidade_saida : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">
                          {mov.estoque_atual || 0}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTipoBadge(mov.tipo_movimentacao)}`}>
                            {mov.tipo_movimentacao}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">
                          {formatarMoeda(mov.valor_total || 0)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700">
                          {mov.usuario_nome || '-'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {mov.numero_pedido ? (
                            <button
                              className="text-blue-600 hover:text-blue-800 underline font-mono text-sm"
                              title="Clique para ver o pedido"
                            >
                              #{mov.numero_pedido}
                            </button>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}

        {/* Footer com Total */}
        {!loading && movimentacoes.length > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              Total: {movimentacoes.length} movimentações no período
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
