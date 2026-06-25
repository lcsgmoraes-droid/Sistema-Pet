import { useCallback, useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { finalizarVenda, criarVenda, atualizarVenda } from "../../api/vendas";
import { verificarEstoqueNegativo } from "../../api/alertasEstoque";
import api from "../../api";
import useRevealFloatingPanel from "../../hooks/useRevealFloatingPanel";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  emitirNotaFiscalAssistida,
  extrairAcaoCorrecaoFiscal,
  extrairMensagemNFe,
} from "../../utils/nfeFiscalAssistida";
import { montarPayloadVenda } from "../../utils/pdvVendaPayload";
import { useModulos } from "../../contexts/ModulosContext";
import {
  calcularBeneficiosCampanhaPreview,
  calcularFaixasParcelamento,
  calcularCustoTotalItensVenda,
  calcularResumoRecebimento,
  descreverCupomMargem,
  devePerguntarNotaFiscal,
  ehFormaPagamentoPix,
  avaliarEstadoJustificativaMargem,
  extrairCorIndicadorMargem,
  montarCupomParaFinalizar,
  montarItensParaVerificarEstoqueNegativo,
  montarMensagemEstoqueNegativo,
  montarObservacoesComJustificativaMargem,
  montarFallbackSimulacaoParcelamento,
  montarPagamentoAVista,
  montarPagamentoRecebido,
  montarPagamentoSimuladoParcelamento,
  montarPagamentosMargem,
  montarPayloadAnaliseMargem,
  montarVendaParaPersistirComCupom,
  normalizarResultadoSimulacaoParcelamento,
  obterCorParcelamentoAtual,
  obterCorVisualParcelamento,
  obterEstiloVisualParcelamento,
  resolverFaixasParcelamentoDaForma,
  validarPagamentoParaAdicionar,
} from "../modalPagamentoUtils";

export default function useModalPagamentoController({
  venda,
  cupomAplicado,
  onClose,
  onConfirmar,
  onVendaAtualizada,
}) {
  const navigate = useNavigate();
  const { moduloAtivo } = useModulos();
  const moduloCampanhasAtivo = moduloAtivo("campanhas");
  const [pagamentos, setPagamentos] = useState([]);
  const [pagamentosExistentes, setPagamentosExistentes] = useState([]);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [operadoras, setOperadoras] = useState([]); // 🆕 Operadoras de cartão
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null); // 🆕 Operadora selecionada
  const [formaPagamentoSelecionada, setFormaPagamentoSelecionada] = useState(null);
  const [bandeira, setBandeira] = useState("");
  const [nsuCartao, setNsuCartao] = useState(""); // NSU para conciliação bancária
  const [numeroParcelas, setNumeroParcelas] = useState(1);
  const [valorRecebido, setValorRecebido] = useState(0);
  const [loading, setLoading] = useState(false);
  const [, setLoadingPagamentos] = useState(false);
  const [erro, setErro] = useState("");
  const [totalPagoExistente, setTotalPagoExistente] = useState(0);
  const [mostrarPerguntaNFe, setMostrarPerguntaNFe] = useState(false);
  const [vendaFinalizadaId, setVendaFinalizadaId] = useState(null);

  // 🆕 Estados para status de margem operacional
  const [statusMargem, setStatusMargem] = useState(null);
  const [loadingStatusMargem, setLoadingStatusMargem] = useState(false);

  // 💡 Sugestão PIX — desconto que pode ser oferecido ao cliente se pagar no PIX
  const [sugestaoPix, setSugestaoPix] = useState(null);

  // 🆕 Estados para justificativa inline (ÚNICO campo)
  const [justificativaTexto, setJustificativaTexto] = useState("");
  const [erroJustificativa, setErroJustificativa] = useState("");

  // 🆕 PASSO 2️⃣ - Estados para simulação de parcelamentos
  const [simulacoesParcelamento, setSimulacoesParcelamento] = useState({});
  const [loadingSimulacao, setLoadingSimulacao] = useState(false);
  const [faixasParcelamento, setFaixasParcelamento] = useState(null);

  // 🆕 Estados para excedente (troco vs crédito) em métodos não-dinheiro
  const [opcaoExcedente, setOpcaoExcedente] = useState(null); // 'troco' | 'credito'
  const [mostrarModalCreditoExcedente, setMostrarModalCreditoExcedente] = useState(false);
  const [valorExcedente, setValorExcedente] = useState(0);

  // 💰 Cashback de campanhas
  const [saldoCashback, setSaldoCashback] = useState(0);
  const [campanhasCompra, setCampanhasCompra] = useState([]);
  const [rankCliente, setRankCliente] = useState("bronze");
  const [loadingBeneficiosCampanha, setLoadingBeneficiosCampanha] = useState(false);

  const modalPagamentoContentRef = useRef(null);

  // Ref para o container das opções de parcelamento
  const opcoesParcelamentoRef = useRef(null);
  const statusMargemRef = useRef(null);
  const justificativaRef = useRef(null);
  const justificativaTextareaRef = useRef(null);

  // Carregar formas de pagamento do backend
  useEffect(() => {
    const carregarFormas = async () => {
      try {
        const response = await api.get(`/financeiro/formas-pagamento`);
        setFormasPagamento(response.data);
      } catch (error) {
        console.error("Erro ao carregar formas:", error);
      }
    };
    carregarFormas();
  }, []);

  // 💰 Carregar saldo de cashback do cliente
  useEffect(() => {
    if (!moduloCampanhasAtivo) {
      setSaldoCashback(0);
      return;
    }
    if (!venda.cliente?.id) return;
    const clienteId = venda.cliente.id;
    api
      .get(`/campanhas/clientes/${clienteId}/saldo`)
      .then((res) => setSaldoCashback(parseFloat(res.data.saldo_cashback || 0)))
      .catch(() => {}); // campanhas são opcionais
  }, [moduloCampanhasAtivo, venda.cliente?.id]);

  useEffect(() => {
    if (!moduloCampanhasAtivo || !venda.cliente?.id) {
      setCampanhasCompra([]);
      setRankCliente("bronze");
      setLoadingBeneficiosCampanha(false);
      return;
    }

    const carregarBeneficiosCampanha = async () => {
      try {
        setLoadingBeneficiosCampanha(true);
        const [campanhasResp, saldoResp] = await Promise.allSettled([
          api.get("/campanhas"),
          api.get(`/campanhas/clientes/${venda.cliente.id}/saldo`),
        ]);

        const campanhasAtivas =
          campanhasResp.status === "fulfilled"
            ? (campanhasResp.value.data || []).filter((campanha) => campanha.status === "active")
            : [];

        const rankAtual =
          saldoResp.status === "fulfilled"
            ? String(saldoResp.value?.data?.rank_level || "bronze").toLowerCase()
            : "bronze";

        setCampanhasCompra(campanhasAtivas);
        setRankCliente(rankAtual);
      } catch (error) {
        console.error("Erro ao carregar prévia de benefícios no pagamento:", error);
      } finally {
        setLoadingBeneficiosCampanha(false);
      }
    };

    carregarBeneficiosCampanha();
  }, [moduloCampanhasAtivo, venda.cliente?.id]);

  // 🆕 Carregar operadoras de cartão
  useEffect(() => {
    const carregarOperadoras = async () => {
      try {
        const response = await api.get("/operadoras-cartao?apenas_ativas=true");
        setOperadoras(response.data);

        // Pré-selecionar operadora padrão
        const padrao = response.data.find((op) => op.padrao);
        if (padrao) {
          setOperadoraSelecionada(padrao);
        }
      } catch (error) {
        console.error("Erro ao carregar operadoras:", error);
      }
    };
    carregarOperadoras();
  }, []);

  // Buscar pagamentos existentes da venda
  useEffect(() => {
    const buscarPagamentos = async () => {
      if (!venda.id) return; // Se venda não foi criada ainda, não há pagamentos

      setLoadingPagamentos(true);
      try {
        const response = await api.get(`/vendas/${venda.id}/pagamentos`);
        setPagamentosExistentes(response.data.pagamentos || []);
        setTotalPagoExistente(response.data.total_pago || 0);
      } catch (error) {
        console.error("Erro ao buscar pagamentos:", error);
        // Não mostrar erro se a venda ainda não existe
        if (error.response?.status !== 404) {
          setErro("Erro ao carregar pagamentos existentes");
        }
      } finally {
        setLoadingPagamentos(false);
      }
    };

    buscarPagamentos();
  }, [venda.id, venda.status]); // Recarregar quando status mudar também

  // Scroll automático quando opções de parcelamento aparecem
  useEffect(() => {
    if (formaPagamentoSelecionada?.permite_parcelamento && opcoesParcelamentoRef.current) {
      setTimeout(() => {
        opcoesParcelamentoRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }, 100);
    }
  }, [formaPagamentoSelecionada?.permite_parcelamento]);

  const valorTotal = venda.total;
  const { valorPago, valorRestante, podeConfirmarFinalizacao, troco } = calcularResumoRecebimento({
    valorTotal,
    pagamentos,
    totalPagoExistente,
    valorRecebido,
  });
  const cupomParaFinalizar = montarCupomParaFinalizar({ cupomAplicado, venda });
  const descricaoCupomMargem = descreverCupomMargem(cupomParaFinalizar, formatMoneyBRL);
  const corParcelamentoAtual = obterCorParcelamentoAtual({
    formaPagamento: formaPagamentoSelecionada,
    simulacoesParcelamento,
    numeroParcelas,
  });
  const corVisualParcelamento = obterCorVisualParcelamento({
    formaPagamento: formaPagamentoSelecionada,
    simulacoesParcelamento,
    numeroParcelas,
    statusMargem,
  });
  const estiloVisualParcelamento = obterEstiloVisualParcelamento(corVisualParcelamento);
  const { margemCriticaAtual, mostrarCampoJustificativa } = avaliarEstadoJustificativaMargem({
    statusMargem,
    corParcelamentoAtual,
    justificativaTexto,
  });
  const mostrarBotaoAdicionarRodape = Boolean(formaPagamentoSelecionada) && valorRestante > 0.01;

  const rolarElementoNoModal = useCallback((elemento, { focusElement } = {}) => {
    if (!elemento) return;

    const rolar = () => {
      const container = modalPagamentoContentRef.current;

      if (container && typeof elemento.getBoundingClientRect === "function") {
        const containerRect = container.getBoundingClientRect();
        const elementoRect = elemento.getBoundingClientRect();
        const destino = container.scrollTop + elementoRect.top - containerRect.top - 24;
        const limite = Math.max(0, container.scrollHeight - container.clientHeight);

        container.scrollTo({
          top: Math.max(0, Math.min(destino, limite)),
          behavior: "smooth",
        });
      } else if (typeof elemento.scrollIntoView === "function") {
        elemento.scrollIntoView({ behavior: "smooth", block: "center" });
      }

      if (focusElement && typeof window !== "undefined") {
        window.setTimeout(() => {
          focusElement.focus?.({ preventScroll: true });
        }, 250);
      }
    };

    if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
      window.requestAnimationFrame(() => window.requestAnimationFrame(rolar));
      return;
    }

    rolar();
  }, []);

  const revelarJustificativaObrigatoria = useCallback(() => {
    rolarElementoNoModal(justificativaRef.current, {
      focusElement: justificativaTextareaRef.current,
    });
  }, [rolarElementoNoModal]);

  useRevealFloatingPanel({
    enabled: Boolean(statusMargem === "amarelo" || statusMargem === "vermelho"),
    panelRef: statusMargemRef,
    refreshKey: `${statusMargem || ""}:${formaPagamentoSelecionada?.id || ""}:${numeroParcelas}`,
  });

  useEffect(() => {
    if (erroJustificativa) {
      revelarJustificativaObrigatoria();
    }
  }, [erroJustificativa, revelarJustificativaObrigatoria]);

  const { cashbackPrevisto, carimbosPrevistos, recompraPrevista } =
    calcularBeneficiosCampanhaPreview({
      campanhasCompra,
      rankCliente,
      canalVenda: venda.canal || venda.origem_canal_venda || "loja_fisica",
      valorBase: venda.total,
    });

  // 🆕 Função para calcular status de margem operacional (INICIAL - À VISTA)
  const calcularStatusMargemInicial = async () => {
    setLoadingStatusMargem(true);
    try {
      // 🎯 SIMULAR pagamento à vista (dinheiro) para análise inicial
      const pagamentoSimuladoAVista = montarPagamentoAVista(venda.total);

      const response = await api.post(
        `/formas-pagamento/analisar-venda`,
        montarPayloadAnaliseMargem({
          venda,
          formasPagamento: pagamentoSimuladoAVista,
        }),
      );

      // Salvar SOMENTE a cor do indicador
      const corIndicador = extrairCorIndicadorMargem(response.data);
      if (corIndicador) {
        setStatusMargem(corIndicador);
        console.log("✅ Status inicial calculado:", corIndicador);
      }
    } catch (error) {
      console.error("❌ Erro ao calcular status inicial:", error);
      setStatusMargem(null);
    } finally {
      setLoadingStatusMargem(false);
    }
  };

  // 🆕 Função para calcular status de margem operacional (COM PAGAMENTOS REAIS)
  const calcularStatusMargem = async () => {
    if (pagamentos.length === 0 && pagamentosExistentes.length === 0) {
      // Se não há pagamentos, manter o status inicial
      return;
    }

    setLoadingStatusMargem(true);
    try {
      const todosPagamentos = montarPagamentosMargem({
        pagamentosExistentes,
        pagamentos,
      });

      const response = await api.post(
        `/formas-pagamento/analisar-venda`,
        montarPayloadAnaliseMargem({
          venda,
          formasPagamento: todosPagamentos,
        }),
      );

      // Salvar SOMENTE a cor do indicador
      const corIndicador = extrairCorIndicadorMargem(response.data);
      if (corIndicador) {
        setStatusMargem(corIndicador);
      }
    } catch (error) {
      console.error("Erro ao calcular status de margem:", error);
      setStatusMargem(null);
    } finally {
      setLoadingStatusMargem(false);
    }
  };

  // 🆕 REMOVIDO: classificarParcelamento - O BACKEND É A ÚNICA FONTE DA VERDADE
  // A cor_indicador JÁ vem do backend, não precisamos interpretar aqui

  // 🆕 Recalcular status de margem sempre que pagamentos mudarem
  useEffect(() => {
    const timer = setTimeout(() => {
      calcularStatusMargem();
    }, 500); // Debounce de 500ms

    return () => clearTimeout(timer);
  }, [pagamentos, numeroParcelas]);

  // 💡 Calcular sugestão PIX quando a forma de pagamento selecionada NÃO É PIX
  useEffect(() => {
    const ehPix = ehFormaPagamentoPix(formaPagamentoSelecionada);
    if (ehPix || !formaPagamentoSelecionada) {
      setSugestaoPix(null);
      return;
    }
    const custoTotal = calcularCustoTotalItensVenda(venda.itens);
    if (!custoTotal) {
      setSugestaoPix(null);
      return;
    }
    api
      .post("/pdv/indicadores/sugestao-pix", {
        total_venda: venda.total || 0,
        custo_total: custoTotal,
        desconto_atual: venda.desconto_valor || 0,
        taxa_cartao_pct: formaPagamentoSelecionada?.taxa_percentual || 0,
      })
      .then((res) => setSugestaoPix(res.data?.tem_sugestao ? res.data : null))
      .catch(() => setSugestaoPix(null));
  }, [formaPagamentoSelecionada?.id]);

  // 🆕 PASSO 1️⃣ - Calcular status IMEDIATAMENTE ao abrir o modal
  useEffect(() => {
    console.log("🎬 Modal de pagamento aberto - Calculando status inicial...");
    calcularStatusMargemInicial();
  }, []); // Executa apenas uma vez ao montar

  // 🎯 SIMULAR PARCELAMENTOS assim que formas de pagamento forem carregadas
  useEffect(() => {
    if (formasPagamento && formasPagamento.length > 0) {
      const formasComParcelamento = formasPagamento.filter((f) => f.permite_parcelamento);
      if (formasComParcelamento.length > 0 && Object.keys(simulacoesParcelamento).length === 0) {
        console.log("📊 Simulando parcelamentos ao carregar formas...");
        // Simular a primeira forma com parcelamento
        simularParcelamentos(formasComParcelamento[0]);
      }
    }
  }, [formasPagamento]); // Executa quando formas de pagamento são carregadas

  // 🆕 PASSO 2️⃣ - Simular parcelamentos para uma forma de pagamento
  const simularParcelamentos = async (formaPagamento) => {
    if (!formaPagamento || !formaPagamento.permite_parcelamento) {
      console.log("⏭️ Forma de pagamento inválida ou não permite parcelamento");
      return;
    }

    const maxParcelas = formaPagamento?.parcelas_maximas ?? 12;
    const formaPagamentoId = formaPagamento.id;

    console.log(`🎲 Simulando parcelamentos para ${formaPagamento.nome} (até ${maxParcelas}x)...`);

    setLoadingSimulacao(true);

    try {
      const resultados = {};

      // Simular todas as parcelas de 1 até max
      for (let parcelas = 1; parcelas <= maxParcelas; parcelas++) {
        const pagamentoSimulado = montarPagamentoSimuladoParcelamento({
          formaPagamentoId,
          valorTotal: venda.total,
          parcelas,
        });

        try {
          const response = await api.post(
            `/formas-pagamento/analisar-venda`,
            montarPayloadAnaliseMargem({
              venda,
              formasPagamento: pagamentoSimulado,
            }),
          );

          const resultadoSimulacao = normalizarResultadoSimulacaoParcelamento(response.data);
          if (resultadoSimulacao) resultados[parcelas] = resultadoSimulacao;
        } catch (error) {
          console.error(`Erro ao simular ${parcelas}x:`, error);
          resultados[parcelas] = montarFallbackSimulacaoParcelamento();
        }
      }

      // Salvar simulações no estado
      setSimulacoesParcelamento((prev) => ({
        ...prev,
        [formaPagamentoId]: resultados,
      }));

      // 🆕 PASSO 3️⃣ - Calcular faixas de parcelamento
      const faixas = calcularFaixasParcelamento(resultados, maxParcelas);
      setFaixasParcelamento(faixas);

      console.log("✅ Simulações concluídas:", resultados);
      console.log("📊 Faixas calculadas:", faixas);
    } catch (error) {
      console.error("❌ Erro ao simular parcelamentos:", error);
    } finally {
      setLoadingSimulacao(false);
    }
  };

  // 🆕 PASSO 2️⃣ - Disparar simulação quando forma de pagamento é selecionada
  useEffect(() => {
    const decisaoParcelamento = resolverFaixasParcelamentoDaForma({
      formaPagamentoSelecionada,
      simulacoesParcelamento,
      formasPagamento,
    });

    if (decisaoParcelamento?.acao === "simular") {
      simularParcelamentos(decisaoParcelamento.formaPagamento);
      return;
    }

    if (decisaoParcelamento?.faixas) {
      setFaixasParcelamento(decisaoParcelamento.faixas);
      if (decisaoParcelamento.formaPagamento === formaPagamentoSelecionada) {
        console.log("Reutilizando simulacao existente");
      }
    }
  }, [formaPagamentoSelecionada?.id]);

  // Adicionar forma de pagamento
  const adicionarPagamento = () => {
    const valor = valorRecebido || 0;
    const erroValidacao = validarPagamentoParaAdicionar({
      formaPagamento: formaPagamentoSelecionada,
      valor,
      saldoCashback,
      bandeira,
      operadora: operadoraSelecionada,
      numeroParcelas,
    });

    if (erroValidacao) {
      setErro(erroValidacao);
      return;
    }

    // Permitir valor maior que o restante (para dinheiro com troco)
    // ou menor (para baixa parcial)

    // DEBUG: Verificar estrutura da forma de pagamento
    console.log("🔍 DEBUG formaPagamentoSelecionada:", formaPagamentoSelecionada);

    const novoPagamento = montarPagamentoRecebido({
      formaPagamento: formaPagamentoSelecionada,
      valor,
      valorRestante,
      bandeira,
      nsuCartao,
      operadora: operadoraSelecionada,
      numeroParcelas,
      troco,
    });
    console.log("📤 DEBUG novoPagamento:", novoPagamento);

    // ✅ PASSO 5: Se margem crítica, EXIGIR justificativa (mas NÃO bloquear fluxo)
    console.log(
      `♻️ Reutilizando simulação do backend: ${numeroParcelas}x = cor ${corParcelamentoAtual}`,
    );
    const margemCritica = margemCriticaAtual;

    if (margemCritica) {
      if (!justificativaTexto || justificativaTexto.trim().length < 10) {
        setErroJustificativa(
          "⚠️ Justificativa obrigatória para margem crítica (mínimo 10 caracteres)",
        );
        setErro("Por favor, preencha a justificativa abaixo");
        revelarJustificativaObrigatoria();
        return;
      }

      venda.observacoes = montarObservacoesComJustificativaMargem({
        observacoesAtuais: venda.observacoes || "",
        descricaoCupomMargem,
        justificativaTexto,
      });
    }

    // Adicionar pagamento normalmente
    // Capturar troco excedente ANTES de resetar os estados
    const trocoParaCredito =
      opcaoExcedente === "credito" && troco > 0 && formaPagamentoSelecionada?.tipo !== "dinheiro"
        ? troco
        : 0;

    setPagamentos([...pagamentos, novoPagamento]);
    setFormaPagamentoSelecionada(null);
    setValorRecebido(0);
    setBandeira("");
    setOperadoraSelecionada(operadoras.find((op) => op.padrao) || null); // 🆕 Resetar para padrão
    setNsuCartao(""); // Limpar NSU
    setNumeroParcelas(1);
    setErro("");
    setErroJustificativa("");
    setOpcaoExcedente(null);
    // ✅ NÃO limpar justificativaTexto - deve permanecer até finalizar venda

    // Se escolheu gerar crédito, abrir modal após adicionar pagamento
    if (trocoParaCredito > 0) {
      setValorExcedente(trocoParaCredito);
      setMostrarModalCreditoExcedente(true);
    }
  };

  // Remover forma de pagamento
  const removerPagamento = (index) => {
    setPagamentos(pagamentos.filter((_, i) => i !== index));
  };

  // Excluir pagamento existente
  const excluirPagamentoExistente = async (pagamentoId) => {
    if (!confirm("Deseja realmente excluir este pagamento?")) {
      return;
    }

    setLoading(true);
    setErro("");

    try {
      console.log(`🗑️ Excluindo pagamento ID ${pagamentoId}...`);
      await api.delete(`/vendas/pagamentos/${pagamentoId}`);
      console.log("✅ Pagamento excluído com sucesso!");

      // Recarregar pagamentos do servidor para garantir sincronização
      const response = await api.get(`/vendas/${venda.id}/pagamentos`);
      setPagamentosExistentes(response.data.pagamentos || []);
      setTotalPagoExistente(response.data.total_pago || 0);

      // Se excluiu todos os pagamentos, recarregar a venda para atualizar o status
      if (response.data.pagamentos.length === 0 && onVendaAtualizada) {
        await onVendaAtualizada();
      }

      setErro(""); // Limpar erros anteriores
    } catch (error) {
      console.error("❌ Erro ao excluir pagamento:", error);
      console.error("   Response:", error.response);
      console.error("   Message:", error.message);

      if (error.message && error.message.includes("CORS")) {
        setErro(
          "⚠️ Erro de CORS: O backend precisa ser reiniciado. Feche e abra novamente o servidor backend.",
        );
      } else {
        setErro(error.response?.data?.detail || error.message || "Erro ao excluir pagamento");
      }
    } finally {
      setLoading(false);
    }
  };

  const confirmarEstoqueNegativoAntesDeReceber = async () => {
    const itensParaVerificar = montarItensParaVerificarEstoqueNegativo(venda.itens);

    if (itensParaVerificar.length === 0) {
      return true;
    }

    const response = await verificarEstoqueNegativo(itensParaVerificar);
    const produtosNegativos = response.data || [];

    if (produtosNegativos.length === 0) {
      return true;
    }

    return globalThis.confirm(montarMensagemEstoqueNegativo(produtosNegativos));
  };

  const salvarVendaAbertaParaPagamento = async () => {
    const vendaParaPersistir = montarVendaParaPersistirComCupom({
      venda,
      cupomParaFinalizar,
    });
    const payloadVenda = montarPayloadVenda(vendaParaPersistir);

    const vendaIdPersistida = vendaParaPersistir.id;
    if (!vendaIdPersistida) {
      const vendaCriada = await criarVenda(payloadVenda);
      return vendaCriada.id;
    }

    await atualizarVenda(vendaIdPersistida, payloadVenda);
    return vendaIdPersistida;
  };

  // Finalizar venda
  const handleFinalizar = async () => {
    // Permitir baixa parcial - nao exigir pagamento total
    if (!podeConfirmarFinalizacao) {
      setErro("Adicione pelo menos uma forma de pagamento");
      return;
    }

    setLoading(true);
    setErro("");

    try {
      const podeContinuar = await confirmarEstoqueNegativoAntesDeReceber();
      if (!podeContinuar) {
        setLoading(false);
        return;
      }

      // Criar a venda primeiro se ainda nao foi criada
      const vendaId = await salvarVendaAbertaParaPagamento();

      // Finalizar a venda com os pagamentos
      const resultado = await finalizarVenda(vendaId, pagamentos, {
        cupom_code: cupomParaFinalizar?.code || null,
        cupom_discount_applied: cupomParaFinalizar?.discount_applied ?? null,
      });

      // Mostrar pergunta sobre NF-e APENAS se pagamento completo
      setVendaFinalizadaId(vendaId);

      if (devePerguntarNotaFiscal(resultado)) {
        setMostrarPerguntaNFe(true);
      } else {
        onConfirmar();
      }
    } catch (error) {
      console.error("Erro ao finalizar venda:", error);
      setErro(error.response?.data?.detail || "Erro ao finalizar venda");
    } finally {
      setLoading(false);
    }
  };
  // Emitir NF-e
  const emitirNFe = async (tipoNota) => {
    setLoading(true);
    setErro("");

    try {
      const resultado = await emitirNotaFiscalAssistida({
        vendaId: vendaFinalizadaId,
        tipoNota,
      });

      if (resultado?.cancelado) return;

      const transmissao = resultado?.data?.transmissao;
      if (transmissao?.success === false) {
        alert(
          `${tipoNota === "nfe" ? "NF-e" : "NFC-e"} criada no Bling, mas a transmissao nao foi concluida automaticamente.\n\n${transmissao.erro || ""}`.trim(),
        );
      } else {
        alert(
          `${tipoNota === "nfe" ? "NF-e" : "NFC-e"} enviada para emissao/transmissao com sucesso!`,
        );
      }
      onConfirmar();
    } catch (error) {
      console.error("Erro ao emitir nota:", error);
      const mensagem = extrairMensagemNFe(error);
      const acaoFiscal = extrairAcaoCorrecaoFiscal(error);
      setErro(mensagem);
      if (
        acaoFiscal &&
        window.confirm(`${mensagem}\n\nAbrir o cadastro fiscal deste produto agora?`)
      ) {
        navigate(acaoFiscal.url);
      } else {
        alert(mensagem);
      }
      return;
    } finally {
      setLoading(false);
    }
  };

  return {
    mostrarPerguntaNFe,
    modalPerguntaNFeProps: {
      cliente: venda.cliente,
      erro,
      loading,
      onConfirmar,
      onEmitir: emitirNFe,
    },
    viewProps: {
      venda,
      onClose,
      modalPagamentoContentRef,
      formaPagamentoSelecionada,
      setFormaPagamentoSelecionada,
      numeroParcelas,
      setNumeroParcelas,
      setBandeira,
      setNsuCartao,
      setValorRecebido,
      valorRestante,
      saldoCashback,
      formasPagamento,
      valorRecebido,
      bandeira,
      nsuCartao,
      operadoras,
      operadoraSelecionada,
      setOperadoraSelecionada,
      troco,
      opcaoExcedente,
      setOpcaoExcedente,
      opcoesParcelamentoRef,
      estiloVisualParcelamento,
      valorTotal,
      valorPago,
      moduloCampanhasAtivo,
      loadingBeneficiosCampanha,
      carimbosPrevistos,
      cashbackPrevisto,
      recompraPrevista,
      pagamentosExistentes,
      pagamentos,
      loading,
      excluirPagamentoExistente,
      removerPagamento,
      statusMargem,
      statusMargemRef,
      loadingStatusMargem,
      sugestaoPix,
      faixasParcelamento,
      simulacoesParcelamento,
      loadingSimulacao,
      mostrarCampoJustificativa,
      justificativaRef,
      descricaoCupomMargem,
      justificativaTextareaRef,
      justificativaTexto,
      setJustificativaTexto,
      erroJustificativa,
      setErroJustificativa,
      setErro,
      erro,
      adicionarPagamento,
      mostrarBotaoAdicionarRodape,
      handleFinalizar,
      podeConfirmarFinalizacao,
      mostrarModalCreditoExcedente,
      setMostrarModalCreditoExcedente,
      valorExcedente,
    },
  };
}
