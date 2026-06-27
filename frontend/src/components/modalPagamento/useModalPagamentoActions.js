import { useNavigate } from "react-router-dom";

import api from "../../api";
import { verificarEstoqueNegativo } from "../../api/alertasEstoque";
import { atualizarVenda, criarVenda, finalizarVenda } from "../../api/vendas";
import {
  emitirNotaFiscalAssistida,
  extrairAcaoCorrecaoFiscal,
  extrairMensagemNFe,
} from "../../utils/nfeFiscalAssistida";
import { montarPayloadVenda } from "../../utils/pdvVendaPayload";
import {
  devePerguntarNotaFiscal,
  montarItensParaVerificarEstoqueNegativo,
  montarMensagemEstoqueNegativo,
  montarObservacoesComJustificativaMargem,
  montarPagamentoRecebido,
  montarVendaParaPersistirComCupom,
  validarPagamentoParaAdicionar,
} from "../modalPagamentoUtils";

export function useModalPagamentoActions({
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
  troco,
  valorRecebido,
  valorRestante,
  venda,
  vendaFinalizadaId,
}) {
  const navigate = useNavigate();

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
    setOperadoraSelecionada(operadoras.find((op) => op.padrao) || null);
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
    if (!globalThis.confirm("Deseja realmente excluir este pagamento?")) {
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
      const resultado = await finalizarVenda(vendaId, pagamentos, {
        cupom_code: cupomParaFinalizar?.code || null,
        cupom_discount_applied: cupomParaFinalizar?.discount_applied ?? null,
      });

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
        globalThis.alert(
          `${tipoNota === "nfe" ? "NF-e" : "NFC-e"} criada no Bling, mas a transmissao nao foi concluida automaticamente.\n\n${transmissao.erro || ""}`.trim(),
        );
      } else {
        globalThis.alert(
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
        globalThis.confirm(`${mensagem}\n\nAbrir o cadastro fiscal deste produto agora?`)
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
