import React, { useState, useEffect } from 'react';
import { X, ChevronDown, Loader2 } from 'lucide-react';
import api from '../../api';
import toast from 'react-hot-toast';
import { ehRacao } from '../../helpers/deteccaoRacao';  // 🆕 Helper centralizado
import './ModalCalculadoraRacaoPDV.css';

/**
 * Modal de Calculadora de Ração no PDV
 * ====================================
 * 
 * COMPORTAMENTO CRÍTICO:
 * 1. Abre automaticamente ao adicionar uma ração ao carrinho
 * 2. Ração selecionada por padrão = ÚLTIMA ração adicionada
 * 3. Dropdown permite selecionar manualmente qualquer ração do carrinho
 * 4. Botão "Calcular" chama POST /internal/racao/calcular
 * 5. Resultados exibidos no próprio modal
 * 6. Erro silencioso - NÃO quebra o PDV
 * 7. Se fechado, NÃO reabre para a mesma ração
 * 
 * ESCOPO DO MODAL:
 * - Exibir APENAS informações objetivas
 * - Consumo diário, duração, custo diário, custo mensal, custo/kg
 * - NÃO fazer comparações
 * - NÃO sugerir trocas
 * - NÃO tomar decisões
 */
export default function ModalCalculadoraRacaoPDV({
  itensCarrinho = [],
  onClose = () => {},
  isOpen = false,
  racaoIdFechada = null  // ID da ração que foi fechada (não reabre)
}) {
  // Estados
  const [racaoSelecionadaId, setRacaoSelecionadaId] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [resultados, setResultados] = useState(null);
  const [erroCalculo, setErroCalculo] = useState(null);
  const [mostraDropdown, setMostraDropdown] = useState(false);

  // Filtrar apenas rações do carrinho usando helper centralizado
  const racoes = itensCarrinho.filter(item => ehRacao(item));
  
  // Debug: Log das rações encontradas
  useEffect(() => {
    if (isOpen) {
      console.log('🥫 Modal: Rações encontradas:', racoes.length);
      racoes.forEach((r, i) => {
        console.log(`  ${i + 1}. ${r.produto_nome} - peso_embalagem: ${r.peso_embalagem}`);
      });
    }
  }, [isOpen, racoes.length]);

  // Quando o modal abre ou racões mudam, selecionar a ÚLTIMA ração
  useEffect(() => {
    if (isOpen && racoes.length > 0) {
      // Selecionar a última ração APENAS se não foi fechada
      const ultimaRacao = racoes[racoes.length - 1];
      
      // Se essa ração foi fechada antes, não reabrir
      if (racaoIdFechada !== ultimaRacao.produto_id) {
        setRacaoSelecionadaId(ultimaRacao.produto_id);
        setResultados(null);
        setErroCalculo(null);
        setCarregando(false);
      }
    }
  }, [isOpen, racoes.length, racaoIdFechada]);

  // Buscar ração selecionada
  const racaoAtual = racoes.find(r => r.produto_id === racaoSelecionadaId);

  // Função para calcular consumo
  const calcularConsumo = async () => {
    if (!racaoAtual) {
      setErroCalculo('Ração não selecionada');
      return;
    }

    // Validar dados básicos
    const pesoEmbalagem = racaoAtual.peso_embalagem || racaoAtual.peso_pacote_kg;
    if (!pesoEmbalagem || !racaoAtual.preco_unitario) {
      console.error('❌ Modal: Dados da ração incompletos', {
        peso_embalagem: racaoAtual.peso_embalagem,
        peso_pacote_kg: racaoAtual.peso_pacote_kg,
        preco_unitario: racaoAtual.preco_unitario
      });
      setErroCalculo('Dados da ração incompletos');
      return;
    }

    try {
      setCarregando(true);
      setErroCalculo(null);
      setResultados(null);

      // Preparar payload para calcular
      const pesoEmbalagem = racaoAtual.peso_embalagem || racaoAtual.peso_pacote_kg || 1;
      const payload = {
        especie: 'cao', // Padrão (pode ser extraído do pet se associado)
        peso_kg: 15, // Padrão (idealmente viria do pet)
        fase: 'adulto', // Padrão
        porte: 'medio', // Padrão
        tipo_racao: 'premium', // Padrão
        peso_pacote_kg: parseFloat(pesoEmbalagem),
        preco_pacote: parseFloat(racaoAtual.preco_unitario) || 0
      };
      
      console.log('🧑 Modal: Enviando payload:', payload);

      // Chamar endpoint da calculadora
      const response = await api.post('/internal/racao/calcular', payload);
      
      if (response.data) {
        setResultados(response.data);
      } else {
        setErroCalculo('Sem resposta do servidor');
      }
    } catch (error) {
      console.error('Erro ao calcular:', error);
      // Erro silencioso - não quebra o PDV
      setErroCalculo(null); // Não mostrar erro para não assustar o caixa
    } finally {
      setCarregando(false);
    }
  };

  // Se não tem rações no carrinho, não exibir modal
  if (!isOpen || racoes.length === 0) {
    if (isOpen && racoes.length === 0) {
      console.warn('⚠️ Modal: isOpen=true mas racoes.length=0');
    }
    return null;
  }
  
  console.log('✅ Modal: Renderizando com', racoes.length, 'rações');

  return (
    <div className="fixed inset-0 bg-black bg-opacity-20 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🥫</span>
            <div>
              <h2 className="text-lg font-bold">Calculadora de Ração</h2>
              <p className="text-sm text-blue-100">Informações rápidas</p>
            </div>
          </div>
          <button
            onClick={() => {
              // Marcar essa ração como fechada para não reabre automático
              if (racaoAtual) {
                // Passar para componente pai que essa ração foi fechada
              }
              onClose();
            }}
            className="p-1 hover:bg-blue-400 rounded-lg transition-colors"
            title="Fechar"
          >
            <X size={24} />
          </button>
        </div>

        {/* Conteúdo do Modal */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          
          {/* Seleção de Ração */}
          {racoes.length > 1 && (
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-gray-700">
                Selecionar Ração
              </label>
              <div className="relative">
                <button
                  onClick={() => setMostraDropdown(!mostraDropdown)}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-left flex items-center justify-between hover:border-blue-500 transition-colors"
                >
                  <span className="text-gray-900 font-medium">
                    {racaoAtual?.produto_nome || 'Selecione uma ração'}
                  </span>
                  <ChevronDown 
                    size={20} 
                    className={`text-gray-500 transition-transform ${mostraDropdown ? 'rotate-180' : ''}`}
                  />
                </button>

                {/* Dropdown */}
                {mostraDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-300 rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
                    {racoes.map((racao, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setRacaoSelecionadaId(racao.produto_id);
                          setMostraDropdown(false);
                          setResultados(null);
                        }}
                        className={`w-full px-4 py-3 text-left border-b last:border-b-0 hover:bg-blue-50 transition-colors ${
                          racao.produto_id === racaoSelecionadaId 
                            ? 'bg-blue-100 border-l-4 border-l-blue-600' 
                            : ''
                        }`}
                      >
                        <div className="font-medium text-gray-900">
                          {racao.produto_nome}
                        </div>
                        <div className="text-xs text-gray-500">
                          {(racao.peso_embalagem || racao.peso_pacote_kg) ? `${(racao.peso_embalagem || racao.peso_pacote_kg)}kg` : ''} • 
                          R$ {(racao.preco_unitario || 0).toFixed(2)}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Informações da Ração Selecionada */}
          {racaoAtual && (
            <div className="bg-blue-50 rounded-lg p-4 space-y-2">
              <h3 className="font-bold text-gray-900">{racaoAtual.produto_nome}</h3>
              <div className="text-sm text-gray-700 space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-600">Pacote:</span>
                  <span className="font-medium">
                    {racaoAtual.peso_pacote_kg ? `${racaoAtual.peso_pacote_kg}kg` : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Preço:</span>
                  <span className="font-medium text-blue-600">
                    R$ {(racaoAtual.preco_unitario || 0).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Botão Calcular */}
          <button
            onClick={calcularConsumo}
            disabled={carregando || !racaoAtual}
            className={`w-full py-3 rounded-lg font-semibold transition-colors ${
              carregando || !racaoAtual
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
            }`}
          >
            {carregando ? (
              <div className="flex items-center justify-center gap-2">
                <Loader2 size={18} className="animate-spin" />
                Calculando...
              </div>
            ) : (
              '📊 Calcular Consumo'
            )}
          </button>

          {/* Resultados */}
          {resultados && (
            <div className="bg-green-50 rounded-lg p-4 space-y-3 border border-green-200">
              <h3 className="font-bold text-green-900 text-center">✅ Cálculo Realizado</h3>
              
              <div className="grid grid-cols-2 gap-3 text-sm">
                {/* Consumo Diário */}
                <div className="bg-white rounded p-3 border border-green-100">
                  <div className="text-gray-600 text-xs font-semibold">Consumo Diário</div>
                  <div className="text-lg font-bold text-green-700">
                    {(resultados.consumo_diario_gramas || 0).toFixed(0)}g
                  </div>
                </div>

                {/* Duração do Pacote */}
                <div className="bg-white rounded p-3 border border-green-100">
                  <div className="text-gray-600 text-xs font-semibold">Duração</div>
                  <div className="text-lg font-bold text-green-700">
                    {(resultados.duracao_pacote_dias || 0).toFixed(1)}d
                  </div>
                </div>

                {/* Custo Diário */}
                <div className="bg-white rounded p-3 border border-green-100">
                  <div className="text-gray-600 text-xs font-semibold">Custo/Dia</div>
                  <div className="text-lg font-bold text-green-700">
                    R$ {(resultados.custo_diario || 0).toFixed(2)}
                  </div>
                </div>

                {/* Custo Mensal */}
                <div className="bg-white rounded p-3 border border-green-100">
                  <div className="text-gray-600 text-xs font-semibold">Custo/Mês</div>
                  <div className="text-lg font-bold text-green-700">
                    R$ {(resultados.custo_mensal || 0).toFixed(2)}
                  </div>
                </div>

                {/* Custo por KG */}
                <div className="bg-white rounded p-3 border border-green-100 col-span-2">
                  <div className="text-gray-600 text-xs font-semibold">Custo/kg</div>
                  <div className="text-lg font-bold text-green-700">
                    R$ {(resultados.custo_por_kg || 0).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Mensagem de Erro Silencioso */}
          {erroCalculo && (
            <div className="bg-yellow-50 rounded-lg p-3 text-sm text-yellow-700 border border-yellow-200">
              ⚠️ Não foi possível calcular. Tente novamente.
            </div>
          )}

          {/* Nota Informativa */}
          <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600 border border-gray-200 italic">
            💡 Valores calculados com base em dados padrão. 
            Para análises personalizadas, utilize a calculadora completa.
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 border-t px-6 py-3 flex justify-end gap-3 flex-shrink-0">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg font-medium transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
