import { useState } from "react";
import api from "../api";
import { debugLog } from "../utils/debug";

export function usePDVOportunidades(vendaAtual, userId) {
  const [painelOportunidadesAberto, setPainelOportunidadesAberto] =
    useState(false);
  const [opportunities, setOpportunities] = useState([]);

  const buscarOportunidades = async (vendaId) => {
    const clienteId = vendaAtual.cliente?.id;
    if (!clienteId) {
      setOpportunities([]);
      return;
    }

    try {
      const url = vendaId
        ? `/internal/pdv/oportunidades/${vendaId}`
        : `/internal/pdv/oportunidades-cliente/${clienteId}`;

      const response = await api.get(url);
      const data = response.data;

      if (data && Array.isArray(data.oportunidades)) {
        setOpportunities(data.oportunidades);
      } else {
        setOpportunities([]);
      }
    } catch {
      setOpportunities([]);
    }
  };

  const registrarEventoOportunidade = async (eventType, oportunidade) => {
    try {
      const payload = {
        opportunity_id: oportunidade.id,
        event_type: eventType,
        user_id: userId,
        contexto: "PDV",
        extra_data: {
          produto_origem_id: oportunidade.produto_origem_id || null,
          produto_sugerido_id: oportunidade.produto_sugerido_id || null,
          tipo_oportunidade: oportunidade.tipo || null,
          venda_id: vendaAtual.id || null,
        },
      };

      api.post("/internal/pdv/eventos-oportunidade", payload).catch(() => {
        // Erro silencioso - nunca afeta UX
      });
    } catch {
      // Fail-safe: erro silencioso
    }
  };

  const adicionarOportunidadeAoCarrinho = (oportunidade) => {
    void registrarEventoOportunidade("oportunidade_convertida", oportunidade);
    debugLog("Adicionar ao carrinho:", oportunidade.id);
  };

  const buscarAlternativaOportunidade = (oportunidade) => {
    void registrarEventoOportunidade("oportunidade_refinada", oportunidade);
    debugLog("Buscar alternativa:", oportunidade.id);
  };

  const ignorarOportunidade = (oportunidade) => {
    void registrarEventoOportunidade("oportunidade_rejeitada", oportunidade);
    setOpportunities((prev) => prev.filter((item) => item.id !== oportunidade.id));
  };

  const abrirPainelOportunidades = async () => {
    setPainelOportunidadesAberto(true);
    await buscarOportunidades(vendaAtual.id || null);
  };

  return {
    painelOportunidadesAberto,
    setPainelOportunidadesAberto,
    opportunities,
    buscarOportunidades,
    abrirPainelOportunidades,
    adicionarOportunidadeAoCarrinho,
    buscarAlternativaOportunidade,
    ignorarOportunidade,
  };
}
