import { useState, useEffect } from 'react';
import { 
  Plus, Edit2, Trash2, DollarSign, TrendingUp, AlertCircle,
  Building2, Wallet, CreditCard, X, Save, ArrowUpCircle, ArrowDownCircle
} from 'lucide-react';
import api from '../api';

const TIPOS_CONTA = [
  { value: 'banco', label: 'Banco', icon: Building2, cor_padrao: '#dc2626' },
  { value: 'caixa', label: 'Caixa Físico', icon: Wallet, cor_padrao: '#16a34a' },
  { value: 'digital', label: 'Carteira Digital', icon: CreditCard, cor_padrao: '#2563eb' }
];

const ICONES_DISPONIVEIS = [
  '🏦', '💰', '💳', '💵', '💸', '🏧',
  '🪙', '💴', '💶', '💷', '🤑', '💲',
  '🔒', '🏦', '🏪', '🏢', '🏭', '🎯',
  '📊', '📈', '💼', '👛', '🎁', '⚡'
];

function ContasBancarias() {
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [modalAjuste, setModalAjuste] = useState(false);
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [erro, setErro] = useState('');
  
  // Form states
  const [formData, setFormData] = useState({
    nome: '',
    tipo: 'banco',
    banco: '',
    saldo_inicial: 0,
    cor: '#dc2626',
    icone: '🏦',
    ativa: true
  });
  
  const [ajusteData, setAjusteData] = useState({
    novo_saldo: 0,
    descricao: ''
  });

  useEffect(() => {
    carregarContas();
  }, []);

  const carregarContas = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/contas-bancarias');
      setContas(response.data);
    } catch (error) {
      console.error('Erro:', error);
      setErro('Erro ao carregar contas bancárias');
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (conta = null) => {
    if (conta) {
      setFormData({
        nome: conta.nome,
        tipo: conta.tipo,
        banco: conta.banco || '',
        saldo_inicial: conta.saldo_inicial,
        cor: conta.cor || '#dc2626',
        icone: conta.icone || '🏦',
        ativa: conta.ativa
      });
      setContaSelecionada(conta);
    } else {
      const tipoPadrao = TIPOS_CONTA[0];
      setFormData({
        nome: '',
        tipo: 'banco',
        banco: '',
        saldo_inicial: 0,
        cor: tipoPadrao.cor_padrao,
        icone: '🏦',
        ativa: true
      });
      setContaSelecionada(null);
    }
    setModalAberto(true);
    setErro('');
  };

  const abrirModalAjuste = (conta) => {
    setContaSelecionada(conta);
    setAjusteData({
      novo_saldo: conta.saldo_atual,
      descricao: ''
    });
    setModalAjuste(true);
    setErro('');
  };

  const salvarConta = async (e) => {
    e.preventDefault();
    
    try {
      // Garantir que os dados estão no formato correto
      const dadosEnvio = {
        nome: formData.nome.trim(),
        tipo: formData.tipo,
        banco: formData.banco?.trim() || null,
        saldo_inicial: Number(formData.saldo_inicial) || 0,
        cor: formData.cor,
        icone: formData.icone || '🏦',
        ativa: Boolean(formData.ativa)
      };

      console.log('Enviando dados:', dadosEnvio);
      
      if (contaSelecionada) {
        await api.put(`/api/contas-bancarias/${contaSelecionada.id}`, dadosEnvio);
      } else {
        await api.post('/api/contas-bancarias', dadosEnvio);
      }
      
      await carregarContas();
      setModalAberto(false);
      setErro('');
    } catch (error) {
      console.error('Erro completo:', error);
      console.error('Response:', error.response);
      setErro(error.response?.data?.detail || error.message || 'Erro ao salvar conta');
    }
  };

  const ajustarSaldo = async (e) => {
    e.preventDefault();
    
    if (!ajusteData.descricao.trim()) {
      setErro('Informe o motivo do ajuste');
      return;
    }
    
    try {
      await api.post(
        `/api/contas-bancarias/${contaSelecionada.id}/ajustar-saldo`,
        ajusteData
      );
      
      await carregarContas();
      setModalAjuste(false);
    } catch (error) {
      console.error('Erro:', error);
      setErro(error.response?.data?.detail || 'Erro ao ajustar saldo');
    }
  };

  const excluirConta = async (id) => {
    if (!confirm('Deseja realmente excluir esta conta?')) return;
    
    try {
      await api.delete(`/api/contas-bancarias/${id}`);
      await carregarContas();
    } catch (error) {
      console.error('Erro:', error);
      setErro(error.response?.data?.detail || 'Erro ao excluir conta');
    }
  };

  const calcularTotais = () => {
    return contas.reduce((acc, conta) => {
      if (!conta.ativa) return acc;
      
      acc.total += conta.saldo_atual;
      acc.por_tipo[conta.tipo] = (acc.por_tipo[conta.tipo] || 0) + conta.saldo_atual;
      return acc;
    }, { total: 0, por_tipo: {} });
  };

  const totais = calcularTotais();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Contas Bancárias</h1>
            <p className="text-gray-600">Gerencie suas contas, caixas e carteiras digitais</p>
          </div>
          <button
            onClick={() => abrirModal()}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
          >
            <Plus className="w-5 h-5" />
            Nova Conta
          </button>
        </div>
        
        {/* Resumo Geral */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 text-sm">Saldo Total</p>
                <p className="text-2xl font-bold">
                  R$ {totais.total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <DollarSign className="w-10 h-10 text-blue-200" />
            </div>
          </div>
          
          {TIPOS_CONTA.map(tipo => {
            const Icon = tipo.icon;
            const valor = totais.por_tipo[tipo.value] || 0;
            return (
              <div key={tipo.value} className="bg-white rounded-xl p-4 border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">{tipo.label}</p>
                    <p className="text-xl font-bold text-gray-800">
                      R$ {valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                  </div>
                  <Icon className="w-8 h-8 text-gray-400" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {erro && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-red-800">{erro}</p>
        </div>
      )}

      {/* Lista de Contas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {contas.map(conta => {
          const TipoIcon = TIPOS_CONTA.find(t => t.value === conta.tipo)?.icon || Building2;
          
          return (
            <div
              key={conta.id}
              className={`bg-white rounded-xl border-2 p-4 transition ${
                conta.ativa ? 'border-gray-200 hover:border-blue-300' : 'border-gray-100 opacity-60'
              }`}
            >
              {/* Header do Card */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div 
                    className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
                    style={{ backgroundColor: `${conta.cor}20` }}
                  >
                    {conta.icone}
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-800">{conta.nome}</h3>
                    <p className="text-sm text-gray-500 flex items-center gap-1">
                      <TipoIcon className="w-3 h-3" />
                      {TIPOS_CONTA.find(t => t.value === conta.tipo)?.label}
                    </p>
                  </div>
                </div>
                
                {!conta.ativa && (
                  <span className="text-xs bg-gray-200 text-gray-600 px-2 py-1 rounded">
                    Inativa
                  </span>
                )}
              </div>

              {/* Saldo */}
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-1">Saldo Atual</p>
                <p className="text-2xl font-bold text-gray-800">
                  R$ {conta.saldo_atual.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>

              {/* Ações */}
              <div className="flex gap-2">
                <button
                  onClick={() => abrirModalAjuste(conta)}
                  className="flex-1 flex items-center justify-center gap-1 bg-yellow-50 text-yellow-700 px-3 py-2 rounded-lg hover:bg-yellow-100 transition text-sm"
                  disabled={!conta.ativa}
                >
                  <TrendingUp className="w-4 h-4" />
                  Ajustar
                </button>
                <button
                  onClick={() => abrirModal(conta)}
                  className="flex items-center justify-center bg-gray-100 text-gray-700 p-2 rounded-lg hover:bg-gray-200 transition"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => excluirConta(conta.id)}
                  className="flex items-center justify-center bg-red-50 text-red-600 p-2 rounded-lg hover:bg-red-100 transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {contas.length === 0 && (
        <div className="text-center py-12">
          <Wallet className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg mb-4">Nenhuma conta cadastrada</p>
          <button
            onClick={() => abrirModal()}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            Cadastrar primeira conta
          </button>
        </div>
      )}

      {/* Modal Criar/Editar */}
      {modalAberto && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-800">
                {contaSelecionada ? 'Editar Conta' : 'Nova Conta'}
              </h2>
              <button onClick={() => setModalAberto(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={salvarConta} className="space-y-4">
              {erro && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-800 text-sm">
                  {erro}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                <select
                  value={formData.tipo}
                  onChange={(e) => {
                    const tipo = TIPOS_CONTA.find(t => t.value === e.target.value);
                    setFormData({ 
                      ...formData, 
                      tipo: e.target.value,
                      cor: tipo?.cor_padrao || formData.cor
                    });
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {TIPOS_CONTA.map(tipo => (
                    <option key={tipo.value} value={tipo.value}>{tipo.label}</option>
                  ))}
                </select>
              </div>

              {formData.tipo === 'banco' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Banco</label>
                  <input
                    type="text"
                    value={formData.banco}
                    onChange={(e) => setFormData({ ...formData, banco: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ex: Santander, Bradesco..."
                  />
                </div>
              )}

              {!contaSelecionada && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Saldo Inicial</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.saldo_inicial}
                    onChange={(e) => setFormData({ ...formData, saldo_inicial: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Cor</label>
                  <input
                    type="color"
                    value={formData.cor}
                    onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
                    className="w-full h-10 rounded-lg cursor-pointer"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Ícone Atual</label>
                  <div 
                    className="w-full h-10 border border-gray-300 rounded-lg flex items-center justify-center text-2xl bg-white"
                    style={{ backgroundColor: `${formData.cor}10` }}
                  >
                    {formData.icone}
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Escolher Ícone</label>
                <div className="grid grid-cols-8 gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200 max-h-32 overflow-y-auto">
                  {ICONES_DISPONIVEIS.map((icone, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => setFormData({ ...formData, icone })}
                      className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl transition hover:scale-110 ${
                        formData.icone === icone 
                          ? 'bg-blue-100 border-2 border-blue-500 ring-2 ring-blue-200' 
                          : 'bg-white border border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      {icone}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="ativa"
                  checked={formData.ativa}
                  onChange={(e) => setFormData({ ...formData, ativa: e.target.checked })}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="ativa" className="text-sm text-gray-700">Conta ativa</label>
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setModalAberto(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
                >
                  <Save className="w-4 h-4" />
                  Salvar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Ajustar Saldo */}
      {modalAjuste && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-800">Ajustar Saldo</h2>
              <button onClick={() => setModalAjuste(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={ajustarSaldo} className="space-y-4">
              {erro && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-800 text-sm">
                  {erro}
                </div>
              )}

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Saldo Atual</p>
                <p className="text-2xl font-bold text-gray-800">
                  R$ {contaSelecionada.saldo_atual.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Novo Saldo</label>
                <input
                  type="number"
                  step="0.01"
                  value={ajusteData.novo_saldo}
                  onChange={(e) => setAjusteData({ ...ajusteData, novo_saldo: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              {ajusteData.novo_saldo !== contaSelecionada.saldo_atual && (
                <div className={`flex items-center gap-2 p-3 rounded-lg ${
                  ajusteData.novo_saldo > contaSelecionada.saldo_atual 
                    ? 'bg-green-50 text-green-700' 
                    : 'bg-red-50 text-red-700'
                }`}>
                  {ajusteData.novo_saldo > contaSelecionada.saldo_atual ? (
                    <ArrowUpCircle className="w-5 h-5" />
                  ) : (
                    <ArrowDownCircle className="w-5 h-5" />
                  )}
                  <span className="font-medium">
                    {ajusteData.novo_saldo > contaSelecionada.saldo_atual ? '+' : ''}
                    R$ {Math.abs(ajusteData.novo_saldo - contaSelecionada.saldo_atual).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo do Ajuste</label>
                <textarea
                  value={ajusteData.descricao}
                  onChange={(e) => setAjusteData({ ...ajusteData, descricao: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                  placeholder="Ex: Acerto de caixa, valor encontrado a mais..."
                  required
                />
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setModalAjuste(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
                >
                  <Save className="w-4 h-4" />
                  Confirmar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default ContasBancarias;
