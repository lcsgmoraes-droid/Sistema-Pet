import { useState, useEffect, useRef } from "react";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Receipt,
  Clock,
  X,
  ChevronDown,
  RotateCcw,
  List,
  Eye,
  EyeOff,
  Users,
} from "lucide-react";
import { obterResumoCaixa } from "../api/caixa";
import { ModalSuprimento, ModalSangria, ModalDespesa } from "./ModaisCaixa";
import ModalFecharCaixa from "./ModalFecharCaixa";
import ModalDevolucao from "./ModalDevolucao";
import ModalMovimentacoesCaixa from "./ModalMovimentacoesCaixa";
import { getNumeroVendaParaExibicao, podeAbrirDevolucaoVenda } from "../utils/pdvReturnEligibility";
import { precisaConsultarResumoCaixa, publicarEventoCaixa } from "../utils/caixaAbertoMonitor";
import { formatMoneyBRL } from "../utils/formatters";

export default function MenuCaixa({
  abrirDevolucaoSignal = 0,
  onAbrirCaixa,
  onDevolucaoSucesso,
  vendaParaDevolucao = null,
  caixaAberto,
  contextoCaixa,
  statusConsultaCaixa,
  atualizandoCaixa,
  atualizarCaixa,
}) {
  const [resumo, setResumo] = useState(null);
  const [menuAberto, setMenuAberto] = useState(false);
  const [modalAtivo, setModalAtivo] = useState(null);
  const [mostrarSaldoTopo, setMostrarSaldoTopo] = useState(false); // Press-to-reveal (topo)
  const [mostrarValores, setMostrarValores] = useState(false); // Toggle normal (resumo)
  const [resumoKey, setResumoKey] = useState(0);
  const [statusResumo, setStatusResumo] = useState("carregando");
  const ultimoSignalDevolucaoRef = useRef(0);
  const vendaAtualPodeAbrirDevolucao = podeAbrirDevolucaoVenda(vendaParaDevolucao);
  const precisaResumo = precisaConsultarResumoCaixa({ menuAberto, mostrarSaldoTopo, modalAtivo });

  useEffect(() => {
    if (!abrirDevolucaoSignal || ultimoSignalDevolucaoRef.current === abrirDevolucaoSignal) {
      return;
    }

    ultimoSignalDevolucaoRef.current = abrirDevolucaoSignal;
    setModalAtivo("devolucao");
    setMenuAberto(false);
  }, [abrirDevolucaoSignal]);

  useEffect(() => {
    setResumo(null);
    setStatusResumo("carregando");
    setMenuAberto(false);
    setModalAtivo((ativo) => (ativo === "devolucao" ? ativo : null));
  }, [caixaAberto?.id]);

  useEffect(() => {
    if (!caixaAberto?.id || !precisaResumo) return;
    const controller = new AbortController();
    setStatusResumo("carregando");
    void obterResumoCaixa(caixaAberto.id, { signal: controller.signal })
      .then((dados) => {
        if (!controller.signal.aborted) {
          setResumo(dados);
          setStatusResumo("pronto");
        }
      })
      .catch((erro) => {
        if (!controller.signal.aborted) {
          setStatusResumo("erro");
          console.error("Erro ao carregar resumo do caixa:", erro);
        }
      });
    return () => {
      controller.abort();
    };
  }, [caixaAberto, precisaResumo, resumoKey]);

  // Fechar olho do topo ao soltar o mouse
  useEffect(() => {
    const handleMouseUp = () => {
      setMostrarSaldoTopo(false);
    };

    if (mostrarSaldoTopo) {
      document.addEventListener("mouseup", handleMouseUp);
      return () => document.removeEventListener("mouseup", handleMouseUp);
    }
  }, [mostrarSaldoTopo]);

  // Resetar estados ao fechar menu
  const handleFecharMenu = () => {
    setMenuAberto(false);
    setMostrarValores(false);
    setMostrarSaldoTopo(false);
  };

  const handleOperacaoSucesso = () => {
    setModalAtivo(null);
    publicarEventoCaixa("movimentacao", { contextoCaixa, caixaId: caixaAberto?.id });
    setResumoKey((valor) => valor + 1);
    void atualizarCaixa();
  };

  const handleDevolucaoSucesso = (devolucao) => {
    handleOperacaoSucesso();
    void onDevolucaoSucesso?.(devolucao);
  };

  const handleCaixaAberto = async () => {
    await onAbrirCaixa();
  };

  // A troca do estado do caixa não deve desmontar uma devolução em andamento.
  const modalDevolucao = modalAtivo === "devolucao" && (
    <ModalDevolucao
      key="devolucao"
      caixaId={caixaAberto?.id}
      vendaInicial={vendaAtualPodeAbrirDevolucao ? vendaParaDevolucao : null}
      onClose={() => setModalAtivo(null)}
      onSucesso={handleDevolucaoSucesso}
    />
  );

  if (statusConsultaCaixa === "carregando") {
    return (
      <>
        <div className="flex h-10 w-full min-w-[138px] items-center rounded-lg bg-slate-100 px-3 shadow-sm sm:w-auto">
          <div className="h-5 w-full animate-pulse rounded-lg bg-slate-200"></div>
        </div>
        {modalDevolucao}
      </>
    );
  }

  if (!caixaAberto && statusConsultaCaixa === "erro") {
    return (
      <>
        <button
          type="button"
          disabled={atualizandoCaixa}
          onClick={() => atualizarCaixa()}
          className="inline-flex h-10 items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 text-sm font-semibold text-amber-900 disabled:opacity-50"
        >
          <RotateCcw className={`h-4 w-4 ${atualizandoCaixa ? "animate-spin" : ""}`} />
          Verificar caixa
        </button>
        {modalDevolucao}
      </>
    );
  }

  if (!caixaAberto) {
    return (
      <>
        <button
          onClick={handleCaixaAberto}
          className="inline-flex h-10 w-full min-w-[138px] items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-emerald-700 sm:w-auto"
        >
          <DollarSign className="h-4 w-4" />
          <span>Abrir Caixa</span>
        </button>
        {modalDevolucao}
      </>
    );
  }

  return (
    <>
      <div className="relative w-full sm:w-auto">
        <button
          onClick={() => setMenuAberto(!menuAberto)}
          className="inline-flex h-10 w-full min-w-[150px] items-center justify-between gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3.5 text-sm font-semibold text-slate-800 shadow-sm transition-colors hover:border-emerald-300 hover:bg-white sm:w-auto"
        >
          <div className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 rounded-full bg-green-500"></div>
            <span className="font-semibold text-gray-900">Caixa #{caixaAberto.numero_caixa}</span>
          </div>
          <ChevronDown
            className={`h-4 w-4 text-gray-400 transition-transform ${menuAberto ? "rotate-180" : ""}`}
          />
        </button>

        {menuAberto && (
          <>
            {/* Overlay para fechar ao clicar fora */}
            <div className="fixed inset-0 z-40" onClick={handleFecharMenu} />

            {/* Menu Dropdown */}
            <div className="absolute right-0 z-50 mt-2 w-[calc(100vw-2rem)] max-w-80 rounded-lg border border-gray-200 bg-white shadow-xl">
              {/* Header do Menu */}
              <div className="p-4 border-b bg-gradient-to-r from-green-50 to-blue-50">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <span>Caixa #{caixaAberto.numero_caixa}</span>
                      {caixaAberto.compartilhado && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                          <Users className="h-3 w-3" /> Compartilhado
                        </span>
                      )}
                    </div>
                    <div className="text-lg font-bold text-gray-900">
                      {caixaAberto.compartilhado
                        ? `Aberto por ${caixaAberto.usuario_nome}`
                        : caixaAberto.usuario_nome}
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
                    Aberto em{" "}
                    {new Date(caixaAberto.data_abertura).toLocaleString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>

                  {/* Saldo Atual com olho press-to-reveal */}
                  <div className="flex items-center space-x-2">
                    <div className="text-right">
                      <div className="text-xs text-gray-500">Saldo Atual</div>
                      <div
                        className={`text-sm font-bold ${mostrarSaldoTopo ? "text-green-600" : "text-gray-400"}`}
                      >
                        {mostrarSaldoTopo
                          ? resumo?.totais?.saldo_atual != null
                            ? formatMoneyBRL(resumo.totais.saldo_atual)
                            : statusResumo === "erro"
                              ? "Saldo indisponível"
                              : "Consultando..."
                          : "••••••"}
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
                      <div
                        className={`font-semibold ${mostrarValores ? "text-gray-900" : "text-gray-300"}`}
                      >
                        {mostrarValores ? formatMoneyBRL(caixaAberto.valor_abertura) : "••••••"}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Recebimentos em dinheiro</div>
                      <div
                        className={`font-semibold ${mostrarValores ? "text-green-600" : "text-green-300"}`}
                      >
                        {mostrarValores ? `+ ${formatMoneyBRL(resumo.totais.vendas)}` : "••••••"}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Suprimentos</div>
                      <div
                        className={`font-semibold ${mostrarValores ? "text-green-600" : "text-green-300"}`}
                      >
                        {mostrarValores
                          ? `+ ${formatMoneyBRL(resumo.totais.suprimentos)}`
                          : "••••••"}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Sangrias</div>
                      <div
                        className={`font-semibold ${mostrarValores ? "text-orange-600" : "text-orange-300"}`}
                      >
                        {mostrarValores ? `- ${formatMoneyBRL(resumo.totais.sangrias)}` : "••••••"}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Despesas</div>
                      <div
                        className={`font-semibold ${mostrarValores ? "text-red-600" : "text-red-300"}`}
                      >
                        {mostrarValores ? `- ${formatMoneyBRL(resumo.totais.despesas)}` : "••••••"}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Ações */}
              <div className="p-2">
                <button
                  onClick={() => {
                    setModalAtivo("suprimento");
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
                    setModalAtivo("sangria");
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
                    setModalAtivo("despesa");
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
                    setModalAtivo("devolucao");
                    setMenuAberto(false);
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-purple-50 rounded-lg transition-colors text-left"
                >
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <RotateCcw className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">Devolução</div>
                    <div className="text-xs text-gray-500">
                      {vendaAtualPodeAbrirDevolucao
                        ? `Abrir venda #${getNumeroVendaParaExibicao(vendaParaDevolucao)}`
                        : "Pesquisar venda e devolver ao estoque"}
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setModalAtivo("movimentacoes");
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
                    setModalAtivo("fechar");
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
      {modalAtivo === "suprimento" && (
        <ModalSuprimento
          caixaId={caixaAberto.id}
          numeroCaixa={caixaAberto.numero_caixa}
          onClose={() => setModalAtivo(null)}
          onSucesso={handleOperacaoSucesso}
        />
      )}

      {modalAtivo === "sangria" && (
        <ModalSangria
          caixaId={caixaAberto.id}
          numeroCaixa={caixaAberto.numero_caixa}
          saldoAtual={resumo?.totais?.saldo_atual ?? null}
          statusResumo={statusResumo}
          onRecarregarResumo={() => setResumoKey((valor) => valor + 1)}
          onClose={() => setModalAtivo(null)}
          onSucesso={handleOperacaoSucesso}
        />
      )}

      {modalAtivo === "despesa" && (
        <ModalDespesa
          caixaId={caixaAberto.id}
          onClose={() => setModalAtivo(null)}
          onSucesso={handleOperacaoSucesso}
        />
      )}

      {modalAtivo === "fechar" && caixaAberto && (
        <ModalFecharCaixa
          caixaId={caixaAberto.id}
          onClose={() => setModalAtivo(null)}
          onSuccess={() => {
            setModalAtivo(null);
            publicarEventoCaixa("fechamento", { contextoCaixa, caixaId: caixaAberto.id });
            void atualizarCaixa({ invalidar: true });
          }}
        />
      )}

      {modalDevolucao}

      {modalAtivo === "movimentacoes" && caixaAberto && (
        <ModalMovimentacoesCaixa caixaId={caixaAberto.id} onClose={() => setModalAtivo(null)} />
      )}
    </>
  );
}
