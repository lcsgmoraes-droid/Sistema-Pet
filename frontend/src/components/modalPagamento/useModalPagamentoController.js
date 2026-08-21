import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import api from "../../api";
import useRevealFloatingPanel from "../../hooks/useRevealFloatingPanel";
import { formatMoneyBRL } from "../../utils/formatters";
import { useModulos } from "../../contexts/ModulosContext";
import { useModalPagamentoActions } from "./useModalPagamentoActions";
import {
  calcularBeneficiosCampanhaPreview,
  calcularFaixasParcelamento,
  calcularCustoTotalItensVenda,
  calcularResumoRecebimento,
  descreverCupomMargem,
  ehFormaPagamentoCartao,
  ehFormaPagamentoPix,
  avaliarEstadoJustificativaMargem,
  extrairCorIndicadorMargem,
  montarCupomParaFinalizar,
  montarFallbackSimulacaoParcelamento,
  montarFormasPagamentoAnalise,
  montarPagamentoSimuladoParcelamento,
  montarPagamentosMargem,
  montarPayloadAnaliseMargem,
  normalizarResultadoSimulacaoParcelamento,
  obterBandeiraPadraoPdv,
  obterBandeirasDisponiveis,
  obterCorParcelamentoAtual,
  obterCorVisualParcelamento,
  obterEstiloVisualParcelamento,
  obterModalidadeCartao,
  obterParcelasDisponiveis,
  obterTaxaCartaoSelecionada,
  resolverFaixasParcelamentoDaForma,
} from "../modalPagamentoUtils";

export default function useModalPagamentoController({
  venda,
  cupomAplicado,
  onClose,
  onConfirmar,
  onVendaAtualizada,
}) {
  const { moduloAtivo } = useModulos();
  const moduloCampanhasAtivo = moduloAtivo("campanhas");
  const [pagamentos, setPagamentos] = useState([]);
  const [pagamentosExistentes, setPagamentosExistentes] = useState([]);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [operadoras, setOperadoras] = useState([]); // 🆕 Operadoras de cartão
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null); // 🆕 Operadora selecionada
  const [taxasOperadora, setTaxasOperadora] = useState([]);
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
  const [vendaFinalizadaParaCupom, setVendaFinalizadaParaCupom] = useState(null);

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
        const padrao = response.data.find((op) => op.padrao) || response.data[0];
        if (padrao) {
          setOperadoraSelecionada(padrao);
        }
      } catch (error) {
        console.error("Erro ao carregar operadoras:", error);
      }
    };
    carregarOperadoras();
  }, []);

  useEffect(() => {
    let ativo = true;
    setTaxasOperadora([]);
    setBandeira("");
    setNumeroParcelas(1);

    if (!operadoraSelecionada?.id) {
      return () => {
        ativo = false;
      };
    }

    api
      .get(`/operadoras-cartao/${operadoraSelecionada.id}/taxas`, {
        params: { apenas_ativas: true },
      })
      .then((response) => {
        if (ativo) setTaxasOperadora(response.data || []);
      })
      .catch((error) => {
        console.error("Erro ao carregar taxas da operadora no PDV:", error);
        if (ativo) setTaxasOperadora([]);
      });

    return () => {
      ativo = false;
    };
  }, [operadoraSelecionada?.id]);

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
  const modalidadeCartao = obterModalidadeCartao(formaPagamentoSelecionada);
  const bandeirasDisponiveis = useMemo(
    () => obterBandeirasDisponiveis({ taxas: taxasOperadora, modalidade: modalidadeCartao }),
    [modalidadeCartao, taxasOperadora],
  );
  const parcelasDisponiveis = useMemo(
    () => {
      if (!ehFormaPagamentoCartao(formaPagamentoSelecionada)) {
        const maxParcelas = formaPagamentoSelecionada?.parcelas_maximas || 12;
        return Array.from({ length: maxParcelas }, (_, index) => index + 1);
      }
      const maxParcelas =
        operadoraSelecionada?.max_parcelas || formaPagamentoSelecionada?.parcelas_maximas || 12;
      return obterParcelasDisponiveis({
        taxas: taxasOperadora,
        modalidade: modalidadeCartao,
        bandeira,
        maxParcelas,
      });
    },
    [
      bandeira,
      formaPagamentoSelecionada?.parcelas_maximas,
      modalidadeCartao,
      operadoraSelecionada?.max_parcelas,
      taxasOperadora,
    ],
  );
  const taxaCartaoSelecionada = useMemo(
    () =>
      obterTaxaCartaoSelecionada({
        taxas: taxasOperadora,
        modalidade: modalidadeCartao,
        bandeira,
        parcelas: numeroParcelas,
      }),
    [bandeira, modalidadeCartao, numeroParcelas, taxasOperadora],
  );

  useEffect(() => {
    if (!ehFormaPagamentoCartao(formaPagamentoSelecionada) || !operadoraSelecionada) return;
    const aindaDisponivel = bandeirasDisponiveis.includes(bandeira);
    if (aindaDisponivel) return;
    setBandeira(
      obterBandeiraPadraoPdv({ operadora: operadoraSelecionada, bandeiras: bandeirasDisponiveis }),
    );
  }, [bandeira, bandeirasDisponiveis, formaPagamentoSelecionada, operadoraSelecionada]);

  useEffect(() => {
    if (!parcelasDisponiveis.length) {
      setNumeroParcelas(1);
      return;
    }
    if (!parcelasDisponiveis.includes(numeroParcelas)) {
      setNumeroParcelas(parcelasDisponiveis[0]);
    }
  }, [numeroParcelas, parcelasDisponiveis]);

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
    if (!formasPagamento.length) return;

    setLoadingStatusMargem(true);
    try {
      // Usa a forma de pagamento à vista cadastrada no tenant, sem assumir ID fixo.
      const pagamentoSimuladoAVista = montarFormasPagamentoAnalise({
        pagamentos: [],
        formasPagamento,
        valorTotal: venda.total,
      });

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

  // Calcula a margem inicial assim que as formas de pagamento estiverem disponíveis.
  useEffect(() => {
    if (formasPagamento.length > 0) {
      calcularStatusMargemInicial();
    }
  }, [formasPagamento]);

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

    if (ehFormaPagamentoCartao(formaPagamento) && (!operadoraSelecionada || !bandeira)) {
      return;
    }

    const parcelasParaSimular = ehFormaPagamentoCartao(formaPagamento)
      ? parcelasDisponiveis
      : Array.from({ length: formaPagamento?.parcelas_maximas ?? 12 }, (_, index) => index + 1);
    if (!parcelasParaSimular.length) return;
    const maxParcelas = Math.max(...parcelasParaSimular);
    const formaPagamentoId = formaPagamento.id;

    console.log(`🎲 Simulando parcelamentos para ${formaPagamento.nome} (até ${maxParcelas}x)...`);

    setLoadingSimulacao(true);

    try {
      const resultados = {};

      // Simular todas as parcelas de 1 até max
      for (const parcelas of parcelasParaSimular) {
        const pagamentoSimulado = montarPagamentoSimuladoParcelamento({
          formaPagamentoId,
          valorTotal: venda.total,
          parcelas,
          operadoraId: operadoraSelecionada?.id || null,
          bandeira,
          modalidade: obterModalidadeCartao(formaPagamento),
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

  useEffect(() => {
    if (!formaPagamentoSelecionada?.id) return;
    setSimulacoesParcelamento((atuais) => {
      const atualizados = { ...atuais };
      delete atualizados[formaPagamentoSelecionada.id];
      return atualizados;
    });
    setFaixasParcelamento(null);
  }, [bandeira, formaPagamentoSelecionada?.id, operadoraSelecionada?.id]);

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
  }, [
    bandeira,
    formaPagamentoSelecionada?.id,
    operadoraSelecionada?.id,
    parcelasDisponiveis.join(","),
    simulacoesParcelamento,
  ]);

  const {
    adicionarPagamento,
    emitirNFe,
    excluirPagamentoExistente,
    handleFinalizar,
    removerPagamento,
  } = useModalPagamentoActions({
    bandeira,
    corParcelamentoAtual,
    cupomParaFinalizar,
    descricaoCupomMargem,
    formaPagamentoSelecionada,
    justificativaTexto,
    margemCriticaAtual,
    nsuCartao,
    numeroParcelas,
    onConfirmar,
    onVendaAtualizada,
    operadoraSelecionada,
    operadoras,
    parcelasDisponiveis,
    opcaoExcedente,
    pagamentos,
    podeConfirmarFinalizacao,
    revelarJustificativaObrigatoria,
    saldoCashback,
    setBandeira,
    setErro,
    setErroJustificativa,
    setFormaPagamentoSelecionada,
    setLoading,
    setMostrarModalCreditoExcedente,
    setMostrarPerguntaNFe,
    setNsuCartao,
    setNumeroParcelas,
    setOperadoraSelecionada,
    setOpcaoExcedente,
    setPagamentos,
    setPagamentosExistentes,
    setTotalPagoExistente,
    setValorExcedente,
    setValorRecebido,
    setVendaFinalizadaId,
    setVendaFinalizadaParaCupom,
    troco,
    valorRecebido,
    valorRestante,
    venda,
    vendaFinalizadaId,
  });

  return {
    mostrarPerguntaNFe,
    modalPerguntaNFeProps: {
      cliente: venda.cliente,
      erro,
      loading,
      onConfirmar,
      onEmitir: emitirNFe,
      venda: vendaFinalizadaParaCupom || venda,
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
      bandeirasDisponiveis,
      parcelasDisponiveis,
      taxaCartaoSelecionada,
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
