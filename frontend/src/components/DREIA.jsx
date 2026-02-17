import React, { useState, useEffect } from 'react';
import api from '../api';
import toast from 'react-hot-toast';
import { 
  Calendar, TrendingUp, BarChart3, Settings, 
  Download, RefreshCw, ChevronDown, Plus, Trash2,
  Lock, Unlock, DollarSign, Percent
} from 'lucide-react';

/**
 * ABA 7 - DRE IA
 * Componente principal para visualização e análise de DRE por canal
 */
export default function DREIA() {
  // ==================== ESTADO ====================
  const [tab, setTab] = useState('visao-geral'); // visao-geral, canais, alocacao
  const [loading, setLoading] = useState(false);
  const [dados, setDados] = useState(null);
  const [canais, setCanais] = useState([]);
  const [consolidado, setConsolidado] = useState(null);
  
  // Filtros
  const [usuarioId, setUsuarioId] = useState(1); // Ajustar conforme auth
  const [dataInicio, setDataInicio] = useState(obterDataInicio());
  const [dataFim, setDataFim] = useState(new Date().toISOString().split('T')[0]);
  
  // Alocação
  const [modoAlocacao, setModoAlocacao] = useState('proporcional'); // proporcional, manual
  const [alocacoes, setAlocacoes] = useState([]);
  const [salvarAlocacao, setSalvarAlocacao] = useState(false);
  
  // ==================== FUNÇÕES AUXILIARES ====================
  function obterDataInicio() {
    const hoje = new Date();
    const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    return inicio.toISOString().split('T')[0];
  }
  
  // ==================== CARREGAR DADOS ====================
  useEffect(() => {
    carregarDados();
  }, [dataInicio, dataFim]);
  
  const carregarDados = async () => {
    setLoading(true);
    try {
      // Buscar DRE período
      const respPeriodo = await api.get('/ia/dre/periodo', {
        params: {
          usuario_id: usuarioId,
          data_inicio: dataInicio,
          data_fim: dataFim
        }
      });
      
      // Buscar DRE por canais
      const respCanais = await api.get('/ia/dre/canais', {
        params: {
          usuario_id: usuarioId,
          data_inicio: dataInicio,
          data_fim: dataFim
        }
      });
      
      // Buscar DRE consolidado
      const respConsolidado = await api.get('/ia/dre/consolidado', {
        params: {
          usuario_id: usuarioId,
          data_inicio: dataInicio,
          data_fim: dataFim
        }
      });
      
      setDados(respPeriodo.data);
      setCanais(respCanais.data.canais || []);
      setConsolidado(respConsolidado.data);
      
      // Inicializar alocações
      inicializarAlocacoes(respCanais.data.canais || []);
      
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar DRE: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };
  
  const inicializarAlocacoes = (canaisData) => {
    if (modoAlocacao === 'proporcional') {
      // Calcular alocações proporcionais
      const receita_total = canaisData.reduce((sum, c) => sum + (c.receita || 0), 0);
      const novasAlocacoes = canaisData.map(canal => ({
        canal_id: canal.id,
        nome_canal: canal.nome,
        percentual: receita_total > 0 ? (canal.receita / receita_total) * 100 : 0,
        valor_alocado: 0 // Será calculado conforme despesas
      }));
      setAlocacoes(novasAlocacoes);
    }
  };
  
  // ==================== HANDLERS ====================
  const handleModoAlocacao = (modo) => {
    setModoAlocacao(modo);
    inicializarAlocacoes(canais);
  };
  
  const handleAtualizarAlocacao = (index, campo, valor) => {
    const novas = [...alocacoes];
    novas[index][campo] = valor;
    setAlocacoes(novas);
  };
  
  const handleSalvarAlocacao = async () => {
    setSalvarAlocacao(true);
    try {
      const payload = {
        usuario_id: usuarioId,
        periodo_id: dados?.id,
        modo: modoAlocacao,
        alocacoes: alocacoes
      };
      
      await api.post('/ia/dre/alocacao', payload);
      toast.success('Alocação salva com sucesso!');
      carregarDados();
    } catch (error) {
      console.error('Erro ao salvar alocação:', error);
      toast.error('Erro ao salvar: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSalvarAlocacao(false);
    }
  };
  
  // ==================== RENDERIZAÇÃO ====================
  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* HEADER */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <BarChart3 className="text-blue-600" size={32} />
            DRE Inteligente - ABA 7
          </h1>
          <p className="text-gray-600 mt-1">Análise detalhada por canal de vendas</p>
        </div>
        
        <button 
          onClick={carregarDados}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>
      
      {/* FILTROS */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar size={16} className="inline mr-2" />
              Data Início
            </label>
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar size={16} className="inline mr-2" />
              Data Fim
            </label>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-end gap-2">
            <button 
              onClick={carregarDados}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
            >
              Filtrar
            </button>
          </div>
        </div>
      </div>
      
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="text-gray-600 mt-4">Carregando dados...</p>
        </div>
      )}
      
      {!loading && (
        <>
          {/* TABS */}
          <div className="flex gap-4 mb-6 border-b">
            <button
              onClick={() => setTab('visao-geral')}
              className={`px-4 py-3 font-medium border-b-2 transition ${
                tab === 'visao-geral'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <TrendingUp size={18} className="inline mr-2" />
              Visão Geral
            </button>
            
            <button
              onClick={() => setTab('canais')}
              className={`px-4 py-3 font-medium border-b-2 transition ${
                tab === 'canais'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <BarChart3 size={18} className="inline mr-2" />
              Por Canal ({canais.length})
            </button>
            
            <button
              onClick={() => setTab('alocacao')}
              className={`px-4 py-3 font-medium border-b-2 transition ${
                tab === 'alocacao'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <Settings size={18} className="inline mr-2" />
              Alocação de Despesas
            </button>
          </div>
          
          {/* CONTEÚDO */}
          {tab === 'visao-geral' && <AbaDREVisaoGeral dados={consolidado} />}
          {tab === 'canais' && <AbaDRECanais canais={canais} />}
          {tab === 'alocacao' && (
            <AbaDREAlocacao 
              canais={canais}
              alocacoes={alocacoes}
              modoAlocacao={modoAlocacao}
              onModoChange={handleModoAlocacao}
              onAlocacaoChange={handleAtualizarAlocacao}
              onSalvar={handleSalvarAlocacao}
              salvando={salvarAlocacao}
            />
          )}
        </>
      )}
    </div>
  );
}

// ==================== COMPONENTES INTERNOS ====================

function AbaDREVisaoGeral({ dados }) {
  if (!dados) return <div className="text-center py-12 text-gray-500">Sem dados</div>;
  
  return (
    <div className="space-y-6">
      {/* CARDS PRINCIPAIS */}
      <div className="grid grid-cols-4 gap-4">
        <CardDRE 
          titulo="Receita Líquida"
          valor={dados.receita_liquida}
          cor="blue"
          icon={<DollarSign />}
        />
        <CardDRE 
          titulo="Custo de Produtos"
          valor={dados.custo_produtos}
          cor="red"
          icon={<TrendingDown />}
        />
        <CardDRE 
          titulo="Lucro Bruto"
          valor={dados.lucro_bruto}
          cor="green"
          icon={<TrendingUp />}
        />
        <CardDRE 
          titulo="Margem Bruta"
          valor={`${dados.margem_bruta}%`}
          cor="purple"
          icon={<Percent />}
        />
      </div>
      
      {/* TABELA COMPLETA */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <tbody className="divide-y">
            <TrDRE label="Receita Bruta" valor={dados.receita_bruta} destaque />
            <TrDRE label="(-) Descontos" valor={-dados.deducoes_receita} />
            <TrDRE label="= Receita Líquida" valor={dados.receita_liquida} destaque />
            <TrDRE label="(-) CMV" valor={-dados.custo_produtos} />
            <TrDRE label="= Lucro Bruto" valor={dados.lucro_bruto} destaque />
            <TrDRE label="(-) Despesas Vendas" valor={-dados.desp_vendas} />
            <TrDRE label="(-) Despesas Admin" valor={-dados.desp_administrativas} />
            <TrDRE label="(-) Despesas Financeiras" valor={-dados.desp_financeiras} />
            <TrDRE label="= Lucro Operacional" valor={dados.lucro_operacional} destaque />
            <TrDRE label="(-) Impostos" valor={-dados.impostos} />
            <TrDRE label="= Lucro Líquido" valor={dados.lucro_liquido} destaque color="green" />
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AbaDRECanais({ canais }) {
  return (
    <div className="space-y-4">
      {canais.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <BarChart3 size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500">Nenhum canal encontrado no período</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {canais.map((canal, idx) => (
            <CardCanal key={idx} canal={canal} />
          ))}
        </div>
      )}
    </div>
  );
}

function AbaDREAlocacao({ canais, alocacoes, modoAlocacao, onModoChange, onAlocacaoChange, onSalvar, salvando }) {
  return (
    <div className="space-y-6">
      {/* SELETOR DE MODO */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Settings size={20} />
          Modo de Alocação
        </h3>
        
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={modoAlocacao === 'proporcional'}
              onChange={() => onModoChange('proporcional')}
              className="w-4 h-4"
            />
            <span className="font-medium">
              <Lock size={16} className="inline mr-2" />
              Proporcional (Automático)
            </span>
            <span className="text-sm text-gray-600">Baseado na receita de cada canal</span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={modoAlocacao === 'manual'}
              onChange={() => onModoChange('manual')}
              className="w-4 h-4"
            />
            <span className="font-medium">
              <Unlock size={16} className="inline mr-2" />
              Manual (Customizado)
            </span>
            <span className="text-sm text-gray-600">Você define a alocação</span>
          </label>
        </div>
      </div>
      
      {/* TABELA DE ALOCAÇÕES */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-900">Canal</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900">Receita</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900">
                {modoAlocacao === 'proporcional' ? 'Percentual' : 'Valor Alocado'}
              </th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900">Ação</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {alocacoes.map((aloc, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{aloc.nome_canal}</td>
                <td className="px-4 py-3 text-right text-gray-600">
                  R$ {aloc.receita?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}
                </td>
                <td className="px-4 py-3 text-right">
                  {modoAlocacao === 'proporcional' ? (
                    <span className="font-medium text-blue-600">{aloc.percentual?.toFixed(2)}%</span>
                  ) : (
                    <input
                      type="number"
                      value={aloc.valor_alocado}
                      onChange={(e) => onAlocacaoChange(idx, 'valor_alocado', parseFloat(e.target.value))}
                      className="w-24 px-2 py-1 border border-gray-300 rounded text-right focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <button className="text-red-600 hover:text-red-700">
                    <Trash2 size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* BOTÃO SALVAR */}
      <div className="flex justify-end">
        <button
          onClick={onSalvar}
          disabled={salvando}
          className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
        >
          <Download size={18} />
          {salvando ? 'Salvando...' : 'Salvar Alocação'}
        </button>
      </div>
    </div>
  );
}

// ==================== COMPONENTES REUTILIZÁVEIS ====================

function CardDRE({ titulo, valor, cor, icon }) {
  const corClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    red: 'bg-red-50 text-red-600 border-red-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200'
  };
  
  return (
    <div className={`${corClasses[cor]} border rounded-lg p-4`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{titulo}</p>
          <p className="text-2xl font-bold mt-2">
            {typeof valor === 'string' ? valor : `R$ ${valor?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`}
          </p>
        </div>
        <div className="text-3xl opacity-30">{icon}</div>
      </div>
    </div>
  );
}

function TrDRE({ label, valor, destaque, color }) {
  return (
    <tr className={destaque ? 'bg-gray-100 font-semibold' : ''}>
      <td className="px-6 py-3 text-gray-900">{label}</td>
      <td className={`px-6 py-3 text-right ${color === 'green' ? 'text-green-600 font-bold' : 'text-gray-900'}`}>
        R$ {valor?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}
      </td>
    </tr>
  );
}

function CardCanal({ canal }) {
  const margem = canal.receita > 0 ? ((canal.lucro / canal.receita) * 100) : 0;
  
  return (
    <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-600">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{canal.nome}</h3>
      
      <div className="space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-600">Receita:</span>
          <span className="font-semibold">R$ {canal.receita?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Custo:</span>
          <span className="font-semibold">R$ {canal.custo?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Despesas:</span>
          <span className="font-semibold">R$ {canal.despesas?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span>
        </div>
        <div className="border-t pt-2 mt-2 flex justify-between">
          <span className="text-gray-900 font-semibold">Lucro:</span>
          <span className="text-green-600 font-bold">R$ {canal.lucro?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Margem:</span>
          <span className="font-semibold text-blue-600">{margem.toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
}
