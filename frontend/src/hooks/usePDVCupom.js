import { useEffect, useState } from "react";
import api from "../api";

export function usePDVCupom({ vendaAtual, aplicarDescontoTotal, removerDescontoTotal }) {
  const [codigoCupom, setCodigoCupom] = useState("");
  const [cuponsAplicados, setCuponsAplicados] = useState([]);
  const [loadingCupom, setLoadingCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState("");

  useEffect(() => {
    if (!vendaAtual.id && vendaAtual.itens.length === 0) {
      setCuponsAplicados([]);
      setCodigoCupom("");
      setErroCupom("");
    }
  }, [vendaAtual.id, vendaAtual.itens.length]);

  useEffect(() => {
    const codigosPersistidos = String(vendaAtual.cupom_code || "")
      .split(",")
      .map((codigo) => codigo.trim().toUpperCase())
      .filter(Boolean);
    if (codigosPersistidos.length === 0) return;

    setCuponsAplicados((atuais) => {
      if (atuais.map((cupom) => cupom.code).join(",") === codigosPersistidos.join(",")) {
        return atuais;
      }
      return codigosPersistidos.map((code, index) => ({
        code,
        discount_applied: index === 0 ? Number(vendaAtual.cupom_discount_applied || 0) : 0,
        persistido_sem_detalhe: true,
      }));
    });
  }, [vendaAtual.cupom_code, vendaAtual.cupom_discount_applied]);

  const cupomAplicado =
    cuponsAplicados.length > 0
      ? {
          code: cuponsAplicados.map((cupom) => cupom.code).join(","),
          discount_applied: cuponsAplicados.reduce(
            (total, cupom) => total + Number(cupom.discount_applied || 0),
            0,
          ),
          items: cuponsAplicados,
        }
      : null;

  const aplicarCupom = async () => {
    const code = codigoCupom.trim().toUpperCase();
    if (!code) return;
    if (vendaAtual.itens.length === 0) {
      setErroCupom("Adicione itens a venda antes de aplicar um cupom.");
      return;
    }
    if (cuponsAplicados.some((cupom) => cupom.code === code)) {
      setErroCupom("Este cupom ja foi aplicado nesta venda.");
      return;
    }
    if (cuponsAplicados.length >= 5) {
      setErroCupom("Use no maximo 5 cupons na mesma venda.");
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
      const proximosCupons = [...cuponsAplicados, dados];
      const descontoTotal = proximosCupons.reduce(
        (total, cupom) => total + Number(cupom.discount_applied || 0),
        0,
      );
      const codigos = proximosCupons.map((cupom) => cupom.code).join(",");
      setCuponsAplicados(proximosCupons);
      setCodigoCupom("");
      aplicarDescontoTotal("valor", descontoTotal, {
        cupom_code: codigos,
        cupom_discount_applied: descontoTotal,
      });
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erro ao validar cupom";
      setErroCupom(msg);
    } finally {
      setLoadingCupom(false);
    }
  };

  const removerCupom = (codigo) => {
    const cupomSelecionado = cuponsAplicados.find((cupom) => cupom.code === codigo);
    const removerTodos = !codigo || cupomSelecionado?.persistido_sem_detalhe;
    const restantes = removerTodos ? [] : cuponsAplicados.filter((cupom) => cupom.code !== codigo);
    setCuponsAplicados(restantes);
    setCodigoCupom("");
    setErroCupom(
      removerTodos && cuponsAplicados.length > 1
        ? "Os cupons salvos anteriormente foram removidos juntos. Aplique novamente os que desejar."
        : "",
    );
    if (restantes.length === 0) {
      removerDescontoTotal({
        cupom_code: null,
        cupom_discount_applied: null,
      });
      return;
    }
    const descontoTotal = restantes.reduce(
      (total, cupom) => total + Number(cupom.discount_applied || 0),
      0,
    );
    aplicarDescontoTotal("valor", descontoTotal, {
      cupom_code: restantes.map((cupom) => cupom.code).join(","),
      cupom_discount_applied: descontoTotal,
    });
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
