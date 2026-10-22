import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import api from "../../api";
import useRevealFloatingPanel from "../../hooks/useRevealFloatingPanel";
import { formatMoneyBRL } from "../../utils/formatters";
import { useModulos } from "../../contexts/ModulosContext";
import { useModalPagamentoActions } from "./useModalPagamentoActions";
import {
  comporExcedentePagamento,
  excecaoPagamentoAutorizada,
  usarContextoExcedenteServidor,
  validarTiposPagamentoExcedente,
} from "./modalPagamentoExcedente";
import {
  calcularBeneficiosCampanhaPreview,
  calcularFaixasParcelamento,
  calcularCustoTotalItensVenda,
  calcularResumoRecebimento,
  calcularSaldoBeneficioDisponivel,
  calcularCashbackDisponivelNaVenda,
  descreverCupomMargem,
  ehFormaPagamentoCartao,
  ehFormaPagamentoPix,
  avaliarEstadoJustificativaMargem,
  extrairCorIndicadorMargem,
  montarCupomParaFinalizar,
  montarFallbackSimulacaoParcelamento,
  montarFormasPagamentoAnalise,
  montarPagamentoSimuladoParcelamento,
  montarPagamentoRecebido,
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
  obterParcelasPermitidasParaForma,
  obterTaxaCartaoSelecionada,
  obterTotalRecebidoExistente,
  resolverFaixasParcelamentoDaForma,
} from "../modalPagamentoUtils";

export default function useModalPagamentoController({
  venda: vendaOriginal,
  cupomAplicado,
  onClose,
  onConfirmar,
  onVendaAtualizada,
}) {
  const [persistencia, setPersistencia] = useState(null);
  const chaveVendaOriginal = JSON.stringify([
    vendaOriginal.id,
    vendaOriginal.total,
    vendaOriginal.desconto_valor,
    vendaOriginal.desconto_venda_valor,
    vendaOriginal.cupom_code,
    vendaOriginal.cupom_discount_applied,
    vendaOriginal.itens,
  ]);
  const setVendaPersistida = useCallback(
    (dados) => setPersistencia({ chave: chaveVendaOriginal, dados }),
    [chaveVendaOriginal],
  );
  const venda = useMemo(
    () => ({
      ...vendaOriginal,
      ...(persistencia?.chave === chaveVendaOriginal ? persistencia.dados : null),
      cliente: vendaOriginal.cliente,
      entrega: vendaOriginal.entrega,
    }),
    [vendaOriginal, persistencia, chaveVendaOriginal],
  );
  const { moduloAtivo } = useModulos();
  const moduloCampanhasAtivo = moduloAtivo("campanhas");
  const moduloFiscalAtivo = moduloAtivo("fiscal");
  const [pagamentos, setPagamentos] = useState([]);
  const [pagamentosExistentes, setPagamentosExistentes] = useState([]);
  const [naoGerarBeneficios, setNaoGerarBeneficios] = useState(Boolean(venda.nao_gerar_beneficios));
  const [justificativaBeneficios, setJustificativaBeneficios] = useState(
    venda.justificativa_nao_gerar_beneficios || "",
  );
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
  const [loadingPagamentos, setLoadingPagamentos] = useState(Boolean(venda.id));
  const [erroPagamentosExistentes, setErroPagamentosExistentes] = useState(false);
  const [autorizacaoExcedente, setAutorizacaoExcedente] = useState(null);
  const [contextoExcedenteServidor, setContextoExcedenteServidor] = useState(null);
  const [erro, setErro] = useState("");
  const [totalPagoExistente, setTotalPagoExistente] = useState(0);
  const [mostrarPerguntaNFe, setMostrarPerguntaNFe] = useState(false);
  const [emissaoAutomatica, setEmissaoAutomatica] = useState(null);
  const [autoEmitirTipo, setAutoEmitirTipo] = useState(null);
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

  // 💰 Cashback de campanhas
  const [saldoCashback, setSaldoCashback] = useState(0);
  const [cashbackLimitPercent, setCashbackLimitPercent] = useState(null);
  const [campanhasCompra, setCampanhasCompra] = useState([]);
  const [rankCliente, setRankCliente] = useState("bronze");
  const [loadingBeneficiosCampanha, setLoadingBeneficiosCampanha] = useState(false);

  const modalPagamentoContentRef = useRef(null);

  useEffect(() => {
    if (!moduloFiscalAtivo) return;
    let ativo = true;
    api
      .get("/empresa/config/pdv")
      .then(({ data }) => {
        if (ativo)
          setEmissaoAutomatica({
            ativa: Boolean(data?.emitir_nota_automatica_pdv),
            tipo: data?.tipo_nota_automatica_pdv === "nfe" ? "nfe" : "nfce",
          });
      })
      .catch(() => {
        if (ativo) setEmissaoAutomatica(null);
      });
    return () => {
      ativo = false;
    };
  }, [moduloFiscalAtivo]);

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
      setCashbackLimitPercent(null);
      return;
    }
    if (!venda.cliente?.id) {
      setSaldoCashback(0);
      setCashbackLimitPercent(null);
      return;
    }
    const clienteId = venda.cliente.id;
    api
      .get(`/campanhas/clientes/${clienteId}/saldo`)
      .then((res) => {
        setSaldoCashback(parseFloat(res.data.saldo_cashback || 0));
        setCashbackLimitPercent(res.data.cashback_use_limit_percent ?? null);
      })
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
    let ativo = true;
    const buscarPagamentos = async () => {
      if (!venda.id) {
        setLoadingPagamentos(false);
        setErroPagamentosExistentes(false);
        setPagamentosExistentes([]);
        setTotalPagoExistente(0);
        return;
      }

      setLoadingPagamentos(true);
      setErroPagamentosExistentes(false);
      try {
        const response = await api.get(`/vendas/${venda.id}/pagamentos`);
        if (!ativo) return;
        setPagamentosExistentes(response.data.pagamentos || []);
        setTotalPagoExistente(obterTotalRecebidoExistente(response.data));
      } catch (error) {
        if (!ativo) return;
        console.error("Erro ao buscar pagamentos:", error);
        setErroPagamentosExistentes(true);
        setErro(
          "Não foi possível conferir os pagamentos já registrados. Feche e abra o recebimento para tentar novamente.",
        );
      } finally {
        if (ativo) setLoadingPagamentos(false);
      }
    };

    buscarPagamentos();
    return () => {
      ativo = false;
    };
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
    () =>
      obterBandeirasDisponiveis({
        taxas: taxasOperadora,
        modalidade: modalidadeCartao,
        bandeiraLegada: formaPagamentoSelecionada?.bandeira,
      }),
    [formaPagamentoSelecionada?.bandeira, modalidadeCartao, taxasOperadora],
  );
  const parcelasDisponiveis = useMemo(() => {
    if (!ehFormaPagamentoCartao(formaPagamentoSelecionada)) {
      return obterParcelasPermitidasParaForma(formaPagamentoSelecionada);
    }
    const maxParcelas = Math.min(
      Number(operadoraSelecionada?.max_parcelas || 12),
      Number(formaPagamentoSelecionada?.parcelas_maximas || 12),
    );
    return obterParcelasDisponiveis({
      taxas: taxasOperadora,
      modalidade: modalidadeCartao,
      bandeira,
      maxParcelas,
    });
  }, [
    bandeira,
    formaPagamentoSelecionada?.parcelas_maximas,
    modalidadeCartao,
    operadoraSelecionada?.max_parcelas,
    taxasOperadora,
  ]);
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
  const candidatoExcedente =
    formaPagamentoSelecionada &&
    valorRestante > 0 &&
    Number(valorRecebido) > 0 &&
    !["dinheiro", "cashback", "credito_cliente", "crediario", "boleto"].includes(
      formaPagamentoSelecionada.tipo,
    )
      ? montarPagamentoRecebido({
          formaPagamento: formaPagamentoSelecionada,
          valor: valorRecebido,
          valorRestante,
          bandeira,
          nsuCartao,
          operadora: operadoraSelecionada,
          numeroParcelas,
        })
      : null;
  const composicaoExcedente = usarContextoExcedenteServidor(
    comporExcedentePagamento({
      valorTotal,
      totalPagoExistente,
      pagamentos: candidatoExcedente ? [...pagamentos, candidatoExcedente] : pagamentos,
    }),
    contextoExcedenteServidor,
  );
  const composicaoFinalizacao = usarContextoExcedenteServidor(
    comporExcedentePagamento({ valorTotal, totalPagoExistente, pagamentos }),
    contextoExcedenteServidor,
  );
  const erroTiposExcedente = validarTiposPagamentoExcedente({
    valorTotal,
    totalPagoExistente,
    pagamentos,
  });
  const pagamentosDisponiveis = !loadingPagamentos && !erroPagamentosExistentes;
  const saldoCreditoDisponivel = calcularSaldoBeneficioDisponivel({
    saldo: venda.cliente?.credito,
    pagamentos,
    tipo: "credito_cliente",
  });
  const saldoCashbackDisponivel = calcularCashbackDisponivelNaVenda({
    saldo: saldoCashback,
    valorTotal,
    limitePercentual: cashbackLimitPercent,
    pagamentos,
    pagamentosExistentes,
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
  const mostrarBotaoAdicionarRodape = Boolean(formaPagamentoSelecionada) && valorRestante > 0;

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
      const formasPagamentoMargem = montarFormasPagamentoAnalise({
        pagamentos: todosPagamentos,
        formasPagamento,
        valorTotal: venda.total,
      });

      const response = await api.post(
        `/formas-pagamento/analisar-venda`,
        montarPayloadAnaliseMargem({
          venda,
          formasPagamento: formasPagamentoMargem,
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
    bloqueado: loading || !pagamentosDisponiveis,
    autorizacaoExcedente,
    setAutorizacaoExcedente,
    composicaoFinalizacao,
    setContextoExcedenteServidor,
    setErroPagamentosExistentes,
    bandeira,
    corParcelamentoAtual,
    cupomParaFinalizar,
    descricaoCupomMargem,
    formaPagamentoSelecionada,
    justificativaTexto,
    margemCriticaAtual,
    moduloFiscalAtivo,
    emissaoAutomatica,
    naoGerarBeneficios,
    justificativaBeneficios,
    nsuCartao,
    numeroParcelas,
    onConfirmar,
    onVendaAtualizada,
    operadoraSelecionada,
    operadoras,
    parcelasDisponiveis,
    pagamentos,
    podeConfirmarFinalizacao,
    revelarJustificativaObrigatoria,
    saldoCashback: saldoCashbackDisponivel,
    saldoCreditoDisponivel,
    setBandeira,
    setErro,
    setErroJustificativa,
    setFormaPagamentoSelecionada,
    setLoading,
    setMostrarPerguntaNFe,
    setAutoEmitirTipo,
    setNsuCartao,
    setNumeroParcelas,
    setOperadoraSelecionada,
    setPagamentos,
    setPagamentosExistentes,
    setTotalPagoExistente,
    setValorRecebido,
    setVendaFinalizadaId,
    setVendaFinalizadaParaCupom,
    setVendaPersistida,
    totalPagoExistente,
    valorRecebido,
    valorRestante,
    venda,
    vendaFinalizadaId,
  });

  return {
    mostrarPerguntaNFe,
    modalPerguntaNFeProps: {
      autoEmitirTipo,
      cliente: venda.cliente,
      erro,
      loading,
      moduloFiscalAtivo,
      onConfirmar,
      onVoltar: async () => {
        await onVendaAtualizada(vendaFinalizadaId);
        onClose();
      },
      onEmitir: emitirNFe,
      venda: vendaFinalizadaParaCupom || venda,
      vendaId: vendaFinalizadaId,
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
      saldoCashback: saldoCashbackDisponivel,
      saldoCashbackTotal: saldoCashback,
      cashbackLimitPercent,
      saldoCreditoDisponivel,
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
      opcoesParcelamentoRef,
      estiloVisualParcelamento,
      valorTotal,
      valorPago,
      moduloCampanhasAtivo,
      naoGerarBeneficios,
      setNaoGerarBeneficios,
      justificativaBeneficios,
      setJustificativaBeneficios,
      moduloFiscalAtivo,
      loadingBeneficiosCampanha,
      carimbosPrevistos,
      cashbackPrevisto,
      recompraPrevista,
      pagamentosExistentes,
      pagamentos,
      loading: loading || loadingPagamentos,
      composicaoExcedente: erroTiposExcedente ? null : composicaoExcedente,
      autorizacaoExcedente,
      setAutorizacaoExcedente,
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
      erro: erro || erroTiposExcedente,
      adicionarPagamento,
      mostrarBotaoAdicionarRodape,
      handleFinalizar,
      podeConfirmarFinalizacao:
        podeConfirmarFinalizacao &&
        !erroTiposExcedente &&
        pagamentosDisponiveis &&
        (composicaoFinalizacao.excedente === 0 ||
          excecaoPagamentoAutorizada(composicaoFinalizacao, autorizacaoExcedente)),
    },
  };
}
