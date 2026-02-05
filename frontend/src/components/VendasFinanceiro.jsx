import { useState, useEffect } from 'react';
import api from '../api';
import { Calendar, DollarSign, TrendingUp, Package, Users, CreditCard, Filter, ChevronDown, ChevronRight, Download, FileText, BarChart3, ArrowUp, ArrowDown, Minus } from 'lucide-react';
import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';

export default function VendasFinanceiro() {
  const [loading, setLoading] = useState(false);
  const [abaAtiva, setAbaAtiva] = useState('resumo');
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  const [filtroSelecionado, setFiltroSelecionado] = useState('');
  const [modoComparacao, setModoComparacao] = useState(false);
  const [periodoComparacao, setPeriodoComparacao] = useState('mes_anterior');
  
  // Filtros avançados
  const [filtroFuncionario, setFiltroFuncionario] = useState('');
  const [filtroFormaPagamento, setFiltroFormaPagamento] = useState('');
  const [filtroCategoria, setFiltroCategoria] = useState('');
  const [mostrarGraficos, setMostrarGraficos] = useState(true);
  const [tipoComparacao, setTipoComparacao] = useState('financeiro'); // financeiro, formas_pagamento, produtos, funcionarios
  
  // Estados dos dados
  const [resumo, setResumo] = useState({
    venda_bruta: 0,
    taxa_entrega: 0,
    desconto: 0,
    venda_liquida: 0,
    em_aberto: 0,
    quantidade_vendas: 0
  });
  
  const [resumoComparacao, setResumoComparacao] = useState({
    venda_bruta: 0,
    taxa_entrega: 0,
    desconto: 0,
    venda_liquida: 0,
    em_aberto: 0,
    quantidade_vendas: 0
  });
  
  const [vendasPorData, setVendasPorData] = useState([]);
  const [formasRecebimento, setFormasRecebimento] = useState([]);
  const [vendasPorFuncionario, setVendasPorFuncionario] = useState([]);
  const [vendasPorTipo, setVendasPorTipo] = useState([]);
  const [vendasPorGrupo, setVendasPorGrupo] = useState([]);
  const [produtosDetalhados, setProdutosDetalhados] = useState([]);
  const [listaVendas, setListaVendas] = useState([]);
  const [vendasExpandidas, setVendasExpandidas] = useState(new Set());
  
  // Dados de comparação estendidos
  const [formasRecebimentoComparacao, setFormasRecebimentoComparacao] = useState([]);
  const [vendasPorGrupoComparacao, setVendasPorGrupoComparacao] = useState([]);
  const [vendasPorFuncionarioComparacao, setVendasPorFuncionarioComparacao] = useState([]);

  const toggleVendaExpandida = (vendaId) => {
    const novoSet = new Set(vendasExpandidas);
    if (novoSet.has(vendaId)) {
      novoSet.delete(vendaId);
    } else {
      novoSet.add(vendaId);
    }
    setVendasExpandidas(novoSet);
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  const formatarData = (dataStr) => {
    if (!dataStr) return '';
    // Parse manual para evitar problemas de timezone
    const [ano, mes, dia] = dataStr.split('-').map(Number);
    const data = new Date(ano, mes - 1, dia);
    return data.toLocaleDateString('pt-BR');
  };

  const CORES_GRAFICOS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'];

  // Funções de filtragem
  const aplicarFiltros = (dados, tipo) => {
    if (!dados || dados.length === 0) return dados;

    let dadosFiltrados = [...dados];

    // Filtro por funcionário
    if (filtroFuncionario && tipo === 'funcionario') {
      dadosFiltrados = dadosFiltrados.filter(item => item.funcionario === filtroFuncionario);
    }

    // Filtro por forma de pagamento
    if (filtroFormaPagamento && tipo === 'formaPagamento') {
      dadosFiltrados = dadosFiltrados.filter(item => item.forma_pagamento === filtroFormaPagamento);
    }

    // Filtro por categoria
    if (filtroCategoria && tipo === 'categoria') {
      dadosFiltrados = dadosFiltrados.filter(item => item.categoria === filtroCategoria);
    }

    return dadosFiltrados;
  };

  const vendasPorDataFiltradas = vendasPorData;
  const formasRecebimentoFiltradas = aplicarFiltros(formasRecebimento, 'formaPagamento');
  const vendasPorFuncionarioFiltradas = aplicarFiltros(vendasPorFuncionario, 'funcionario');
  const produtosDetalhadosFiltrados = aplicarFiltros(produtosDetalhados, 'categoria');

  const CardComVariacao = ({ titulo, valor, icone: Icone, cor, valorAnterior }) => {
    const variacao = calcularVariacao(valor, valorAnterior);
    const cresceu = variacao.percentual > 0;
    const manteve = variacao.percentual === 0;

    return (
      <div className={`${cor} text-white p-4 rounded-lg shadow`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm opacity-90">{titulo}</span>
          <Icone className="w-5 h-5 opacity-80" />
        </div>
        <div className="text-3xl font-bold mb-1">{formatarMoeda(valor)}</div>
        {modoComparacao && valorAnterior !== undefined && (
          <div className={`flex items-center gap-1 text-sm ${manteve ? 'opacity-70' : ''}`}>
            {cresceu && <ArrowUp className="w-4 h-4" />}
            {!cresceu && !manteve && <ArrowDown className="w-4 h-4" />}
            {manteve && <Minus className="w-4 h-4" />}
            <span>{Math.abs(variacao.percentual)}%</span>
          </div>
        )}
      </div>
    );
  };

  const getTextoComparacao = () => {
    switch (periodoComparacao) {
      case 'periodo_anterior':
        return 'mesmo período anterior';
      case 'mes_anterior':
        return 'mesmo período do mês anterior';
      case 'ano_anterior':
        return 'mesmo período do ano anterior';
      default:
        return 'período anterior';
    }
  };

  const exportarParaPDF = async () => {
    if (!dataInicio || !dataFim) {
      toast.error('Selecione um período para gerar o relatório');
      return;
    }

    try {
      toast.loading('Gerando PDF...', { id: 'pdf' });
      
      const params = new URLSearchParams({
        data_inicio: dataInicio,
        data_fim: dataFim,
      });

      if (filtroFuncionario) params.append('funcionario', filtroFuncionario);
      if (filtroFormaPagamento) params.append('forma_pagamento', filtroFormaPagamento);
      if (filtroCategoria) params.append('categoria', filtroCategoria);

      const response = await api.get(`/relatorios/vendas/export/pdf?${params.toString()}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `relatorio_vendas_${dataInicio}_${dataFim}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('📄 PDF exportado com sucesso!', { id: 'pdf' });
    } catch (error) {
      console.error('Erro ao exportar PDF:', error);
      toast.error('Erro ao exportar PDF', { id: 'pdf' });
    }
  };

  const exportarParaExcel = () => {
    const wb = XLSX.utils.book_new();

    // Aba Resumo
    const resumoData = [
      ['RELATÓRIO DE VENDAS'],
      ['Período:', `${formatarData(dataInicio)} até ${formatarData(dataFim)}`],
      [''],
      ['Métrica', 'Valor'],
      ['Venda Bruta', resumo.venda_bruta],
      ['Taxa de Entrega', resumo.taxa_entrega],
      ['Desconto', resumo.desconto],
      ['Venda Líquida', resumo.venda_liquida],
      ['Em Aberto', resumo.em_aberto],
      ['Quantidade de Vendas', resumo.quantidade_vendas]
    ];
    const wsResumo = XLSX.utils.aoa_to_sheet(resumoData);
    XLSX.utils.book_append_sheet(wb, wsResumo, 'Resumo');

    // Aba Vendas por Data
    if (vendasPorData.length > 0) {
      const vendasData = [
        ['Data', 'Qtd', 'Tkt. Médio', 'Vl. bruto', 'Taxa entrega', 'Desconto', '(%)', 'Vl. líquido', 'Vl. recebido', 'Saldo aberto'],
        ...vendasPorData.map(v => [
          formatarData(v.data), v.quantidade, v.ticket_medio, v.valor_bruto, 
          v.taxa_entrega, v.desconto, v.percentual_desconto, v.valor_liquido, 
          v.valor_recebido, v.saldo_aberto
        ])
      ];
      const wsVendas = XLSX.utils.aoa_to_sheet(vendasData);
      XLSX.utils.book_append_sheet(wb, wsVendas, 'Vendas por Data');
    }

    // Aba Formas de Recebimento
    if (formasRecebimentoFiltradas.length > 0) {
      const formasData = [
        ['Forma', 'Valor pago'],
        ...formasRecebimentoFiltradas.map(f => [f.forma_pagamento, f.valor_total])
      ];
      const wsFormas = XLSX.utils.aoa_to_sheet(formasData);
      XLSX.utils.book_append_sheet(wb, wsFormas, 'Formas Pagamento');
    }

    // Gerar arquivo
    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'binary' });
    const buf = new ArrayBuffer(wbout.length);
    const view = new Uint8Array(buf);
    for (let i = 0; i < wbout.length; i++) view[i] = wbout.charCodeAt(i) & 0xFF;
    const fileName = `relatorio_vendas_${dataInicio}_${dataFim}.xlsx`;
    saveAs(new Blob([buf], { type: 'application/octet-stream' }), fileName);
  };

  const aplicarFiltroRapido = (filtro) => {
    // Obter data atual sem conversão de timezone
    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = String(agora.getMonth() + 1).padStart(2, '0');
    const dia = String(agora.getDate()).padStart(2, '0');
    const hoje = `${ano}-${mes}-${dia}`;
    
    let inicio, fim;

    switch (filtro) {
      case 'hoje':
        inicio = fim = hoje;
        break;
      case 'ontem':
        const dataOntem = new Date(agora);
        dataOntem.setDate(agora.getDate() - 1);
        const anoOntem = dataOntem.getFullYear();
        const mesOntem = String(dataOntem.getMonth() + 1).padStart(2, '0');
        const diaOntem = String(dataOntem.getDate()).padStart(2, '0');
        inicio = fim = `${anoOntem}-${mesOntem}-${diaOntem}`;
        break;
      case 'esta_semana':
        const diaSemana = agora.getDay(); // 0=domingo, 1=segunda, ..., 6=sábado
        const diasDesdeSegunda = diaSemana === 0 ? 6 : diaSemana - 1; // Se domingo, volta 6 dias; senão volta (dia-1)
        const primeiroDia = new Date(agora);
        primeiroDia.setDate(agora.getDate() - diasDesdeSegunda);
        const anoPri = primeiroDia.getFullYear();
        const mesPri = String(primeiroDia.getMonth() + 1).padStart(2, '0');
        const diaPri = String(primeiroDia.getDate()).padStart(2, '0');
        inicio = `${anoPri}-${mesPri}-${diaPri}`;
        fim = hoje;
        break;
      case 'este_mes':
        inicio = `${ano}-${mes}-01`;
        fim = hoje;
        break;
      case 'mes_anterior':
        const mesPassado = new Date(agora.getFullYear(), agora.getMonth() - 1, 1);
        const ultimoDia = new Date(agora.getFullYear(), agora.getMonth(), 0);
        const anoMesPass = mesPassado.getFullYear();
        const numeroMesPass = String(mesPassado.getMonth() + 1).padStart(2, '0');
        const anoUltDia = ultimoDia.getFullYear();
        const mesUltDia = String(ultimoDia.getMonth() + 1).padStart(2, '0');
        const diaUltDia = String(ultimoDia.getDate()).padStart(2, '0');
        inicio = `${anoMesPass}-${numeroMesPass}-01`;
        fim = `${anoUltDia}-${mesUltDia}-${diaUltDia}`;
        break;
      case 'ultimos_7_dias':
        const sete = new Date(agora);
        sete.setDate(agora.getDate() - 7);
        const anoSete = sete.getFullYear();
        const mesSete = String(sete.getMonth() + 1).padStart(2, '0');
        const diaSete = String(sete.getDate()).padStart(2, '0');
        inicio = `${anoSete}-${mesSete}-${diaSete}`;
        fim = hoje;
        break;
      case 'ultimos_30_dias':
        const trinta = new Date(agora);
        trinta.setDate(agora.getDate() - 30);
        const anoTrinta = trinta.getFullYear();
        const mesTrinta = String(trinta.getMonth() + 1).padStart(2, '0');
        const diaTrinta = String(trinta.getDate()).padStart(2, '0');
        inicio = `${anoTrinta}-${mesTrinta}-${diaTrinta}`;
        fim = hoje;
        break;
      case 'este_ano':
        inicio = `${ano}-01-01`;
        fim = hoje;
        break;
      default:
        return;
    }

    setDataInicio(inicio);
    setDataFim(fim);
    setFiltroSelecionado(filtro);
  };

  const calcularPeriodoComparacao = () => {
    // Parse manual das datas para evitar problemas de timezone
    const [anoIni, mesIni, diaIni] = dataInicio.split('-').map(Number);
    const [anoFim, mesFim, diaFim] = dataFim.split('-').map(Number);
    
    const inicio = new Date(anoIni, mesIni - 1, diaIni);
    const fim = new Date(anoFim, mesFim - 1, diaFim);
    const diffDias = Math.floor((fim - inicio) / (1000 * 60 * 60 * 24)) + 1;

    let inicioComp, fimComp;

    switch (periodoComparacao) {
      case 'periodo_anterior':
        inicioComp = new Date(inicio);
        inicioComp.setDate(inicio.getDate() - diffDias);
        fimComp = new Date(inicio);
        fimComp.setDate(inicio.getDate() - 1);
        break;
      case 'mes_anterior':
        inicioComp = new Date(inicio);
        inicioComp.setMonth(inicio.getMonth() - 1);
        fimComp = new Date(fim);
        fimComp.setMonth(fim.getMonth() - 1);
        break;
      case 'ano_anterior':
        inicioComp = new Date(inicio);
        inicioComp.setFullYear(inicio.getFullYear() - 1);
        fimComp = new Date(fim);
        fimComp.setFullYear(fim.getFullYear() - 1);
        break;
      default:
        return { data_inicio: '', data_fim: '' };
    }

    // Formatar manualmente para evitar problemas de timezone
    const anoIniComp = inicioComp.getFullYear();
    const mesIniComp = String(inicioComp.getMonth() + 1).padStart(2, '0');
    const diaIniComp = String(inicioComp.getDate()).padStart(2, '0');
    
    const anoFimComp = fimComp.getFullYear();
    const mesFimComp = String(fimComp.getMonth() + 1).padStart(2, '0');
    const diaFimComp = String(fimComp.getDate()).padStart(2, '0');

    return {
      data_inicio: `${anoIniComp}-${mesIniComp}-${diaIniComp}`,
      data_fim: `${anoFimComp}-${mesFimComp}-${diaFimComp}`
    };
  };

  const calcularVariacao = (valorAtual, valorAnterior) => {
    if (!valorAnterior || valorAnterior === 0) return { valor: 0, percentual: 0 };
    const diff = valorAtual - valorAnterior;
    const perc = ((diff / valorAnterior) * 100).toFixed(1);
    return { valor: diff, percentual: parseFloat(perc) };
  };

  const carregarDados = async () => {
    if (!dataInicio || !dataFim) return;
    
    setLoading(true);

    try {
      const response = await api.get('/relatorios/vendas/relatorio', {
        params: { data_inicio: dataInicio, data_fim: dataFim }
      });
      const data = response.data;

      setResumo(data.resumo || {});
      setVendasPorData(data.vendas_por_data || []);
      setFormasRecebimento(data.formas_recebimento || []);
      setVendasPorFuncionario(data.vendas_por_funcionario || []);
      setVendasPorTipo(data.vendas_por_tipo || []);
      setVendasPorGrupo(data.vendas_por_grupo || []);
      setProdutosDetalhados(data.produtos_detalhados || []);
      setListaVendas(data.lista_vendas || []);

      if (modoComparacao || abaAtiva === 'comparacao') {
        const periodoComp = calcularPeriodoComparacao();
        const responseComp = await api.get('/relatorios/vendas/relatorio', {
          params: periodoComp
        });
        setResumoComparacao(responseComp.data.resumo || {});
        setFormasRecebimentoComparacao(responseComp.data.formas_recebimento || []);
        setVendasPorGrupoComparacao(responseComp.data.vendas_por_grupo || []);
        setVendasPorFuncionarioComparacao(responseComp.data.vendas_por_funcionario || []);
      } else {
        // Limpar dados de comparação quando desativado
        setResumoComparacao({
          venda_bruta: 0,
          taxa_entrega: 0,
          desconto: 0,
          venda_liquida: 0,
          em_aberto: 0,
          quantidade_vendas: 0
        });
      }
    } catch (error) {
      console.error('Erro ao carregar relatório:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarDados();
  }, [dataInicio, dataFim, modoComparacao, periodoComparacao, abaAtiva]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Cabeçalho com Filtros */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-800">Consulta de Vendas</h1>
          
          <div className="flex items-center gap-4">
            {/* Botão Exportar PDF */}
            <button
              onClick={exportarParaPDF}
              disabled={!dataInicio || !dataFim}
              title={dataInicio && dataFim ? `Exportar PDF de ${formatarData(dataInicio)} até ${formatarData(dataFim)}` : 'Selecione um período'}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <FileText className="w-4 h-4" />
              <div className="flex flex-col items-start">
                <span className="font-medium">Exportar PDF</span>
                {dataInicio && dataFim && (
                  <span className="text-xs opacity-90">({formatarData(dataInicio)} - {formatarData(dataFim)})</span>
                )}
              </div>
            </button>

            {/* Botão Exportar Excel */}
            <button
              onClick={exportarParaExcel}
              disabled={!dataInicio || !dataFim}
              title={dataInicio && dataFim ? `Exportar dados de ${formatarData(dataInicio)} até ${formatarData(dataFim)}` : 'Selecione um período'}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              <div className="flex flex-col items-start">
                <span className="font-medium">Exportar Excel</span>
                {dataInicio && dataFim && (
                  <span className="text-xs opacity-90">({formatarData(dataInicio)} - {formatarData(dataFim)})</span>
                )}
              </div>
            </button>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={modoComparacao}
                onChange={(e) => setModoComparacao(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm font-medium text-gray-700">Comparar com:</span>
            </label>
            
            {modoComparacao && (
              <select
                value={periodoComparacao}
                onChange={(e) => setPeriodoComparacao(e.target.value)}
                className="border rounded px-3 py-2 text-sm bg-blue-50 font-medium"
              >
                <option value="periodo_anterior">Período imediatamente anterior (mesmo nº de dias)</option>
                <option value="mes_anterior">Mesmo período do mês passado</option>
                <option value="ano_anterior">Mesmo período do ano passado</option>
              </select>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          {[
            { id: 'hoje', label: 'Hoje' },
            { id: 'ontem', label: 'Ontem' },
            { id: 'esta_semana', label: 'Esta semana' },
            { id: 'este_mes', label: 'Este mês' },
            { id: 'mes_anterior', label: 'Mês anterior' },
            { id: 'ultimos_7_dias', label: 'Últimos 7 dias' },
            { id: 'ultimos_30_dias', label: 'Últimos 30 dias' },
            { id: 'este_ano', label: 'Este ano' },
            { id: 'personalizado', label: 'Personalizado' }
          ].map(filtro => (
            <button
              key={filtro.id}
              onClick={() => {
                if (filtro.id === 'personalizado') {
                  setFiltroSelecionado('personalizado');
                } else {
                  aplicarFiltroRapido(filtro.id);
                }
              }}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                filtroSelecionado === filtro.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {filtro.label}
            </button>
          ))}
        </div>

        {filtroSelecionado === 'personalizado' && (
          <div className="flex gap-2 items-center mb-4 p-3 bg-gray-50 rounded">
            <Calendar className="w-5 h-5 text-gray-500" />
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="border rounded px-3 py-2"
            />
            <span className="text-gray-600">até</span>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="border rounded px-3 py-2"
            />
          </div>
        )}

        {/* Filtros Avançados */}
        <div className="flex gap-2 items-center mb-4 p-3 bg-blue-50 rounded border border-blue-200">
          <Filter className="w-5 h-5 text-blue-600" />
          <span className="text-sm font-medium text-gray-700">Filtros Avançados:</span>
          
          <select
            value={filtroFuncionario}
            onChange={(e) => setFiltroFuncionario(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todos os funcionários</option>
            {vendasPorFuncionario.map((f, idx) => (
              <option key={idx} value={f.funcionario}>{f.funcionario}</option>
            ))}
          </select>

          <select
            value={filtroFormaPagamento}
            onChange={(e) => setFiltroFormaPagamento(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todas as formas</option>
            {formasRecebimento.map((f, idx) => (
              <option key={idx} value={f.forma_pagamento}>{f.forma_pagamento}</option>
            ))}
          </select>

          <select
            value={filtroCategoria}
            onChange={(e) => setFiltroCategoria(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todas as categorias</option>
            {produtosDetalhados.map((cat, idx) => (
              <option key={idx} value={cat.categoria}>{cat.categoria}</option>
            ))}
          </select>

          <button
            onClick={() => {
              setFiltroFuncionario('');
              setFiltroFormaPagamento('');
              setFiltroCategoria('');
            }}
            className="px-3 py-2 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors"
          >
            Limpar Filtros
          </button>

          <button
            onClick={() => setMostrarGraficos(!mostrarGraficos)}
            className="ml-auto px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <BarChart3 className="w-4 h-4" />
            {mostrarGraficos ? 'Ocultar' : 'Mostrar'} Gráficos
          </button>
        </div>

        {/* Abas */}
        <div className="flex gap-2 border-b">
          <button
            onClick={() => setAbaAtiva('resumo')}
            className={`px-4 py-2 font-medium ${
              abaAtiva === 'resumo'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Resumo
          </button>
          <button
            onClick={() => setAbaAtiva('produtos')}
            className={`px-4 py-2 font-medium ${
              abaAtiva === 'produtos'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Totais por produto/serviço
          </button>
          <button
            onClick={() => setAbaAtiva('lista')}
            className={`px-4 py-2 font-medium ${
              abaAtiva === 'lista'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Lista de Vendas
          </button>
          <button
            onClick={() => setAbaAtiva('comparacao')}
            className={`px-4 py-2 font-medium ${
              abaAtiva === 'comparacao'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Comparação de Períodos
          </button>
        </div>
      </div>

      {/* Conteúdo das Abas */}
      {abaAtiva === 'resumo' && (
        <div>
          {/* Banner de Comparação */}
          {modoComparacao && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                <div className="text-sm">
                  <span className="font-semibold text-blue-800">Modo Comparação Ativo:</span>
                  <span className="text-blue-700 ml-2">
                    Comparando <span className="font-medium">{formatarData(dataInicio)} até {formatarData(dataFim)}</span> com <span className="font-medium">{getTextoComparacao()}</span>
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Cards de Resumo */}
          <div className="grid grid-cols-5 gap-4 mb-6">
            <CardComVariacao
              titulo="Venda Bruta"
              valor={resumo.venda_bruta}
              icone={DollarSign}
              cor="bg-green-500"
              valorAnterior={resumoComparacao.venda_bruta}
            />
            <CardComVariacao
              titulo="Taxa de Entrega"
              valor={resumo.taxa_entrega}
              icone={Package}
              cor="bg-gray-400"
              valorAnterior={resumoComparacao.taxa_entrega}
            />
            <CardComVariacao
              titulo="Desconto"
              valor={resumo.desconto}
              icone={TrendingUp}
              cor="bg-yellow-500"
              valorAnterior={resumoComparacao.desconto}
            />
            <CardComVariacao
              titulo="Venda Líquida"
              valor={resumo.venda_liquida}
              icone={DollarSign}
              cor="bg-blue-500"
              valorAnterior={resumoComparacao.venda_liquida}
            />
            <CardComVariacao
              titulo="Em Aberto"
              valor={resumo.em_aberto}
              icone={CreditCard}
              cor="bg-red-500"
              valorAnterior={resumoComparacao.em_aberto}
            />
          </div>

          {/* Cards de Análise de Rentabilidade */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-orange-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{formatarMoeda(resumo.custo_total || 0)}</div>
              <div className="text-sm">Custo Total</div>
            </div>
            <div className="bg-purple-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{formatarMoeda(resumo.taxa_cartao_total || 0)}</div>
              <div className="text-sm">Taxas de Cartão</div>
            </div>
            <div className="bg-green-600 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{formatarMoeda(resumo.lucro_total || 0)}</div>
              <div className="text-sm">Lucro Total</div>
            </div>
            <div className="bg-teal-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{resumo.margem_media || 0}%</div>
              <div className="text-sm">Margem Média</div>
            </div>
          </div>

          {/* Gráficos */}
          {mostrarGraficos && (
            <div className="grid grid-cols-2 gap-6 mb-6">
              {/* Gráfico de Vendas por Período */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Vendas no Período</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={vendasPorData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="data" tickFormatter={(value) => new Date(value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })} />
                    <YAxis tickFormatter={(value) => `R$ ${(value/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(value) => formatarMoeda(value)} labelFormatter={(label) => formatarData(label)} />
                    <Legend />
                    <Line type="monotone" dataKey="valor_bruto" stroke="#3B82F6" strokeWidth={2} name="Venda Bruta" />
                    <Line type="monotone" dataKey="valor_liquido" stroke="#10B981" strokeWidth={2} name="Venda Líquida" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Gráfico de Formas de Pagamento - Barras Horizontais */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Formas de Pagamento</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart 
                    data={formasRecebimentoFiltradas}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      type="number" 
                      tickFormatter={(value) => formatarMoeda(value)}
                    />
                    <YAxis 
                      type="category" 
                      dataKey="forma_pagamento" 
                      width={110}
                      style={{ fontSize: '12px' }}
                    />
                    <Tooltip 
                      formatter={(value, name, props) => {
                        const total = formasRecebimentoFiltradas.reduce((sum, item) => sum + item.valor_total, 0);
                        const percent = ((value / total) * 100).toFixed(1);
                        return [`${formatarMoeda(value)} (${percent}%)`, 'Valor'];
                      }}
                      contentStyle={{ backgroundColor: 'white', border: '1px solid #ccc', borderRadius: '4px', padding: '8px' }}
                    />
                    <Bar 
                      dataKey="valor_total" 
                      fill="#3B82F6"
                      radius={[0, 8, 8, 0]}
                      label={{
                        position: 'right',
                        formatter: (value) => {
                          const total = formasRecebimentoFiltradas.reduce((sum, item) => sum + item.valor_total, 0);
                          const percent = ((value / total) * 100).toFixed(1);
                          return `${percent}%`;
                        },
                        style: { fontSize: '11px', fontWeight: 'bold' }
                      }}
                    >
                      {formasRecebimentoFiltradas.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Gráfico de Barras - Top 10 Produtos */}
              <div className="bg-white rounded-lg shadow p-4 col-span-2">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Top 10 Categorias de Produtos</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={produtosDetalhadosFiltrados.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="categoria" />
                    <YAxis tickFormatter={(value) => `R$ ${(value/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(value) => formatarMoeda(value)} />
                    <Legend />
                    <Bar dataKey="total_liquido" fill="#3B82F6" name="Valor Líquido" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Vendas por Data */}
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
              Vendas por data
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Data</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Tkt. Médio</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Taxa entrega</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">(%)</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                    <th className="px-4 py-2 text-right">Vl. recebido</th>
                    <th className="px-4 py-2 text-right">Saldo aberto</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorData.map((item, idx) => (
                    <tr key={idx} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2">{formatarData(item.data)}</td>
                      <td className="px-4 py-2 text-right">{item.quantidade}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.ticket_medio)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.taxa_entrega)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.desconto)}</td>
                      <td className="px-4 py-2 text-right">{item.percentual_desconto}%</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_liquido)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_recebido)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.saldo_aberto)}</td>
                    </tr>
                  ))}
                  {/* TOTAL */}
                  {vendasPorData.length > 0 && (() => {
                    const totalQtd = vendasPorData.reduce((sum, item) => sum + item.quantidade, 0);
                    const totalBruto = vendasPorData.reduce((sum, item) => sum + item.valor_bruto, 0);
                    const totalDesconto = vendasPorData.reduce((sum, item) => sum + item.desconto, 0);
                    const ticketMedio = totalQtd > 0 ? totalBruto / totalQtd : 0;
                    const percentualDesconto = totalBruto > 0 ? (totalDesconto / totalBruto * 100).toFixed(1) : 0;
                    
                    return (
                      <tr style={{backgroundColor: '#E5E7EB', color: '#1F2937', fontWeight: 'bold'}}>
                        <td className="px-4 py-3">TOTAL</td>
                        <td className="px-4 py-3 text-right">{totalQtd}</td>
                        <td className="px-4 py-3 text-right">{formatarMoeda(ticketMedio)}</td>
                        <td className="px-4 py-3 text-right">{formatarMoeda(totalBruto)}</td>
                        <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.taxa_entrega, 0))}</td>
                        <td className="px-4 py-3 text-right">{formatarMoeda(totalDesconto)}</td>
                        <td className="px-4 py-3 text-right">{percentualDesconto}%</td>
                        <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.valor_liquido, 0))}</td>
                        <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.valor_recebido, 0))}</td>
                        <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.saldo_aberto, 0))}</td>
                      </tr>
                    );
                  })()}
                </tbody>
              </table>
            </div>
          </div>

          {/* Grid com outras tabelas */}
          <div className="grid grid-cols-2 gap-6">
            {/* Formas de Recebimento */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Formas de recebimento
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Forma</th>
                    <th className="px-4 py-2 text-right">Valor pago</th>
                  </tr>
                </thead>
                <tbody>
                  {formasRecebimento.map((item, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="px-4 py-2">{item.forma_pagamento}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_total)}</td>
                    </tr>
                  ))}
                  {formasRecebimento.length > 0 && (
                    <tr style={{backgroundColor: '#E5E7EB', color: '#1F2937', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(formasRecebimento.reduce((sum, item) => sum + item.valor_total, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Funcionário */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Funcionário
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Nome</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorFuncionarioFiltradas.map((item, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="px-4 py-2">{item.funcionario}</td>
                      <td className="px-4 py-2 text-right">{item.quantidade}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.desconto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_liquido)}</td>
                    </tr>
                  ))}
                  {vendasPorFuncionarioFiltradas.length > 0 && (
                    <tr style={{backgroundColor: '#E5E7EB', color: '#1F2937', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">{vendasPorFuncionarioFiltradas.reduce((sum, item) => sum + item.quantidade, 0)}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorFuncionarioFiltradas.reduce((sum, item) => sum + item.valor_bruto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorFuncionarioFiltradas.reduce((sum, item) => sum + item.desconto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorFuncionarioFiltradas.reduce((sum, item) => sum + item.valor_liquido, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Tipo */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Tipo
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Tipo</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorTipo.map((item, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="px-4 py-2">{item.tipo}</td>
                      <td className="px-4 py-2 text-right">{item.quantidade}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.desconto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_liquido)}</td>
                    </tr>
                  ))}
                  {vendasPorTipo.length > 0 && (
                    <tr style={{backgroundColor: '#E5E7EB', color: '#1F2937', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">{vendasPorTipo.reduce((sum, item) => sum + item.quantidade, 0)}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorTipo.reduce((sum, item) => sum + item.valor_bruto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorTipo.reduce((sum, item) => sum + item.desconto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorTipo.reduce((sum, item) => sum + item.valor_liquido, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Grupo de Produto */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Grupo de produto
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Nome</th>
                    <th className="px-4 py-2 text-right">Percentual</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorGrupo.map((item, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="px-4 py-2">{item.grupo}</td>
                      <td className="px-4 py-2 text-right">{item.percentual}%</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.desconto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_liquido)}</td>
                    </tr>
                  ))}
                  {vendasPorGrupo.length > 0 && (
                    <tr style={{backgroundColor: '#E5E7EB', color: '#1F2937', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">-</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorGrupo.reduce((sum, item) => sum + item.valor_bruto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorGrupo.reduce((sum, item) => sum + item.desconto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorGrupo.reduce((sum, item) => sum + item.valor_liquido, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Aba Produtos Detalhados */}
      {abaAtiva === 'produtos' && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Produtos/Serviços
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Produtos/Serviços</th>
                  <th className="px-4 py-2 text-right">Itens</th>
                  <th className="px-4 py-2 text-right">Bruto</th>
                  <th className="px-4 py-2 text-right">Desconto</th>
                  <th className="px-4 py-2 text-right">Líquido</th>
                </tr>
              </thead>
              <tbody>
                {produtosDetalhadosFiltrados.map((categoria, catIdx) => (
                  <>
                    {/* Linha da Categoria */}
                    <tr key={`cat-${catIdx}`} className="bg-blue-50 font-semibold">
                      <td className="px-4 py-2">{categoria.categoria}</td>
                      <td className="px-4 py-2 text-right">{categoria.total_quantidade}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(categoria.total_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(categoria.total_desconto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(categoria.total_liquido)}</td>
                    </tr>
                    
                    {/* Subcategorias */}
                    {categoria.subcategorias && categoria.subcategorias.map((sub, subIdx) => (
                      <>
                        {/* Linha da Subcategoria */}
                        <tr key={`sub-${catIdx}-${subIdx}`} className="bg-gray-50 font-medium">
                          <td className="px-4 py-2 pl-8">{sub.subcategoria}</td>
                          <td className="px-4 py-2 text-right">{sub.total_quantidade}</td>
                          <td className="px-4 py-2 text-right">{formatarMoeda(sub.total_bruto)}</td>
                          <td className="px-4 py-2 text-right">{formatarMoeda(sub.total_desconto)}</td>
                          <td className="px-4 py-2 text-right">{formatarMoeda(sub.total_liquido)}</td>
                        </tr>
                        
                        {/* Produtos da Subcategoria */}
                        {sub.produtos && sub.produtos.map((produto, prodIdx) => (
                          <tr key={`prod-${catIdx}-${subIdx}-${prodIdx}`} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-2 pl-12 text-gray-700">{produto.produto}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{produto.quantidade}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.valor_bruto)}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.desconto)}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.valor_liquido)}</td>
                          </tr>
                        ))}
                      </>
                    ))}
                    
                    {/* Produtos sem subcategoria */}
                    {categoria.produtos && categoria.produtos.map((produto, prodIdx) => (
                      <tr key={`prod-${catIdx}-${prodIdx}`} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-2 pl-8 text-gray-700">{produto.produto}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{produto.quantidade}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.valor_bruto)}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.desconto)}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.valor_liquido)}</td>
                      </tr>
                    ))}
                  </>
                ))}
                
                {/* TOTAL GERAL */}
                {produtosDetalhados.length > 0 && (
                  <tr style={{backgroundColor: '#E5E7EB', color: '#1F2937', fontWeight: 'bold'}}>
                    <td className="px-4 py-3">TOTAL GERAL</td>
                    <td className="px-4 py-3 text-right">
                      {produtosDetalhados.reduce((sum, cat) => sum + cat.total_quantidade, 0)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(produtosDetalhados.reduce((sum, cat) => sum + cat.total_bruto, 0))}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(produtosDetalhados.reduce((sum, cat) => sum + cat.total_desconto, 0))}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(produtosDetalhados.reduce((sum, cat) => sum + cat.total_liquido, 0))}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aba Lista de Vendas */}
      {abaAtiva === 'lista' && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Lista de Vendas com Análise de Rentabilidade
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-2 py-2 text-left w-8"></th>
                  <th className="px-2 py-2 text-left">Data</th>
                  <th className="px-2 py-2 text-left">Código</th>
                  <th className="px-2 py-2 text-left">Cliente</th>
                  <th className="px-2 py-2 text-right">Venda Bruta</th>
                  <th className="px-2 py-2 text-right">Desconto</th>
                  <th className="px-2 py-2 text-right">Taxa Entrega</th>
                  <th className="px-2 py-2 text-right">Taxa Cartão</th>
                  <th className="px-2 py-2 text-right">Comissão</th>
                  <th className="px-2 py-2 text-right">Custo</th>
                  <th className="px-2 py-2 text-right">Líquida</th>
                  <th className="px-2 py-2 text-right">Lucro</th>
                  <th className="px-2 py-2 text-right">MG Venda</th>
                  <th className="px-2 py-2 text-right">MG Custo</th>
                  <th className="px-2 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {listaVendas.map((venda) => (
                  <>
                    <tr key={venda.id} className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleVendaExpandida(venda.id)}>
                      <td className="px-2 py-2">
                        {vendasExpandidas.has(venda.id) ? 
                          <ChevronDown className="w-4 h-4 text-gray-600" /> : 
                          <ChevronRight className="w-4 h-4 text-gray-600" />
                        }
                      </td>
                      <td className="px-2 py-2 whitespace-nowrap">{formatarData(venda.data_venda)}</td>
                      <td className="px-2 py-2">{venda.numero_venda}</td>
                      <td className="px-2 py-2">{venda.cliente_nome}</td>
                      <td className="px-2 py-2 text-right font-medium">{formatarMoeda(venda.venda_bruta)}</td>
                      <td className="px-2 py-2 text-right text-red-600">-{formatarMoeda(venda.desconto)}</td>
                      <td className="px-2 py-2 text-right text-gray-600">-{formatarMoeda(venda.taxa_entrega)}</td>
                      <td className="px-2 py-2 text-right text-purple-600">-{formatarMoeda(venda.taxa_cartao)}</td>
                      <td className="px-2 py-2 text-right text-blue-600">-{formatarMoeda(venda.comissao)}</td>
                      <td className="px-2 py-2 text-right text-orange-600">-{formatarMoeda(venda.custo_produtos)}</td>
                      <td className="px-2 py-2 text-right font-medium">{formatarMoeda(venda.venda_liquida)}</td>
                      <td className={`px-2 py-2 text-right font-bold ${venda.lucro >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatarMoeda(venda.lucro)}
                      </td>
                      <td className="px-2 py-2 text-right">{venda.margem_sobre_venda}%</td>
                      <td className="px-2 py-2 text-right">{venda.margem_sobre_custo}%</td>
                      <td className="px-2 py-2 text-center">
                        <span className={`px-2 py-1 rounded text-xs ${
                          venda.status === 'finalizada' ? 'bg-green-100 text-green-800' :
                          venda.status === 'baixa_parcial' ? 'bg-blue-100 text-blue-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {venda.status === 'finalizada' ? 'Baixada' : 
                           venda.status === 'baixa_parcial' ? 'Parcial' : 
                           'Aberta'}
                        </span>
                      </td>
                    </tr>
                    
                    {/* Linha expandida com detalhes dos produtos */}
                    {vendasExpandidas.has(venda.id) && venda.itens && venda.itens.length > 0 && (
                      <tr key={`${venda.id}-detalhes`} className="bg-blue-50">
                        <td colSpan="15" className="px-4 py-3">
                          <div className="pl-8">
                            <div className="font-semibold text-gray-700 mb-2">Produtos desta venda:</div>
                            <table className="w-full text-xs">
                              <thead className="bg-blue-100">
                                <tr>
                                  <th className="px-2 py-1 text-left">Produto</th>
                                  <th className="px-2 py-1 text-center">Qtd</th>
                                  <th className="px-2 py-1 text-right">Preço Unit.</th>
                                  <th className="px-2 py-1 text-right">Venda Bruta</th>
                                  <th className="px-2 py-1 text-right">Desconto</th>
                                  <th className="px-2 py-1 text-right">Taxa Entr.</th>
                                  <th className="px-2 py-1 text-right">Taxa Cartão</th>
                                  <th className="px-2 py-1 text-right">Comissão</th>
                                  <th className="px-2 py-1 text-right">Custo Unit.</th>
                                  <th className="px-2 py-1 text-right">Custo Total</th>
                                  <th className="px-2 py-1 text-right">Líquido</th>
                                  <th className="px-2 py-1 text-right">Lucro</th>
                                  <th className="px-2 py-1 text-right">MG Venda</th>
                                  <th className="px-2 py-1 text-right">MG Custo</th>
                                </tr>
                              </thead>
                              <tbody>
                                {venda.itens.map((item, idx) => (
                                  <tr key={idx} className="border-b border-blue-200 hover:bg-blue-100">
                                    <td className="px-2 py-1">{item.produto_nome}</td>
                                    <td className="px-2 py-1 text-center">{item.quantidade}</td>
                                    <td className="px-2 py-1 text-right">{formatarMoeda(item.preco_unitario)}</td>
                                    <td className="px-2 py-1 text-right font-medium">{formatarMoeda(item.venda_bruta)}</td>
                                    <td className="px-2 py-1 text-right text-red-600">-{formatarMoeda(item.desconto)}</td>
                                    <td className="px-2 py-1 text-right text-gray-600">-{formatarMoeda(item.taxa_entrega)}</td>
                                    <td className="px-2 py-1 text-right text-purple-600">-{formatarMoeda(item.taxa_cartao)}</td>
                                    <td className="px-2 py-1 text-right text-blue-600">-{formatarMoeda(item.comissao)}</td>
                                    <td className="px-2 py-1 text-right text-orange-600">{formatarMoeda(item.custo_unitario)}</td>
                                    <td className="px-2 py-1 text-right text-orange-600 font-medium">-{formatarMoeda(item.custo_total)}</td>
                                    <td className="px-2 py-1 text-right font-medium">{formatarMoeda(item.valor_liquido)}</td>
                                    <td 
                                      className={`px-2 py-1 text-right font-bold ${item.lucro >= 0 ? 'text-green-600' : 'text-red-600'} cursor-help`}
                                      title={`Lucro unitário: ${formatarMoeda(item.lucro_unitario)}`}
                                    >
                                      {formatarMoeda(item.lucro)}
                                    </td>
                                    <td 
                                      className="px-2 py-1 text-right cursor-help"
                                      title={`Margem unitária: ${item.margem_sobre_venda}%`}
                                    >
                                      {item.margem_sobre_venda}%
                                    </td>
                                    <td 
                                      className="px-2 py-1 text-right cursor-help"
                                      title={`Markup unitário: ${item.margem_sobre_custo}%`}
                                    >
                                      {item.margem_sobre_custo}%
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aba de Comparação */}
      {abaAtiva === 'comparacao' && (
        <div>
          {/* Filtro de Tipo de Comparação */}
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">Tipo de Análise:</label>
              <select
                value={tipoComparacao}
                onChange={(e) => setTipoComparacao(e.target.value)}
                className="border rounded px-4 py-2 text-sm bg-blue-50 font-medium min-w-[250px]"
              >
                <option value="financeiro">📊 Comparação Financeira</option>
                <option value="formas_pagamento">💳 Por Forma de Pagamento</option>
                <option value="produtos">📦 Por Grupo de Produtos</option>
                <option value="funcionarios">👥 Por Funcionário</option>
              </select>
              
              <div className="ml-auto text-sm text-gray-600">
                <span className="font-medium">Período Atual:</span> {formatarData(dataInicio)} - {formatarData(dataFim)}
              </div>
            </div>
          </div>

          {/* Cards de Comparação - 3 Colunas */}
          {tipoComparacao === 'financeiro' && (
            <>
              <div className="grid grid-cols-3 gap-6 mb-6">
                {/* Card 1 - Período Anterior */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-gray-300">
                  <div className="bg-gray-500 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📅 Período Anterior</h3>
                    <p className="text-xs opacity-90 mt-1">{getTextoComparacao()}</p>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Quantidade de Vendas</div>
                      <div className="text-2xl font-bold text-gray-700">{resumoComparacao.quantidade_vendas || 0}</div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Bruto</div>
                      <div className="text-xl font-bold text-gray-700">{formatarMoeda(resumoComparacao.venda_bruta)}</div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Líquido</div>
                      <div className="text-xl font-bold text-blue-600">{formatarMoeda(resumoComparacao.venda_liquida)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">Valor Recebido</div>
                      <div className="text-xl font-bold text-green-600">{formatarMoeda((resumoComparacao.venda_liquida - resumoComparacao.em_aberto) || 0)}</div>
                    </div>
                  </div>
                </div>

                {/* Card 2 - Período Atual */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-blue-500">
                  <div className="bg-blue-600 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📅 Período Atual</h3>
                    <p className="text-xs opacity-90 mt-1">{formatarData(dataInicio)} - {formatarData(dataFim)}</p>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Quantidade de Vendas</div>
                      <div className="text-2xl font-bold text-gray-700">{resumo.quantidade_vendas || 0}</div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Bruto</div>
                      <div className="text-xl font-bold text-gray-700">{formatarMoeda(resumo.venda_bruta)}</div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Líquido</div>
                      <div className="text-xl font-bold text-blue-600">{formatarMoeda(resumo.venda_liquida)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">Valor Recebido</div>
                      <div className="text-xl font-bold text-green-600">{formatarMoeda((resumo.venda_liquida - resumo.em_aberto) || 0)}</div>
                    </div>
                  </div>
                </div>

                {/* Card 3 - Diferença/Variação */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-green-500">
                  <div className="bg-green-600 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📈 Diferença</h3>
                    <p className="text-xs opacity-90 mt-1">Variação vs período anterior</p>
                  </div>
                  <div className="p-4 space-y-3">
                    {(() => {
                      const varQtd = calcularVariacao(resumo.quantidade_vendas, resumoComparacao.quantidade_vendas);
                      const varBruto = calcularVariacao(resumo.venda_bruta, resumoComparacao.venda_bruta);
                      const varLiquido = calcularVariacao(resumo.venda_liquida, resumoComparacao.venda_liquida);
                      const valorRecebidoAtual = resumo.venda_liquida - resumo.em_aberto;
                      const valorRecebidoAnt = resumoComparacao.venda_liquida - resumoComparacao.em_aberto;
                      const varRecebido = calcularVariacao(valorRecebidoAtual, valorRecebidoAnt);
                      
                      return (
                        <>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">Qtd de Vendas</div>
                            <div className={`text-2xl font-bold flex items-center gap-2 ${varQtd.percentual >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {varQtd.percentual >= 0 ? <ArrowUp className="w-6 h-6" /> : <ArrowDown className="w-6 h-6" />}
                              {Math.abs(varQtd.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {varQtd.valor >= 0 ? '+' : ''}{varQtd.valor.toFixed(0)} vendas
                            </div>
                          </div>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">Valor Bruto</div>
                            <div className={`text-xl font-bold flex items-center gap-2 ${varBruto.percentual >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {varBruto.percentual >= 0 ? <ArrowUp className="w-5 h-5" /> : <ArrowDown className="w-5 h-5" />}
                              {Math.abs(varBruto.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">{formatarMoeda(varBruto.valor)}</div>
                          </div>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">Valor Líquido</div>
                            <div className={`text-xl font-bold flex items-center gap-2 ${varLiquido.percentual >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {varLiquido.percentual >= 0 ? <ArrowUp className="w-5 h-5" /> : <ArrowDown className="w-5 h-5" />}
                              {Math.abs(varLiquido.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">{formatarMoeda(varLiquido.valor)}</div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-600">Valor Recebido</div>
                            <div className={`text-xl font-bold flex items-center gap-2 ${varRecebido.percentual >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {varRecebido.percentual >= 0 ? <ArrowUp className="w-5 h-5" /> : <ArrowDown className="w-5 h-5" />}
                              {Math.abs(varRecebido.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">{formatarMoeda(varRecebido.valor)}</div>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>

              {/* Gráfico de Barras Comparativo */}
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Comparação Visual</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={[
                    { nome: 'Qtd Vendas', Anterior: resumoComparacao.quantidade_vendas || 0, Atual: resumo.quantidade_vendas || 0 },
                    { nome: 'Vl. Bruto (mil)', Anterior: (resumoComparacao.venda_bruta || 0) / 1000, Atual: (resumo.venda_bruta || 0) / 1000 },
                    { nome: 'Vl. Líquido (mil)', Anterior: (resumoComparacao.venda_liquida || 0) / 1000, Atual: (resumo.venda_liquida || 0) / 1000 },
                    { nome: 'Vl. Recebido (mil)', Anterior: ((resumoComparacao.venda_liquida - resumoComparacao.em_aberto) || 0) / 1000, Atual: ((resumo.venda_liquida - resumo.em_aberto) || 0) / 1000 }
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="nome" />
                    <YAxis />
                    <Tooltip formatter={(value, name) => [name.includes('mil') ? `R$ ${value.toFixed(1)}k` : value.toFixed(0), name]} />
                    <Legend />
                    <Bar dataKey="Anterior" fill="#9CA3AF" name="Período Anterior" />
                    <Bar dataKey="Atual" fill="#3B82F6" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Comparação por Forma de Pagamento */}
          {tipoComparacao === 'formas_pagamento' && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Comparação por Forma de Pagamento</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">Forma de Pagamento</th>
                        <th className="px-4 py-3 text-right">Anterior</th>
                        <th className="px-4 py-3 text-right">Atual</th>
                        <th className="px-4 py-3 text-right">Diferença</th>
                        <th className="px-4 py-3 text-center">Variação %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {formasRecebimento.map((formaAtual, idx) => {
                        const formaAnt = formasRecebimentoComparacao.find(f => f.forma_pagamento === formaAtual.forma_pagamento) || { valor_total: 0 };
                        const variacao = calcularVariacao(formaAtual.valor_total, formaAnt.valor_total);
                        return (
                          <tr key={idx} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">{formaAtual.forma_pagamento}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{formatarMoeda(formaAnt.valor_total)}</td>
                            <td className="px-4 py-3 text-right font-medium">{formatarMoeda(formaAtual.valor_total)}</td>
                            <td className="px-4 py-3 text-right">{formatarMoeda(variacao.valor)}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                {variacao.percentual >= 0 ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Barras por Forma de Pagamento */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Comparação Visual</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={formasRecebimento.map(f => ({
                    nome: f.forma_pagamento,
                    Anterior: (formasRecebimentoComparacao.find(fa => fa.forma_pagamento === f.forma_pagamento)?.valor_total || 0) / 1000,
                    Atual: f.valor_total / 1000
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="nome" angle={-15} textAnchor="end" height={80} />
                    <YAxis tickFormatter={(value) => `R$ ${value.toFixed(0)}k`} />
                    <Tooltip formatter={(value) => `R$ ${value.toFixed(1)}k`} />
                    <Legend />
                    <Bar dataKey="Anterior" fill="#9CA3AF" name="Período Anterior" />
                    <Bar dataKey="Atual" fill="#10B981" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Comparação por Grupo de Produtos */}
          {tipoComparacao === 'produtos' && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Comparação por Grupo de Produtos</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">Grupo</th>
                        <th className="px-4 py-3 text-right">Anterior</th>
                        <th className="px-4 py-3 text-right">Atual</th>
                        <th className="px-4 py-3 text-right">Diferença</th>
                        <th className="px-4 py-3 text-center">Variação %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendasPorGrupo.map((grupoAtual, idx) => {
                        const grupoAnt = vendasPorGrupoComparacao.find(g => g.grupo === grupoAtual.grupo) || { valor_liquido: 0 };
                        const variacao = calcularVariacao(grupoAtual.valor_liquido, grupoAnt.valor_liquido);
                        return (
                          <tr key={idx} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">{grupoAtual.grupo}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{formatarMoeda(grupoAnt.valor_liquido)}</td>
                            <td className="px-4 py-3 text-right font-medium">{formatarMoeda(grupoAtual.valor_liquido)}</td>
                            <td className="px-4 py-3 text-right">{formatarMoeda(variacao.valor)}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                {variacao.percentual >= 0 ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Pizza Duplo */}
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Período Anterior</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={vendasPorGrupoComparacao}
                        dataKey="valor_liquido"
                        nameKey="grupo"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={(entry) => {
                          const percent = ((entry.valor_liquido / vendasPorGrupoComparacao.reduce((sum, item) => sum + item.valor_liquido, 0)) * 100).toFixed(1);
                          return percent > 5 ? `${percent}%` : '';
                        }}
                      >
                        {vendasPorGrupoComparacao.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatarMoeda(value)} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Período Atual</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={vendasPorGrupo}
                        dataKey="valor_liquido"
                        nameKey="grupo"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={(entry) => {
                          const percent = ((entry.valor_liquido / vendasPorGrupo.reduce((sum, item) => sum + item.valor_liquido, 0)) * 100).toFixed(1);
                          return percent > 5 ? `${percent}%` : '';
                        }}
                      >
                        {vendasPorGrupo.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatarMoeda(value)} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}

          {/* Comparação por Funcionário */}
          {tipoComparacao === 'funcionarios' && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Comparação por Funcionário</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">Funcionário</th>
                        <th className="px-4 py-3 text-right">Qtd Ant.</th>
                        <th className="px-4 py-3 text-right">Qtd Atual</th>
                        <th className="px-4 py-3 text-right">Vl. Ant.</th>
                        <th className="px-4 py-3 text-right">Vl. Atual</th>
                        <th className="px-4 py-3 text-center">Variação</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendasPorFuncionario.map((funcAtual, idx) => {
                        const funcAnt = vendasPorFuncionarioComparacao.find(f => f.funcionario === funcAtual.funcionario) || { quantidade: 0, valor_liquido: 0 };
                        const variacao = calcularVariacao(funcAtual.valor_liquido, funcAnt.valor_liquido);
                        return (
                          <tr key={idx} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">{funcAtual.funcionario}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{funcAnt.quantidade}</td>
                            <td className="px-4 py-3 text-right font-medium">{funcAtual.quantidade}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{formatarMoeda(funcAnt.valor_liquido)}</td>
                            <td className="px-4 py-3 text-right font-medium">{formatarMoeda(funcAtual.valor_liquido)}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                {variacao.percentual >= 0 ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Barras por Funcionário */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Comparação Visual - Valor Líquido</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={vendasPorFuncionario.map(f => ({
                    nome: f.funcionario,
                    Anterior: (vendasPorFuncionarioComparacao.find(fa => fa.funcionario === f.funcionario)?.valor_liquido || 0) / 1000,
                    Atual: f.valor_liquido / 1000
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="nome" angle={-15} textAnchor="end" height={80} />
                    <YAxis tickFormatter={(value) => `R$ ${value.toFixed(0)}k`} />
                    <Tooltip formatter={(value) => `R$ ${value.toFixed(1)}k`} />
                    <Legend />
                    <Bar dataKey="Anterior" fill="#9CA3AF" name="Período Anterior" />
                    <Bar dataKey="Atual" fill="#8B5CF6" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
