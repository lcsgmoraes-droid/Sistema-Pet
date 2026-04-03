import { useState } from "react";
import api from "../api";

export default function useCampanhasDestaque({
  destaque,
  premiosPorVencedor,
  vencedoresSelecionados,
}) {
  const [enviandoDestaque, setEnviandoDestaque] = useState(false);
  const [destaqueResultado, setDestaqueResultado] = useState(null);

  const enviarDestaque = async () => {
    if (!destaque?.vencedores || Object.keys(destaque.vencedores).length === 0) {
      return;
    }

    setEnviandoDestaque(true);
    setDestaqueResultado(null);
    try {
      const vencedoresComPremio = {};
      for (const [cat, info] of Object.entries(destaque.vencedores)) {
        if (!vencedoresSelecionados[cat]) continue;
        const premio = premiosPorVencedor[cat];
        vencedoresComPremio[cat] = {
          ...info,
          tipo_premio: premio.tipo_premio,
          coupon_value: premio.coupon_value,
          coupon_valid_days: premio.coupon_valid_days,
          mensagem:
            premio.tipo_premio === "cupom"
              ? premio.mensagem || ""
              : premio.mensagem_brinde || "",
          mensagem_brinde: premio.mensagem_brinde || "",
          retirar_de: premio.retirar_de || "",
          retirar_ate: premio.retirar_ate || "",
        };
      }

      const res = await api.post("/campanhas/destaque-mensal/enviar", {
        vencedores: vencedoresComPremio,
      });
      setDestaqueResultado(res.data);
    } catch (e) {
      alert(
        "Erro ao enviar prêmios: " + (e?.response?.data?.detail || e.message),
      );
    } finally {
      setEnviandoDestaque(false);
    }
  };

  return {
    enviandoDestaque,
    destaqueResultado,
    setDestaqueResultado,
    enviarDestaque,
  };
}
