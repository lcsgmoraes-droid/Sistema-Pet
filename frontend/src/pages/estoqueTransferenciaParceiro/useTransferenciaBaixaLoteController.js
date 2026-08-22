import { useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import {
  calcularResumoEncontroContasParceiro,
  criarFormBaixaTransferencia,
  distribuirBaixaTransferencias,
  distribuirCompensacaoAutomatica,
  montarBaixaLoteTransferenciaPayload,
  normalizarNumero,
  obterErroAcertoTransferencia,
} from "./transferenciaParceiroUtils";
import { applyShiftRangeSelection, getShiftSelectionEvent } from "../../utils/shiftRangeSelection";

const PREVIEW_VAZIO = {
  items: [],
  total_aberto: 0,
  total_sugerido: 0,
  valor_restante: 0,
};

export default function useTransferenciaBaixaLoteController({
  historico,
  filtrosHistoricoAplicados,
  pessoaHistoricoSelecionada,
  contasPagarCompensacao,
  setContasPagarCompensacao,
  carregarContasPagarCompensacao,
  carregarHistoricoTransferencias,
  paginaHistorico,
  rotuloPessoa,
} = {}) {
  const [salvandoBaixaLote, setSalvandoBaixaLote] = useState(false);
  const [loadingPreviewBaixaLote, setLoadingPreviewBaixaLote] = useState(false);
  const [baixaLoteAberta, setBaixaLoteAberta] = useState(false);
  const [formBaixaLote, setFormBaixaLote] = useState(() =>
    criarFormBaixaTransferencia({
      valor_total: "",
      ordem: "antiga",
      devolver_estoque: false,
    }),
  );
  const [previewBaixaLote, setPreviewBaixaLote] = useState(PREVIEW_VAZIO);
  const [aplicacoesBaixaLote, setAplicacoesBaixaLote] = useState({});
  const ultimaAplicacaoSelecionadaRef = useRef(null);

  const totalAplicadoBaixaLote = useMemo(
    () =>
      Object.values(aplicacoesBaixaLote || {}).reduce((acumulado, valor) => {
        const numero = normalizarNumero(valor);
        return acumulado + (Number.isFinite(numero) ? numero : 0);
      }, 0),
    [aplicacoesBaixaLote],
  );

  const totalCompensadoBaixaLote = useMemo(() => {
    const totalContasExistentes = Object.values(formBaixaLote.compensacoes || {}).reduce(
      (acumulado, valor) => {
        const numero = normalizarNumero(valor);
        return acumulado + (Number.isFinite(numero) ? numero : 0);
      },
      0,
    );
    const valorNovaConta = normalizarNumero(formBaixaLote.nova_conta_pagar_acerto?.valor);
    return totalContasExistentes + (Number.isFinite(valorNovaConta) ? valorNovaConta : 0);
  }, [formBaixaLote.compensacoes, formBaixaLote.nova_conta_pagar_acerto?.valor]);

  const diferencaAplicacaoBaixaLote = Math.max(
    (normalizarNumero(formBaixaLote.valor_total) || 0) - totalAplicadoBaixaLote,
    0,
  );

  const resolverPessoaBaixaLote = () => {
    const parceiroId = filtrosHistoricoAplicados?.parceiro_id;
    if (!parceiroId) return null;
    if (String(pessoaHistoricoSelecionada?.id || "") === String(parceiroId)) {
      return pessoaHistoricoSelecionada;
    }
    return {
      id: Number(parceiroId),
      nome: filtrosHistoricoAplicados?.busca || `Pessoa #${parceiroId}`,
    };
  };

  const carregarPreviewBaixaLoteTransferencia = async (overrides = {}) => {
    const pessoa = resolverPessoaBaixaLote();
    const valorTotal = normalizarNumero(overrides.valor_total ?? formBaixaLote.valor_total);
    if (!pessoa?.id) {
      toast.error("Selecione uma pessoa no historico para fazer baixa por valor.");
      return false;
    }
    if (!Number.isFinite(valorTotal) || valorTotal <= 0) {
      toast.error("Informe um valor total maior que zero.");
      return false;
    }

    const ordem = overrides.ordem || formBaixaLote.ordem || "antiga";
    try {
      setLoadingPreviewBaixaLote(true);
      const response = await api.post("/estoque/transferencia-parceiro/baixa-lote/preview", {
        parceiro_id: Number(pessoa.id),
        valor_total: valorTotal,
        ordem,
        data_inicio: filtrosHistoricoAplicados?.data_inicio || undefined,
        data_fim: filtrosHistoricoAplicados?.data_fim || undefined,
      });
      const preview = response.data || PREVIEW_VAZIO;
      setPreviewBaixaLote(preview);
      setAplicacoesBaixaLote(distribuirBaixaTransferencias(valorTotal, preview.items || [], ordem));
      const primeiraConta = preview.items?.[0]?.conta_receber_id;
      if (primeiraConta) void carregarContasPagarCompensacao?.(primeiraConta);
      return true;
    } catch (error) {
      console.error("Erro ao carregar preview de baixa por valor:", error);
      toast.error(error?.response?.data?.detail || "Nao foi possivel sugerir a baixa por valor.");
      return false;
    } finally {
      setLoadingPreviewBaixaLote(false);
    }
  };

  const abrirBaixaLoteTransferencia = async () => {
    const pessoa = resolverPessoaBaixaLote();
    if (!pessoa?.id) {
      toast.error("Selecione uma pessoa no historico para fazer baixa por valor.");
      return;
    }

    const valorSugerido = Number(historico?.totais?.saldo_aberto || 0);
    const proximoForm = criarFormBaixaTransferencia({
      valor_total: valorSugerido > 0 ? valorSugerido.toFixed(2) : "",
      valor_recebido: "",
      ordem: "antiga",
      devolver_estoque: false,
    });
    setFormBaixaLote(proximoForm);
    setBaixaLoteAberta(true);
    setPreviewBaixaLote(PREVIEW_VAZIO);
    setAplicacoesBaixaLote({});
    if (valorSugerido > 0) {
      await carregarPreviewBaixaLoteTransferencia({
        valor_total: valorSugerido.toFixed(2),
        ordem: "antiga",
      });
    }
  };

  const fecharBaixaLoteTransferencia = () => {
    setBaixaLoteAberta(false);
    setPreviewBaixaLote(PREVIEW_VAZIO);
    setAplicacoesBaixaLote({});
    setContasPagarCompensacao?.([]);
    setFormBaixaLote(
      criarFormBaixaTransferencia({
        valor_total: "",
        ordem: "antiga",
        devolver_estoque: false,
      }),
    );
  };

  const ajustarBaixaAoSaldoAcerto = async () => {
    const valorInformado = normalizarNumero(formBaixaLote.valor_total);
    const saldoAberto = Number(
      previewBaixaLote.total_aberto || historico?.totais?.saldo_aberto || 0,
    );
    const valorBase =
      Number.isFinite(valorInformado) && valorInformado > 0 ? valorInformado : saldoAberto;
    const resumo = calcularResumoEncontroContasParceiro({
      totalAplicado: valorBase,
      contasPagar: contasPagarCompensacao,
    });
    const valorAjustado = resumo.valorSugeridoAcerto;

    if (!Number.isFinite(valorAjustado) || valorAjustado <= 0) {
      toast.error("Nao ha saldo disponivel para acerto.");
      return;
    }

    const valorFormatado = valorAjustado.toFixed(2);
    const previewCarregado = await carregarPreviewBaixaLoteTransferencia({
      valor_total: valorFormatado,
      ordem: formBaixaLote.ordem || "antiga",
    });
    if (!previewCarregado) return;

    setFormBaixaLote((prev) => ({
      ...prev,
      valor_total: valorFormatado,
      modo_baixa: "acerto",
      compensacoes: distribuirCompensacaoAutomatica(valorAjustado, contasPagarCompensacao),
      nova_conta_pagar_acerto: {
        ...(prev.nova_conta_pagar_acerto || {}),
        valor: "",
      },
    }));
  };

  const registrarBaixaLoteTransferencia = async () => {
    const pessoa = resolverPessoaBaixaLote();
    if (!pessoa?.id) {
      toast.error("Selecione uma pessoa para fazer baixa por valor.");
      return;
    }
    if (totalAplicadoBaixaLote <= 0) {
      toast.error("Marque ao menos uma transferencia com valor para baixar.");
      return;
    }
    if (formBaixaLote.modo_baixa === "recebimento" && !formBaixaLote.forma_pagamento_id) {
      toast.error("Selecione a forma de pagamento.");
      return;
    }

    const valorNovaContaPagar = normalizarNumero(formBaixaLote.nova_conta_pagar_acerto?.valor);
    const temCompensacao =
      Object.values(formBaixaLote.compensacoes || {}).some(
        (valor) => normalizarNumero(valor) > 0,
      ) ||
      (Number.isFinite(valorNovaContaPagar) && valorNovaContaPagar > 0);
    const erroAcerto = obterErroAcertoTransferencia({
      modoBaixa: formBaixaLote.modo_baixa,
      totalBaixa: totalAplicadoBaixaLote,
      totalCompensado: totalCompensadoBaixaLote,
      temCompensacao,
    });
    if (erroAcerto) {
      toast.error(erroAcerto);
      return;
    }

    const payload = montarBaixaLoteTransferenciaPayload({
      parceiroId: pessoa.id,
      form: formBaixaLote,
      aplicacoes: aplicacoesBaixaLote,
      compensacoes: formBaixaLote.compensacoes,
    });

    try {
      setSalvandoBaixaLote(true);
      await api.post("/estoque/transferencia-parceiro/baixa-lote", payload);
      toast.success("Baixa por valor registrada com sucesso.");
      fecharBaixaLoteTransferencia();
      void carregarHistoricoTransferencias?.(filtrosHistoricoAplicados, paginaHistorico);
    } catch (error) {
      console.error("Erro ao registrar baixa por valor:", error);
      toast.error(error?.response?.data?.detail || "Nao foi possivel registrar a baixa por valor.");
    } finally {
      setSalvandoBaixaLote(false);
    }
  };

  const pessoaBaixaLoteAtual = resolverPessoaBaixaLote();
  const alternarAplicacaoBaixaLote = (registro, event) => {
    const contaId = String(registro.conta_receber_id);
    const { checked, shiftKey } = getShiftSelectionEvent(event);

    setAplicacoesBaixaLote((prev) => {
      const aplicacoesAtuais = prev || {};
      const idsAtuais = Object.keys(aplicacoesAtuais).filter(
        (itemId) => aplicacoesAtuais[itemId] !== "",
      );
      const proximosIds = applyShiftRangeSelection({
        anchorId: ultimaAplicacaoSelecionadaRef.current,
        checked,
        currentSelection: idsAtuais,
        getItemId: (item) => String(item.conta_receber_id),
        itemId: contaId,
        items: previewBaixaLote.items || [],
        shiftKey,
      });
      const proximosIdsSet = new Set(proximosIds);
      const proximo = { ...aplicacoesAtuais };

      (previewBaixaLote.items || []).forEach((item) => {
        const itemId = String(item.conta_receber_id);
        if (!proximosIdsSet.has(itemId)) {
          delete proximo[itemId];
          return;
        }
        if (proximo[itemId] !== undefined && proximo[itemId] !== "") return;
        proximo[itemId] =
          item.valor_sugerido > 0
            ? Number(item.valor_sugerido).toFixed(2)
            : Number(item.saldo_aberto || 0).toFixed(2);
      });

      return proximo;
    });

    ultimaAplicacaoSelecionadaRef.current = contaId;
  };

  return {
    salvandoBaixaLote,
    loadingPreviewBaixaLote,
    baixaLoteAberta,
    formBaixaLote,
    setFormBaixaLote,
    previewBaixaLote,
    aplicacoesBaixaLote,
    totalAplicadoBaixaLote,
    totalCompensadoBaixaLote,
    diferencaAplicacaoBaixaLote,
    pessoaBaixaLoteNome: pessoaBaixaLoteAtual ? rotuloPessoa?.(pessoaBaixaLoteAtual) : "",
    abrirBaixaLoteTransferencia,
    fecharBaixaLoteTransferencia,
    carregarPreviewBaixaLoteTransferencia,
    registrarBaixaLoteTransferencia,
    ajustarBaixaAoSaldoAcerto,
    atualizarValorAplicacaoBaixaLote: (contaReceberId, valor) =>
      setAplicacoesBaixaLote((prev) => ({ ...(prev || {}), [contaReceberId]: valor })),
    alternarAplicacaoBaixaLote,
    atualizarValorCompensacaoBaixaLote: (contaPagarId, valor) =>
      setFormBaixaLote((prev) => ({
        ...prev,
        compensacoes: { ...(prev.compensacoes || {}), [contaPagarId]: valor },
      })),
    preencherCompensacaoAutomaticaBaixaLote: () => {
      if (totalAplicadoBaixaLote <= 0) {
        toast.error("Aplique primeiro um valor nas transferencias.");
        return;
      }
      setFormBaixaLote((prev) => ({
        ...prev,
        compensacoes: distribuirCompensacaoAutomatica(
          totalAplicadoBaixaLote,
          contasPagarCompensacao,
        ),
      }));
    },
    limparCompensacoesBaixaLote: () => setFormBaixaLote((prev) => ({ ...prev, compensacoes: {} })),
  };
}
