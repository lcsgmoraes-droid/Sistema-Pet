import { useCallback, useState } from "react";
import api from "../api";
import { formatBRL } from "../utils/formatters";

const DEFAULT_CUPOM = {
  coupon_type: "fixed",
  discount_value: "",
  discount_percent: "",
  channel: "pdv",
  valid_until: "",
  min_purchase_value: "",
  customer_id: "",
  descricao: "",
};

export default function useCampanhasCupons({
  setCupons,
  carregarCupons,
  aba,
  setAba,
}) {
  const [anulando, setAnulando] = useState(null);
  const [modalCupomAberto, setModalCupomAberto] = useState(false);
  const [novoCupom, setNovoCupom] = useState(DEFAULT_CUPOM);
  const [criandoCupom, setCriandoCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState("");

  const anularCupom = useCallback(
    async (code) => {
      if (
        !window.confirm(
          `Anular o cupom ${code}? Esta acao nao pode ser desfeita.`,
        )
      ) {
        return;
      }
      setAnulando(code);
      try {
        await api.delete(`/campanhas/cupons/${code}`);
        setCupons((prev) =>
          prev.map((c) => (c.code === code ? { ...c, status: "voided" } : c)),
        );
      } catch (e) {
        alert(e?.response?.data?.detail || "Erro ao anular cupom.");
      } finally {
        setAnulando(null);
      }
    },
    [setCupons],
  );

  const criarCupomManual = async () => {
    setErroCupom("");
    setCriandoCupom(true);
    try {
      const body = {
        coupon_type: novoCupom.coupon_type,
        channel: novoCupom.channel,
      };
      if (novoCupom.descricao) body.descricao = novoCupom.descricao;
      if (novoCupom.coupon_type === "fixed" && novoCupom.discount_value) {
        body.discount_value = Number.parseFloat(
          String(novoCupom.discount_value).replace(",", "."),
        );
      }
      if (novoCupom.coupon_type === "percent" && novoCupom.discount_percent) {
        body.discount_percent = Number.parseFloat(novoCupom.discount_percent);
      }
      if (novoCupom.valid_until) body.valid_until = novoCupom.valid_until;
      if (novoCupom.min_purchase_value) {
        body.min_purchase_value = Number.parseFloat(
          String(novoCupom.min_purchase_value).replace(",", "."),
        );
      }
      if (novoCupom.customer_id) {
        body.customer_id = Number.parseInt(novoCupom.customer_id, 10);
      }

      await api.post("/campanhas/cupons/manual", body);
      setModalCupomAberto(false);
      setNovoCupom(DEFAULT_CUPOM);
      await carregarCupons();
      if (aba !== "cupons") setAba("cupons");
    } catch (e) {
      setErroCupom(e?.response?.data?.detail || "Erro ao criar cupom.");
    } finally {
      setCriandoCupom(false);
    }
  };

  const formatarValorCupom = (cupom) => {
    if (cupom.coupon_type === "percent" && cupom.discount_percent) {
      return `${cupom.discount_percent}% off`;
    }
    if (cupom.coupon_type === "fixed" && cupom.discount_value) {
      return `R$ ${formatBRL(cupom.discount_value)} off`;
    }
    return "-";
  };

  return {
    anulando,
    modalCupomAberto,
    setModalCupomAberto,
    novoCupom,
    setNovoCupom,
    criandoCupom,
    erroCupom,
    setErroCupom,
    anularCupom,
    criarCupomManual,
    formatarValorCupom,
  };
}
