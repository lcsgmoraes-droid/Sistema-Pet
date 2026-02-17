import { useState, useEffect } from 'react';
import { 
  Plus, Edit2, Trash2, AlertCircle, Save, X,
  CreditCard, Check, AlertTriangle, Eye, EyeOff
} from 'lucide-react';
import api from '../api';
import { toast } from 'react-hot-toast';

const ICONES_DISPONIVEIS = [
  '💳', '🏦', '💰', '💵', '💸', '🏧',
  '💼', '🎯', '⚡', '🔒', '✨', '🌟',
  '📊', '💎', '🎁', '🔑', '⭐', '🚀'
];

function OperadorasCartao() {
  const [operadoras, setOperadoras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null);
  const [erro, setErro] = useState('');
  const [mostrarToken, setMostrarToken] = useState(false);
  
  // Form states
  const [formData, setFormData] = useState({
    nome: '',
    codigo: '',
    max_parcelas: 12,
    padrao: false,
    ativo: true,
    api_enabled: false,
    api_endpoint: '',
    api_token_encrypted: '',
    cor: '#00A868',
    icone: '💳'
  });

  useEffect(() => {
    carregarOperadoras();
  }, []);

  const carregarOperadoras = async () => {
    try {
      setLoading(true);
      const response = await api.get('/operadoras-cartao');
      setOperadoras(response.data);
    } catch (error) {
      console.error('Erro ao carregar operadoras:', error);
      toast.error('Erro ao carregar operadoras de cartão');
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (operadora = null) => {
    if (operadora) {
      setFormData({
        nome: operadora.nome,
        codigo: operadora.codigo || '',
        max_parcelas: operadora.max_parcelas,
        padrao: operadora.padrao,
        ativo: operadora.ativo,
        api_enabled: operadora.api_enabled,
        api_endpoint: operadora.api_endpoint || '',
        api_token_encrypted: operadora.api_token_encrypted || '',
        cor: operadora.cor || '#00A868',
        icone: operadora.icone || '💳'
      });
      setOperadoraSelecionada(operadora);
    } else {
      setFormData({
        nome: '',
        codigo: '',
        max_parcelas: 12,
        padrao: false,
        ativo: true,
        api_enabled: false,
        api_endpoint: '',
        api_token_encrypted: '',
        cor: '#00A868',
        icone: '💳'
      });
      setOperadoraSelecionada(null);
    }
    setModalAberto(true);
    setErro('');
    setMostrarToken(false);
  };

  const salvarOperadora = async (e) => {
    e.preventDefault();
    
    if (!formData.nome.trim()) {
      toast.error('Nome da operadora é obrigatório');
      return;
    }

    if (formData.max_parcelas < 1 || formData.max_parcelas > 24) {
      toast.error('Parcelas devem estar entre 1 e 24');
      return;
    }
    
    try {
      const dadosEnvio = {
        ...formData,
        nome: formData.nome.trim(),
        codigo: formData.codigo?.trim()?.toUpperCase() || null,
        api_endpoint: formData.api_endpoint?.trim() || null,
        api_token_encrypted: formData.api_token_encrypted?.trim() || null
      };

      if (operadoraSelecionada) {
        await api.put(`/operadoras-cartao/${operadoraSelecionada.id}`, dadosEnvio);
        toast.success('Operadora atualizada com sucesso!');
      } else {
        await api.post('/operadoras-cartao', dadosEnvio);
        toast.success('Operadora criada com sucesso!');
      }
      
      setModalAberto(false);
      carregarOperadoras();
    } catch (error) {
      console.error('Erro ao salvar:', error);
      const mensagem = error.response?.data?.detail || 'Erro ao salvar operadora';
      toast.error(mensagem);
      setErro(mensagem);
    }
  };

  const excluirOperadora = async (id) => {
    if (!window.confirm('Deseja realmente excluir esta operadora? Ela será desativada se houver vendas vinculadas.')) {
      return;
    }

    try {
      await api.delete(`/operadoras-cartao/${id}`);
      toast.success('Operadora removida com sucesso!');
      carregarOperadoras();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      const mensagem = error.response?.data?.detail || 'Erro ao excluir operadora';
      toast.error(mensagem);
    }
  };

  const getOperadoraPadraoInfo = () => {
    const padraoAtual = operadoras.find(op => op.padrao && op.ativo);
    if (!padraoAtual) return null;

    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-100 rounded-lg">
            <Check className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h3 className="font-medium text-emerald-900">Operadora Padrão</h3>
            <p className="text-sm text-emerald-700">
              <span className="font-medium">{padraoAtual.nome}</span> será pré-selecionada no PDV
            </p>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Operadoras de Cartão</h1>
        <p className="text-gray-600">
          Configure as operadoras de cartão disponíveis (Stone, Cielo, Rede, Getnet, etc)
        </p>
      </div>

      {/* Alertas */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-amber-900 mb-1">Importante</h3>
            <ul className="text-sm text-amber-700 space-y-1">
              <li>• Pelo menos uma operadora deve estar marcada como padrão e ativa</li>
              <li>• O PDV usará a operadora padrão automaticamente para vendas com cartão</li>
              <li>• Operadoras com vendas vinculadas não podem ser excluídas (apenas desativadas)</li>
            </ul>
          </div>
        </div>
      </div>

      {getOperadoraPadraoInfo()}

      {/* Botão Adicionar */}
      <div className="mb-6">
        <button
          onClick={() => abrirModal()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nova Operadora
        </button>
      </div>

      {/* Lista de Operadoras */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {operadoras.map((operadora) => {
          // 🛡️ Garantir que sempre use emoji (fallback se vier como componente React)
          const iconeOperadora = operadora.icone && !operadora.icone.startsWith('Fi') && !operadora.icone.startsWith('Bi')
            ? operadora.icone
            : '💳';
          
          return (
          <div
            key={operadora.id}
            className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${
              !operadora.ativo ? 'bg-gray-50 border-gray-300' : 'bg-white border-gray-200'
            } ${operadora.padrao ? 'ring-2 ring-emerald-500' : ''}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div
                  className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl"
                  style={{ backgroundColor: `${operadora.cor}20` }}
                >
                  {iconeOperadora}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    {operadora.nome}
                    {operadora.padrao && (
                      <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
                        Padrão
                      </span>
                    )}
                  </h3>
                  {operadora.codigo && (
                    <p className="text-xs text-gray-500 font-mono">{operadora.codigo}</p>
                  )}
                </div>
              </div>
              
              <div className={`px-2 py-1 rounded text-xs font-medium ${
                operadora.ativo 
                  ? 'bg-green-100 text-green-700' 
                  : 'bg-gray-200 text-gray-600'
              }`}>
                {operadora.ativo ? 'Ativo' : 'Inativo'}
              </div>
            </div>

            <div className="space-y-2 mb-4 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Parcelas máximas:</span>
                <span className="font-medium text-gray-900">{operadora.max_parcelas}x</span>
              </div>

              {operadora.api_enabled && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <span className="text-xs text-blue-600 flex items-center gap-1">
                    <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                    API Integrada
                  </span>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => abrirModal(operadora)}
                className="flex-1 bg-blue-50 text-blue-600 px-3 py-2 rounded hover:bg-blue-100 flex items-center justify-center gap-2 transition-colors text-sm"
              >
                <Edit2 className="w-4 h-4" />
                Editar
              </button>
              <button
                onClick={() => excluirOperadora(operadora.id)}
                className="flex-1 bg-red-50 text-red-600 px-3 py-2 rounded hover:bg-red-100 flex items-center justify-center gap-2 transition-colors text-sm"
              >
                <Trash2 className="w-4 h-4" />
                Excluir
              </button>
            </div>
          </div>
          );
        })}
      </div>

      {operadoras.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
          <CreditCard className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">Nenhuma operadora cadastrada</p>
          <p className="text-sm text-gray-500">Clique em "Nova Operadora" para começar</p>
        </div>
      )}

      {/* Modal */}
      {modalAberto && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
              <h2 className="text-xl font-bold text-gray-900">
                {operadoraSelecionada ? 'Editar Operadora' : 'Nova Operadora'}
              </h2>
              <button
                onClick={() => setModalAberto(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={salvarOperadora} className="p-6">
              {erro && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  <span className="text-sm text-red-700">{erro}</span>
                </div>
              )}

              {/* Informações Básicas */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Informações Básicas</h3>
                
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nome da Operadora *
                    </label>
                    <input
                      type="text"
                      value={formData.nome}
                      onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Ex: Stone, Cielo, Rede"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Código (sigla)
                    </label>
                    <input
                      type="text"
                      value={formData.codigo}
                      onChange={(e) => setFormData({ ...formData, codigo: e.target.value.toUpperCase() })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                      placeholder="Ex: STONE, CIELO"
                      maxLength={50}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Máximo de Parcelas *
                    </label>
                    <input
                      type="number"
                      value={formData.max_parcelas}
                      onChange={(e) => setFormData({ ...formData, max_parcelas: parseInt(e.target.value) || 1 })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      min="1"
                      max="24"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">Entre 1 e 24 parcelas</p>
                  </div>

                  <div className="space-y-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.padrao}
                        onChange={(e) => setFormData({ ...formData, padrao: e.target.checked })}
                        className="w-4 h-4 text-blue-600"
                      />
                      <span className="text-sm font-medium text-gray-700">Operadora Padrão</span>
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.ativo}
                        onChange={(e) => setFormData({ ...formData, ativo: e.target.checked })}
                        className="w-4 h-4 text-blue-600"
                      />
                      <span className="text-sm font-medium text-gray-700">Ativo</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Interface (Cor e Ícone) */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Interface</h3>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Cor
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={formData.cor}
                        onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
                        className="w-16 h-10 border border-gray-300 rounded cursor-pointer"
                      />
                      <input
                        type="text"
                        value={formData.cor}
                        onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
                        className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                        placeholder="#00A868"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Ícone
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {ICONES_DISPONIVEIS.map(icone => (
                        <button
                          key={icone}
                          type="button"
                          onClick={() => setFormData({ ...formData, icone })}
                          className={`w-10 h-10 rounded flex items-center justify-center text-xl transition-colors ${
                            formData.icone === icone
                              ? 'bg-blue-100 ring-2 ring-blue-500'
                              : 'bg-gray-100 hover:bg-gray-200'
                          }`}
                        >
                          {icone}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Integração API */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Integração API (Opcional)</h3>
                
                <label className="flex items-center gap-2 mb-4 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.api_enabled}
                    onChange={(e) => setFormData({ ...formData, api_enabled: e.target.checked })}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-sm font-medium text-gray-700">Habilitar integração via API</span>
                </label>

                {formData.api_enabled && (
                  <div className="space-y-4 pl-6 border-l-2 border-blue-200">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Endpoint da API
                      </label>
                      <input
                        type="url"
                        value={formData.api_endpoint}
                        onChange={(e) => setFormData({ ...formData, api_endpoint: e.target.value })}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                        placeholder="https://api.operadora.com/v1"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Token de Acesso
                      </label>
                      <div className="relative">
                        <input
                          type={mostrarToken ? 'text' : 'password'}
                          value={formData.api_token_encrypted}
                          onChange={(e) => setFormData({ ...formData, api_token_encrypted: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                          placeholder="Token será criptografado ao salvar"
                        />
                        <button
                          type="button"
                          onClick={() => setMostrarToken(!mostrarToken)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          {mostrarToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Botões */}
              <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => setModalAberto(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 transition-colors"
                >
                  <Save className="w-4 h-4" />
                  {operadoraSelecionada ? 'Salvar Alterações' : 'Criar Operadora'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default OperadorasCartao;
