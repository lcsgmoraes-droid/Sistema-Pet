import { useRef } from "react";
import { useNavigate } from "react-router-dom";

import api from "../../api";
import { verificarEstoqueNegativo } from "../../api/alertasEstoque";
import { atualizarVenda, criarVenda, finalizarVenda } from "../../api/vendas";
import {
  emitirNotaFiscalAssistida,
  extrairAcaoCorrecaoFiscal,
  extrairMensagemNFe,
} from "../../utils/nfeFiscalAssistida";
import { rejeicaoResponsavelTecnico } from "../../utils/fiscalRejectionGuidance.mjs";
import { ehVendaCrediario } from "../../utils/pdvReceipt";
import { montarPayloadVenda } from "../../utils/pdvVendaPayload";
import {
  devePerguntarNotaFiscal,
  montarItensParaVerificarEstoqueNegativo,
  montarMensagemEstoqueNegativo,
  montarObservacoesComJustificativaMargem,
  montarPagamentoRecebido,
  montarVendaParaPersistirComCupom,
  persistirVendaAbertaParaPagamento,
  validarPagamentoParaAdicionar,
} from "../modalPagamentoUtils";
import { confirmarCorePet, perguntarCorePet } from "../../services/corepetDialog";

export function useModalPagamentoActions({
  bandeira,
  corParcelamentoAtual,
  cupomParaFinalizar,
  descricaoCupomMargem,
  formaPagamentoSelecionada,
  justificativaTexto,
  margemCriticaAtual,
  moduloFiscalAtivo,
  naoGerarBeneficios,
  justificativaBeneficios,
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
  saldoCreditoDisponivel,
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
}) {
  const navigate = useNavigate();
  const vendaIdPersistidaRef = useRef(venda?.id || null);

  const adicionarPagamento = () => {
    const valor = valorRecebido || 0;
    const erroValidacao = validarPagamentoParaAdicionar({
      formaPagamento: formaPagamentoSelecionada,
      valor,
      saldoCashback,
      saldoCreditoDisponivel,
      valorRestante,
      bandeira,
      operadora: operadoraSelecionada,
      numeroParcelas,
      parcelasDisponiveis,
      cliente: venda.cliente,
    });

    if (erroValidacao) {
      setErro(erroValidacao);
      return;
    }

    console.log("DEBUG formaPagamentoSelecionada:", formaPagamentoSelecionada);

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
    console.log("DEBUG novoPagamento:", novoPagamento);
    console.log(
      `Reutilizando simulacao do backend: ${numeroParcelas}x = cor ${corParcelamentoAtual}`,
    );

    if (margemCriticaAtual) {
      if (!justificativaTexto || justificativaTexto.trim().length < 10) {
        setErroJustificativa(
          "Justificativa obrigatoria para margem critica (minimo 10 caracteres)",
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

    const trocoParaCredito =
      opcaoExcedente === "credito" && troco > 0 && formaPagamentoSelecionada?.tipo !== "dinheiro"
        ? troco
        : 0;

    setPagamentos([...pagamentos, novoPagamento]);
    setFormaPagamentoSelecionada(null);
    setValorRecebido(0);
    setBandeira("");
    setOperadoraSelecionada(operadoras.find((op) => op.padrao) || operadoras[0] || null);
    setNsuCartao("");
    setNumeroParcelas(1);
    setErro("");
    setErroJustificativa("");
    setOpcaoExcedente(null);

    if (trocoParaCredito > 0) {
      setValorExcedente(trocoParaCredito);
      setMostrarModalCreditoExcedente(true);
    }
  };

  const removerPagamento = (index) => {
    setPagamentos(pagamentos.filter((_, i) => i !== index));
  };

  const excluirPagamentoExistente = async (pagamentoId) => {
    if (!(await confirmarCorePet("Deseja realmente excluir este pagamento?"))) {
      return;
    }

    setLoading(true);
    setErro("");

    try {
      console.log(`Excluindo pagamento ID ${pagamentoId}...`);
      await api.delete(`/vendas/pagamentos/${pagamentoId}`);
      console.log("Pagamento excluido com sucesso!");

      const response = await api.get(`/vendas/${venda.id}/pagamentos`);
      setPagamentosExistentes(response.data.pagamentos || []);
      setTotalPagoExistente(response.data.total_pago || 0);

      if (response.data.pagamentos.length === 0 && onVendaAtualizada) {
        await onVendaAtualizada();
      }

      setErro("");
    } catch (error) {
      console.error("Erro ao excluir pagamento:", error);
      console.error("   Response:", error.response);
      console.error("   Message:", error.message);

      if (error.message && error.message.includes("CORS")) {
        setErro(
          "Erro de CORS: O backend precisa ser reiniciado. Feche e abra novamente o servidor backend.",
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

    return await confirmarCorePet(montarMensagemEstoqueNegativo(produtosNegativos));
  };

  const salvarVendaAbertaParaPagamento = async () => {
    const vendaParaPersistir = montarVendaParaPersistirComCupom({
      venda,
      cupomParaFinalizar,
    });
    const payloadVenda = montarPayloadVenda(vendaParaPersistir);

    const vendaId = await persistirVendaAbertaParaPagamento({
      vendaParaPersistir,
      payloadVenda,
      vendaIdPersistida: vendaIdPersistidaRef.current,
      criarVenda,
      atualizarVenda,
    });
    vendaIdPersistidaRef.current = vendaId;
    return vendaId;
  };

  const handleFinalizar = async () => {
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

      const vendaId = await salvarVendaAbertaParaPagamento();
      const opcoesFinalizacao = {
        cupom_code: cupomParaFinalizar?.code || null,
        cupom_discount_applied: cupomParaFinalizar?.discount_applied ?? null,
        nao_gerar_beneficios: naoGerarBeneficios,
        justificativa_nao_gerar_beneficios: naoGerarBeneficios
          ? justificativaBeneficios.trim()
          : null,
      };
      let resultado;
      try {
        resultado = await finalizarVenda(vendaId, pagamentos, opcoesFinalizacao);
      } catch (erroBloqueio) {
        const detalhe = erroBloqueio.response?.data?.detail;
        if (
          erroBloqueio.response?.status !== 409 ||
          typeof detalhe !== "string" ||
          !detalhe.startsWith("Venda bloqueada:")
        ) {
          throw erroBloqueio;
        }
        const motivo = await perguntarCorePet({
          titulo: "Liberar venda bloqueada",
          mensagem: `${detalhe}\n\nUm administrador ou usuário autorizado em Administração > Usuários pode liberar esta venda. Informe o motivo:`,
          placeholder: "Motivo da liberação (mínimo de 10 caracteres)",
          confirmarTexto: "Liberar esta venda",
        });
        if (motivo === null) throw erroBloqueio;
        resultado = await finalizarVenda(vendaId, pagamentos, {
          ...opcoesFinalizacao,
          motivo_liberacao_crediario: motivo.trim(),
        });
      }

      const tiposPorFormaId = new Map(
        pagamentos
          .filter((pagamento) => pagamento.forma_pagamento_id && pagamento.forma_pagamento_tipo)
          .map((pagamento) => [
            String(pagamento.forma_pagamento_id),
            pagamento.forma_pagamento_tipo,
          ]),
      );
      const pagamentosBase = resultado.pagamentos?.length ? resultado.pagamentos : pagamentos;
      const pagamentosResultado = pagamentosBase.map((pagamento) => ({
        ...pagamento,
        forma_pagamento_tipo:
          pagamento.forma_pagamento_tipo ||
          tiposPorFormaId.get(String(pagamento.forma_pagamento_id || "")) ||
          null,
      }));
      const vendaParaCupom = { ...resultado, pagamentos: pagamentosResultado };

      setVendaFinalizadaId(vendaId);
      setVendaFinalizadaParaCupom({
        ...vendaParaCupom,
        eh_crediario: ehVendaCrediario(vendaParaCupom),
      });

      if (!moduloFiscalAtivo || devePerguntarNotaFiscal(resultado)) {
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
      if (resultado?.data?.processando) {
        globalThis.alert(
          `${tipoNota === "nfe" ? "NF-e" : "NFC-e"} recebida pelo emissor e ainda em processamento. Consulte novamente em Notas Fiscais.`,
        );
        onConfirmar();
        return { autorizada: false, processando: true, data: resultado.data };
      } else if (transmissao?.success === false) {
        globalThis.alert(
          `${tipoNota === "nfe" ? "NF-e" : "NFC-e"} criada, mas a transmissão não foi concluída automaticamente.\n\n${transmissao.erro || ""}`.trim(),
        );
        onConfirmar();
        return { autorizada: false, processando: true, data: resultado.data };
      }
      return {
        autorizada: true,
        data: resultado?.data,
        tipoNota,
        vendaId: vendaFinalizadaId,
      };
    } catch (error) {
      console.error("Erro ao emitir nota:", error);
      const mensagem = extrairMensagemNFe(error);
      const recuperacao = error?.recuperacaoNFe;
      if (recuperacao) {
        setErro(mensagem);
        const suporte = rejeicaoResponsavelTecnico({
          codigo: recuperacao.codigoErro,
          motivo: recuperacao.motivo,
        });
        const pergunta = suporte
          ? "Abrir a orientação de suporte desta nota agora?"
          : "Abrir a tela de correção desta nota agora?";
        if (await confirmarCorePet(`${mensagem}\n\n${pergunta}`)) {
          const params = new URLSearchParams({
            abrir: "1",
            venda_id: String(recuperacao.vendaId),
            corrigir: "1",
          });
          if (recuperacao.numero) params.set("busca", String(recuperacao.numero));
          navigate(`/notas-fiscais/saida?${params.toString()}`);
        }
        return;
      }
      const acaoFiscal = extrairAcaoCorrecaoFiscal(error);
      setErro(mensagem);
      if (
        acaoFiscal &&
        (await confirmarCorePet(`${mensagem}\n\nAbrir o cadastro fiscal deste produto agora?`))
      ) {
        navigate(acaoFiscal.url);
      } else {
        globalThis.alert(mensagem);
      }
      return;
    } finally {
      setLoading(false);
    }
  };

  return {
    adicionarPagamento,
    emitirNFe,
    excluirPagamentoExistente,
    handleFinalizar,
    removerPagamento,
  };
}
