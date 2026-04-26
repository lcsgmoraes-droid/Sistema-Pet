import { useState } from "react";
import api from "../api";
import { formatBRL } from "../utils/formatters";
import { FRASES_ANIVERSARIO } from "../components/campanhas/campanhasConstants";
import { formatBenefitChannelsSummary } from "../utils/campaignChannelScope";

export default function useCampanhasGestao({
  setCampanhas,
  carregarCampanhas,
}) {
  const [toggling, setToggling] = useState(null);
  const [campanhaEditando, setCampanhaEditando] = useState(null);
  const [paramsEditando, setParamsEditando] = useState({});
  const [salvandoParams, setSalvandoParams] = useState(false);
  const [modalCriarCampanha, setModalCriarCampanha] = useState(false);
  const [novaCampanha, setNovaCampanha] = useState({
    name: "",
    campaign_type: "inactivity",
    params: {},
  });
  const [criandoCampanha, setCriandoCampanha] = useState(false);
  const [erroCriarCampanha, setErroCriarCampanha] = useState("");
  const [arquivando, setArquivando] = useState(null);

  const criarCampanha = async () => {
    setErroCriarCampanha("");
    if (!novaCampanha.name.trim()) {
      setErroCriarCampanha("Nome obrigatorio.");
      return;
    }
    setCriandoCampanha(true);
    try {
      await api.post("/campanhas", {
        name: novaCampanha.name,
        campaign_type: novaCampanha.campaign_type,
        params: {},
        priority: 50,
      });
      setModalCriarCampanha(false);
      setNovaCampanha({ name: "", campaign_type: "inactivity", params: {} });
      carregarCampanhas();
    } catch (e) {
      setErroCriarCampanha(
        e?.response?.data?.detail || "Erro ao criar campanha.",
      );
    } finally {
      setCriandoCampanha(false);
    }
  };

  const arquivarCampanha = async (campanha) => {
    if (
      !window.confirm(
        `Arquivar a campanha "${campanha.name}"? Ela ficara inativa e nao podera ser reativada pela interface.`,
      )
    ) {
      return;
    }
    setArquivando(campanha.id);
    try {
      await api.delete(`/campanhas/${campanha.id}`);
      setCampanhas((prev) => prev.filter((x) => x.id !== campanha.id));
    } catch (e) {
      if (e?.response?.status === 404) {
        setCampanhas((prev) => prev.filter((x) => x.id !== campanha.id));
        return;
      }
      alert("Erro ao arquivar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setArquivando(null);
    }
  };

  const toggleCampanha = async (campanha) => {
    setToggling(campanha.id);
    try {
      const res = await api.post(`/campanhas/${campanha.id}/pausar`);
      setCampanhas((prev) =>
        prev.map((c) =>
          c.id === campanha.id ? { ...c, status: res.data.status } : c,
        ),
      );
    } catch (e) {
      console.error("Erro ao alterar status:", e);
    } finally {
      setToggling(null);
    }
  };

  const abrirEdicao = (campanha) => {
    setCampanhaEditando(campanha.id);
    const params = { ...campanha.params };
    if (
      ["birthday_customer", "birthday_pet"].includes(campanha.campaign_type) &&
      !params.notification_message
    ) {
      const tipoPresente = params.tipo_presente || "cupom";
      const frases =
        FRASES_ANIVERSARIO[campanha.campaign_type] ||
        FRASES_ANIVERSARIO.birthday_customer;
      params.notification_message = frases[tipoPresente] || "";
    }
    setParamsEditando(params);
  };

  const fecharEdicao = () => {
    setCampanhaEditando(null);
    setParamsEditando({});
  };

  const salvarParametros = async (campanha) => {
    setSalvandoParams(true);
    try {
      await api.put(`/campanhas/${campanha.id}/parametros`, {
        params: paramsEditando,
      });
      setCampanhas((prev) =>
        prev.map((item) =>
          item.id === campanha.id ? { ...item, params: paramsEditando } : item,
        ),
      );
      fecharEdicao();
    } catch (e) {
      console.error("Erro ao salvar parametros:", e);
      alert("Erro ao salvar os parametros.");
    } finally {
      setSalvandoParams(false);
    }
  };

  const formatarParams = (tipo, params) => {
    if (!params) return "-";
    if (tipo === "loyalty_stamp") {
      return `${params.stamps_to_complete || "?"} carimbos -> R$ ${formatBRL(params.reward_value || 0)} de recompensa | Canais: ${formatBenefitChannelsSummary(params)}`;
    }
    if (tipo === "cashback") {
      return `Bronze ${params.bronze_percent || 0}% / Prata ${params.silver_percent || 0}% / Ouro ${params.gold_percent || 0}% | Canais: ${formatBenefitChannelsSummary(params)}`;
    }
    if (["birthday", "birthday_customer", "birthday_pet"].includes(tipo)) {
      const tipoPresente = params.tipo_presente || "cupom";
      if (tipoPresente === "brinde") return "Brinde na loja";
      return params.coupon_type === "percent"
        ? `Cupom ${params.coupon_value || "?"}% de desconto em ${params.coupon_valid_days || "?"} dias`
        : `Cupom R$ ${formatBRL(params.coupon_value || 0)} de desconto em ${params.coupon_valid_days || "?"} dias`;
    }
    if (tipo === "inactivity") {
      const valor =
        params.coupon_type === "fixed"
          ? `R$ ${formatBRL(params.coupon_value || 0)}`
          : `${params.coupon_value || "?"}%`;
      return `Inativo ${params.inactivity_days || "?"} dias -> ${valor} desconto`;
    }
    if (tipo === "welcome" || tipo === "welcome_app") {
      return `Boas-vindas: R$ ${formatBRL(params.coupon_value || 0)} de bonus`;
    }
    if (tipo === "ranking_monthly") {
      return `${Object.keys(params).length} niveis configurados`;
    }
    if (tipo === "quick_repurchase") {
      const valor =
        params.coupon_type === "fixed"
          ? `R$ ${formatBRL(params.coupon_value || 0)}`
          : `${params.coupon_value || "?"}%`;
      return `Pos-compra: ${valor} desconto em ${params.coupon_valid_days || "?"} dias | Canais: ${formatBenefitChannelsSummary(params)}`;
    }
    return `${JSON.stringify(params).slice(0, 60)}...`;
  };

  return {
    toggling,
    campanhaEditando,
    paramsEditando,
    setParamsEditando,
    salvandoParams,
    modalCriarCampanha,
    setModalCriarCampanha,
    novaCampanha,
    setNovaCampanha,
    criandoCampanha,
    erroCriarCampanha,
    setErroCriarCampanha,
    arquivando,
    criarCampanha,
    arquivarCampanha,
    toggleCampanha,
    abrirEdicao,
    fecharEdicao,
    salvarParametros,
    formatarParams,
  };
}
