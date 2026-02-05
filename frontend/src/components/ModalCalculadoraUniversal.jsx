import { useState, useEffect } from 'react';
import { X, ChevronDown, Loader2 } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import api from '../api';
import toast from 'react-hot-toast';
import { ehRacao } from '../helpers/deteccaoRacao';

/**
 * Modal Universal da Calculadora de Ração
 * ========================================
 * 
 * Funciona em 2 modos:
 * 1. PDV: Usa rações do carrinho, autopreenche pet vinculado
 * 2. Outras telas: Autocomplete para buscar rações manualmente
 */
export default function ModalCalculadoraUniversal({
  isOpen = false,
  onClose = () => {},
  // Props do PDV (quando estiver no contexto do PDV)
  itensCarrinho = [],
  clienteId = null
}) {
  const location = useLocation();
  const estaNoPDV = location.pathname === '/pdv';

  // Estados
  const [racaoSelecionadaId, setRacaoSelecionadaId] = useState(null);
  const [racaoSelecionada, setRacaoSelecionada] = useState(null);
  const [petSelecionado, setPetSelecionado] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [resultados, setResultados] = useState(null);
  const [erroCalculo, setErroCalculo] = useState(null);
  const [mostraDropdown, setMostraDropdown] = useState(false);

  // Estados para modo FORA DO PDV
  const [buscaRacao, setBuscaRacao] = useState('');
  const [racoesDisponiveis, setRacoesDisponiveis] = useState([]);
  const [buscandoRacoes, setBuscandoRacoes] = useState(false);

  // Estados do formulário
  const [form, setForm] = useState({
    peso_pet_kg: '',
    idade_meses: '',
    nivel_atividade: 'normal'
  });

  // Filtrar rações do carrinho (modo PDV)
  const racoesCarrinho = estaNoPDV 
    ? (() => {
        try {
          const pdvData = sessionStorage.getItem('pdv_calculadora_data');
          console.log('🔍 Calculadora Universal - Dados do PDV:', pdvData);
          if (pdvData) {
            const { itens } = JSON.parse(pdvData);
            const racoes = (itens || []).filter(item => ehRacao(item));
            console.log('🥫 Rações encontradas:', racoes);
            return racoes;
          }
        } catch (e) {
          console.error('Erro ao ler dados do PDV:', e);
        }
        return [];
      })()
    : [];

  // Buscar rações disponíveis (modo FORA DO PDV)
  useEffect(() => {
    if (!estaNoPDV && buscaRacao.length >= 2) {
      const timer = setTimeout(async () => {
        setBuscandoRacoes(true);
        try {
          const response = await api.get('/produtos', {
            params: { busca: buscaRacao }
          });
          
          const produtos = response.data.items || response.data.produtos || [];
          // Filtrar apenas rações (que têm peso_embalagem)
          const racoes = produtos.filter(p => p.peso_embalagem && p.peso_embalagem > 0);
          setRacoesDisponiveis(racoes);
        } catch (error) {
          console.error('Erro ao buscar rações:', error);
        } finally {
          setBuscandoRacoes(false);
        }
      }, 300);
      return () => clearTimeout(timer);
    } else {
      setRacoesDisponiveis([]);
    }
  }, [buscaRacao, estaNoPDV]);

  // Selecionar última ração ao abrir (modo PDV)
  useEffect(() => {
    if (isOpen && estaNoPDV && racoesCarrinho.length > 0) {
      const ultimaRacao = racoesCarrinho[racoesCarrinho.length - 1];
      setRacaoSelecionadaId(ultimaRacao.produto_id);
      setRacaoSelecionada(ultimaRacao);
      
      // Buscar pet se existir
      if (ultimaRacao.pet_id) {
        buscarPet(ultimaRacao.pet_id);
      }
    }
  }, [isOpen, racoesCarrinho.length, estaNoPDV]);

  // Buscar dados do pet
  const buscarPet = async (petId) => {
    try {
      const response = await api.get(`/pets/${petId}`);
      const pet = response.data;
      
      setPetSelecionado(pet);
      
      // Autopreencher form
      setForm({
        ...form,
        peso_pet_kg: pet.peso_kg || pet.peso || '',
        idade_meses: pet.idade_meses || pet.idade_aproximada || ''
      });
    } catch (error) {
      console.error('Erro ao buscar pet:', error);
    }
  };

  // Calcular consumo
  const calcularConsumo = async () => {
    console.log('🔍 Iniciando cálculo...');
    console.log('📦 Ração selecionada:', racaoSelecionada);
    console.log('📝 Formulário:', form);
    
    // Usar racaoSelecionada diretamente ao invés de buscar na lista
    const racao = racaoSelecionada;
    
    if (!racao) {
      console.log('❌ Nenhuma ração selecionada');
      toast.error('Selecione uma ração');
      return;
    }

    const pesoEmbalagem = racao.peso_embalagem || racao.peso_pacote_kg;
    const precoVenda = racao.preco_venda || racao.preco_unitario;
    
    console.log('⚖️ Peso embalagem:', pesoEmbalagem);
    console.log('💰 Preço:', precoVenda);
    
    if (!pesoEmbalagem || !precoVenda) {
      console.log('❌ Dados incompletos da ração');
      toast.error('Dados da ração incompletos');
      return;
    }

    if (!form.peso_pet_kg) {
      console.log('❌ Peso do pet não informado');
      toast.error('Informe o peso do pet');
      return;
    }

    try {
      setCarregando(true);
      setErroCalculo(null);
      setResultados(null);

      const payload = {
        especie: 'cao',
        peso_kg: parseFloat(form.peso_pet_kg),
        fase: 'adulto',
        porte: 'medio',
        tipo_racao: 'premium',
        peso_pacote_kg: parseFloat(pesoEmbalagem),
        preco_pacote: parseFloat(precoVenda)
      };

      console.log('📤 Enviando payload:', payload);
      const response = await api.post('/internal/racao/calcular', payload);
      
      console.log('📥 Resposta recebida:', response.data);
      if (response.data) {
        setResultados(response.data);
        toast.success('Cálculo realizado!');
      }
    } catch (error) {
      console.error('❌ Erro ao calcular:', error);
      toast.error('Erro ao calcular. Tente novamente.');
    } finally {
      setCarregando(false);
    }
  };

  // Selecionar ração do autocomplete
  const selecionarRacaoAutocomplete = (racao) => {
    setRacaoSelecionadaId(racao.id);
    setRacaoSelecionada(racao);
    setBuscaRacao(`${racao.nome} - ${racao.peso_embalagem}kg`);
    setMostraDropdown(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🥫</span>
            <div>
              <h2 className="text-xl font-bold">Calculadora de Ração</h2>
              <p className="text-sm text-orange-100">
                {estaNoPDV ? 'Rações do carrinho' : 'Buscar ração manualmente'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-orange-400 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Conteúdo */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Seleção de Ração */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">
              {estaNoPDV ? 'Ração do Carrinho' : 'Buscar Ração'} *
            </label>
            
            {estaNoPDV ? (
              /* Input com autocomplete de rações do carrinho */
              racoesCarrinho.length > 0 ? (
                <div className="relative">
                  <input
                    type="text"
                    value={racaoSelecionada?.produto_nome || ''}
                    readOnly
                    className="w-full px-4 py-3 pr-10 bg-gray-50 border-2 border-gray-300 rounded-lg text-gray-700 font-medium cursor-pointer"
                    placeholder="Nenhuma ração no carrinho"
                  />
                  <button
                    type="button"
                    onClick={() => setMostraDropdown(!mostraDropdown)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                  >
                    <ChevronDown size={20} className={`transition-transform ${mostraDropdown ? 'rotate-180' : ''}`} />
                  </button>

                  {mostraDropdown && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-white border-2 border-gray-300 rounded-lg shadow-xl z-10 max-h-48 overflow-y-auto">
                      {racoesCarrinho.map((racao, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => {
                            setRacaoSelecionadaId(racao.produto_id);
                            setRacaoSelecionada(racao);
                            setMostraDropdown(false);
                            if (racao.pet_id) buscarPet(racao.pet_id);
                          }}
                          className={`w-full px-4 py-3 text-left hover:bg-orange-50 transition-colors ${
                            racao.produto_id === racaoSelecionadaId ? 'bg-orange-100 border-l-4 border-l-orange-600' : ''
                          }`}
                        >
                          <div className="font-medium">{racao.produto_nome}</div>
                          <div className="text-xs text-gray-500">
                            {racao.peso_embalagem}kg • R$ {racao.preco_unitario.toFixed(2)}
                            {racao.pet_id && ' • 🐾 Pet vinculado'}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="px-4 py-3 bg-yellow-50 border-2 border-yellow-300 rounded-lg text-yellow-700">
                  Adicione rações ao carrinho para calcular
                </div>
              )
            ) : (
              /* Autocomplete de rações - Modo busca manual */
              <div className="space-y-2">
                <div className="relative">
                  <input
                    type="text"
                    value={buscaRacao}
                    onChange={(e) => setBuscaRacao(e.target.value)}
                    onFocus={() => racoesDisponiveis.length > 0 && setMostraDropdown(true)}
                    placeholder="Digite para buscar ração..."
                    className="w-full px-4 py-3 pr-20 border-2 border-gray-300 rounded-lg focus:border-orange-500 focus:ring-2 focus:ring-orange-200"
                  />
                  
                  {buscandoRacoes ? (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                      <Loader2 size={20} className="animate-spin text-orange-500" />
                    </div>
                  ) : racoesDisponiveis.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setMostraDropdown(!mostraDropdown)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    >
                      <ChevronDown size={20} className={`transition-transform ${mostraDropdown ? 'rotate-180' : ''}`} />
                    </button>
                  )}
                </div>

                {mostraDropdown && racoesDisponiveis.length > 0 && (
                  <div className="bg-white border-2 border-gray-300 rounded-lg shadow-xl max-h-64 overflow-y-auto">
                    {racoesDisponiveis.map(racao => (
                      <button
                        key={racao.id}
                        type="button"
                        onClick={() => selecionarRacaoAutocomplete(racao)}
                        className={`w-full px-4 py-3 text-left hover:bg-orange-50 transition-colors border-b last:border-b-0 ${
                          racao.id === racaoSelecionadaId ? 'bg-orange-100 border-l-4 border-l-orange-600' : ''
                        }`}
                      >
                        <div className="font-medium">{racao.nome}</div>
                        <div className="text-xs text-gray-500">
                          {racao.peso_embalagem}kg • R$ {racao.preco_venda?.toFixed(2)}
                          {racao.classificacao_racao && ` • ${racao.classificacao_racao}`}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Dados do Pet */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Peso do Pet (kg) *
              </label>
              <input
                type="number"
                step="0.1"
                value={form.peso_pet_kg}
                onChange={(e) => setForm({...form, peso_pet_kg: e.target.value})}
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-orange-500 focus:ring-2 focus:ring-orange-200"
                placeholder="Ex: 8.5"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Idade (meses)
              </label>
              <input
                type="number"
                value={form.idade_meses}
                onChange={(e) => setForm({...form, idade_meses: e.target.value})}
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-orange-500 focus:ring-2 focus:ring-orange-200"
                placeholder="Ex: 24"
              />
            </div>
          </div>

          {/* Pet vinculado (info) */}
          {estaNoPDV && petSelecionado && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-blue-800">
                <span className="text-xl">🐕</span>
                <span className="font-medium">{petSelecionado.nome}</span>
              </div>
              <div className="text-sm text-blue-600 mt-1">
                Dados carregados automaticamente do cadastro
              </div>
            </div>
          )}

          {/* Resultados */}
          {resultados && (
            <div className="bg-green-50 border-2 border-green-200 rounded-xl p-6 space-y-4">
              <h3 className="text-lg font-bold text-green-800 flex items-center gap-2">
                <span>✅</span> Resultados do Cálculo
              </h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-lg p-4">
                  <div className="text-sm text-gray-600">Duração</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {Math.floor(resultados.duracao_pacote_dias)} dias
                  </div>
                  <div className="text-xs text-gray-500">
                    {(resultados.duracao_pacote_dias / 30).toFixed(1)} meses
                  </div>
                </div>

                <div className="bg-white rounded-lg p-4">
                  <div className="text-sm text-gray-600">Custo/dia</div>
                  <div className="text-2xl font-bold text-gray-900">
                    R$ {resultados.custo_diario?.toFixed(2)}
                  </div>
                </div>

                <div className="bg-white rounded-lg p-4">
                  <div className="text-sm text-gray-600">Custo/mês</div>
                  <div className="text-2xl font-bold text-gray-900">
                    R$ {resultados.custo_mensal?.toFixed(2)}
                  </div>
                </div>

                <div className="bg-white rounded-lg p-4">
                  <div className="text-sm text-gray-600">Consumo diário</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {resultados.consumo_diario_gramas?.toFixed(0)}g
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 border-t px-6 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-6 py-2 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors font-medium"
          >
            Fechar
          </button>
          <button
            onClick={calcularConsumo}
            disabled={carregando}
            className="px-6 py-3 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {carregando ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                Calculando...
              </>
            ) : (
              <>
                🧮 Calcular Consumo
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
