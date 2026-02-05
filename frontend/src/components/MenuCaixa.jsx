import { useState, useEffect } from 'react';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Receipt,
  ArrowRightLeft,
  Clock,
  X,
  ChevronDown,
  RotateCcw,
  List,
  Eye,
  EyeOff
} from 'lucide-react';
import { obterCaixaAberto, obterResumoCaixa } from '../api/caixa';
import { ModalSuprimento, ModalSangria, ModalDespesa } from './ModaisCaixa';
import ModalFecharCaixa from './ModalFecharCaixa';
import ModalDevolucao from './ModalDevolucao';
import ModalMovimentacoesCaixa from './ModalMovimentacoesCaixa';

export default function MenuCaixa({ onAbrirCaixa }) {
  const [caixaAberto, setCaixaAberto] = useState(null);
  const [resumo, setResumo] = useState(null);
  const [menuAberto, setMenuAberto] = useState(false);
  const [modalAtivo, setModalAtivo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mostrarSaldoTopo, setMostrarSaldoTopo] = useState(false); // Press-to-reveal (topo)
  const [mostrarValores, setMostrarValores] = useState(false); // Toggle normal (resumo)

  useEffect(() => {
    carregarCaixa();
    
    // Atualizar a cada 30 segundos
    const interval = setInterval(carregarCaixa, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fechar olho do topo ao soltar o mouse
  useEffect(() => {
    const handleMouseUp = () => {
      setMostrarSaldoTopo(false);
    };
    
    if (mostrarSaldoTopo) {
      document.addEventListener('mouseup', handleMouseUp);
      return () => document.removeEventListener('mouseup', handleMouseUp);
    }
  }, [mostrarSaldoTopo]);

  // Resetar estados ao fechar menu
  const handleFecharMenu = () => {
    setMenuAberto(false);
    setMostrarValores(false);
    setMostrarSaldoTopo(false);
  };

  const carregarCaixa = async () => {
    try {
      const caixa = await obterCaixaAberto();
      setCaixaAberto(caixa);
      
      if (caixa) {
        const res = await obterResumoCaixa(caixa.id);
        setResumo(res);
      }
    } catch (error) {
      console.error('Erro ao carregar caixa:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOperacaoSucesso = () => {
    setModalAtivo(null);
    carregarCaixa();
  };

  const handleCaixaAberto = async () => {
    await onAbrirCaixa();
    // Aguardar um pouco e recarregar
    setTimeout(carregarCaixa, 500);
  };

  if (loading) {
    return (
      <div className="px-4 py-2 bg-gray-100 rounded-lg">
        <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
      </div>
    );
  }

  if (!caixaAberto) {
    return (
      <button
        onClick={handleCaixaAberto}
        className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
      >
        <DollarSign className="w-5 h-5" />
        <span>Abrir Caixa</span>
      </button>
    );
  }

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setMenuAberto(!menuAberto)}
          className="flex items-center space-x-3 px-4 py-2 bg-white border-2 border-green-500 rounded-lg hover:bg-green-50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span className="font-semibold text-gray-900">
              Caixa #{caixaAberto.numero_caixa}
            </span>
          </div>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${menuAberto ? 'rotate-180' : ''}`} />
        </button>

        {menuAberto && (
          <>
            {/* Overlay para fechar ao clicar fora */}
            <div
              className="fixed inset-0 z-40"
              onClick={handleFecharMenu}
            />

            {/* Menu Dropdown */}
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-50">
              {/* Header do Menu */}
              <div className="p-4 border-b bg-gradient-to-r from-green-50 to-blue-50">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="text-sm text-gray-600">Caixa #{caixaAberto.numero_caixa}</div>
                    <div className="text-lg font-bold text-gray-900">
                      {caixaAberto.usuario_nome}
                    </div>
                  </div>
                  <button
                    onClick={handleFecharMenu}
                    className="p-1 hover:bg-white rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center text-xs text-gray-500">
                    <Clock className="w-4 h-4 mr-1" />
                    Aberto em {new Date(caixaAberto.data_abertura).toLocaleString('pt-BR', { 
                      day: '2-digit', 
                      month: '2-digit', 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </div>
                  
                  {/* Saldo Atual com olho press-to-reveal */}
                  <div className="flex items-center space-x-2">
                    <div className="text-right">
                      <div className="text-xs text-gray-500">Saldo Atual</div>
                      <div className={`text-sm font-bold ${mostrarSaldoTopo ? 'text-green-600' : 'text-gray-400'}`}>
                        {mostrarSaldoTopo ? `R$ ${resumo?.totais?.saldo_atual?.toFixed(2) || '0,00'}` : '••••••'}
                      </div>
                    </div>
                    <button
                      onMouseDown={() => setMostrarSaldoTopo(true)}
                      className="p-1 hover:bg-blue-100 rounded transition-colors"
                    >
                      {mostrarSaldoTopo ? (
                        <Eye className="w-4 h-4 text-blue-600" />
                      ) : (
                        <EyeOff className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Resumo */}
              {resumo && (
                <div className="p-4 border-b bg-gray-50">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-bold text-gray-900">Resumo do Movimento</h4>
                    <button
                      onClick={() => setMostrarValores(!mostrarValores)}
                      className="p-1 hover:bg-gray-200 rounded transition-colors"
                    >
                      {mostrarValores ? (
                        <Eye className="w-4 h-4 text-blue-600" />
                      ) : (
                        <EyeOff className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="text-gray-600">Abertura</div>
                      <div className={`font-semibold ${mostrarValores ? 'text-gray-900' : 'text-gray-300'}`}>
                        {mostrarValores ? `R$ ${caixaAberto.valor_abertura.toFixed(2)}` : '••••••'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Entradas</div>
                      <div className={`font-semibold ${mostrarValores ? 'text-green-600' : 'text-green-300'}`}>
                        {mostrarValores ? `+ R$ ${resumo.totais.vendas.toFixed(2)}` : '••••••'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Suprimentos</div>
                      <div className={`font-semibold ${mostrarValores ? 'text-green-600' : 'text-green-300'}`}>
                        {mostrarValores ? `+ R$ ${resumo.totais.suprimentos.toFixed(2)}` : '••••••'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Sangrias</div>
                      <div className={`font-semibold ${mostrarValores ? 'text-orange-600' : 'text-orange-300'}`}>
                        {mostrarValores ? `- R$ ${resumo.totais.sangrias.toFixed(2)}` : '••••••'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Despesas</div>
                      <div className={`font-semibold ${mostrarValores ? 'text-red-600' : 'text-red-300'}`}>
                        {mostrarValores ? `- R$ ${resumo.totais.despesas.toFixed(2)}` : '••••••'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Ações */}
              <div className="p-2">
                <button
                  onClick={() => {
                    setModalAtivo('suprimento');
                    setMenuAberto(false);
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-green-50 rounded-lg transition-colors text-left"
                >
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <TrendingUp className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">Suprimento</div>
                    <div className="text-xs text-gray-500">Adicionar dinheiro ao caixa</div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setModalAtivo('sangria');
                    setMenuAberto(false);
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-orange-50 rounded-lg transition-colors text-left"
                >
                  <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                    <TrendingDown className="w-5 h-5 text-orange-600" />
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">Sangria</div>
                    <div className="text-xs text-gray-500">Retirar dinheiro do caixa</div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setModalAtivo('despesa');
                    setMenuAberto(false);
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-red-50 rounded-lg transition-colors text-left"
                >
                  <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                    <Receipt className="w-5 h-5 text-red-600" />
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">Despesa</div>
                    <div className="text-xs text-gray-500">Registrar pagamento de despesa</div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setModalAtivo('devolucao');
                    setMenuAberto(false);
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-purple-50 rounded-lg transition-colors text-left"
                >
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <RotateCcw className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">Devolução</div>
                    <div className="text-xs text-gray-500">Estornar venda e devolver ao estoque</div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setModalAtivo('movimentacoes');
                    setMenuAberto(false);
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-blue-50 rounded-lg transition-colors text-left"
                >
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <List className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">Extrato do Caixa</div>
                    <div className="text-xs text-gray-500">Ver todas as movimentações</div>
                  </div>
                </button>
              </div>

              {/* Fechar Caixa */}
              <div className="p-4 border-t">
                <button
                  onClick={() => {
                    setModalAtivo('fechar');
                    setMenuAberto(false);
                  }}
                  className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                  Fechar Caixa
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modais de Operações */}
      {modalAtivo === 'suprimento' && (
        <ModalSuprimento
          caixaId={caixaAberto.id}
          onClose={() => setModalAtivo(null)}
          onSucesso={handleOperacaoSucesso}
        />
      )}

      {modalAtivo === 'sangria' && (
        <ModalSangria
          caixaId={caixaAberto.id}
          saldoAtual={resumo?.totais?.saldo_atual || 0}
          onClose={() => setModalAtivo(null)}
          onSucesso={handleOperacaoSucesso}
        />
      )}

      {modalAtivo === 'despesa' && (
        <ModalDespesa
          caixaId={caixaAberto.id}
          onClose={() => setModalAtivo(null)}
          onSucesso={handleOperacaoSucesso}
        />
      )}

      {modalAtivo === 'fechar' && (
        <ModalFecharCaixa
          caixaId={caixaAberto.id}
          onClose={() => setModalAtivo(null)}
          onSuccess={() => {
            setModalAtivo(null);
            carregarCaixa(); // Recarrega para mostrar que não há mais caixa aberto
          }}
        />
      )}

      {modalAtivo === 'devolucao' && (
        <ModalDevolucao
          caixaId={caixaAberto.id}
          onClose={() => setModalAtivo(null)}
          onSucesso={handleOperacaoSucesso}
        />
      )}

      {modalAtivo === 'movimentacoes' && (
        <ModalMovimentacoesCaixa
          caixaId={caixaAberto.id}
          onClose={() => setModalAtivo(null)}
        />
      )}
    </>
  );
}
