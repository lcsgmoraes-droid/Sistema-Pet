import { useState } from "react";
import api from "../api";

export function usePDVCupom({
  vendaAtual,
  aplicarDescontoTotal,
  removerDescontoTotal,
}) {
  const [codigoCupom, setCodigoCupom] = useState("");
  const [cupomAplicado, setCupomAplicado] = useState(null);
  const [loadingCupom, setLoadingCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState("");

  const aplicarCupom = async () => {
    const code = codigoCupom.trim().toUpperCase();
    if (!code) return;
    if (vendaAtual.itens.length === 0) {
      setErroCupom("Adicione itens a venda antes de aplicar um cupom.");
      return;
    }
    setLoadingCupom(true);
    setErroCupom("");
    try {
      const res = await api.post(`/campanhas/cupons/${code}/resgatar`, {
        venda_total: vendaAtual.total,
        customer_id: vendaAtual.cliente?.id || null,
      });
      const dados = res.data;
      setCupomAplicado(dados);
      setCodigoCupom("");
      aplicarDescontoTotal("valor", dados.discount_applied);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erro ao validar cupom";
      setErroCupom(msg);
    } finally {
      setLoadingCupom(false);
    }
  };

  const removerCupom = () => {
    setCupomAplicado(null);
    setCodigoCupom("");
    setErroCupom("");
    removerDescontoTotal();
  };

  const handleCodigoCupomChange = (valor) => {
    setCodigoCupom(String(valor || "").toUpperCase());
    setErroCupom("");
  };

  const handleCodigoCupomKeyDown = (e) => {
    if (e.key === "Enter") {
      void aplicarCupom();
    }
  };

  return {
    codigoCupom,
    cupomAplicado,
    loadingCupom,
    erroCupom,
    aplicarCupom,
    removerCupom,
    handleCodigoCupomChange,
    handleCodigoCupomKeyDown,
  };
}
