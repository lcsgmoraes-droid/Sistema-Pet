import { useState } from "react";
import api from "../api";

export default function useCampanhasConfiguracoes({
  rankingConfig,
  setRankingConfig,
  schedulerConfig,
  setSchedulerConfig,
  carregarRanking,
  carregarSchedulerConfig,
}) {
  const [rankingConfigSalvando, setRankingConfigSalvando] = useState(false);
  const [schedulerConfigSalvando, setSchedulerConfigSalvando] = useState(false);

  const salvarRankingConfig = async () => {
    setRankingConfigSalvando(true);
    try {
      await api.put("/campanhas/ranking/config", rankingConfig);
      alert("Critérios de ranking salvos!");
    } catch (e) {
      alert("Erro ao salvar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setRankingConfigSalvando(false);
    }
  };

  const salvarSchedulerConfig = async () => {
    setSchedulerConfigSalvando(true);
    try {
      await api.put("/campanhas/config/horarios", schedulerConfig);
      await carregarSchedulerConfig();
      alert("Configurações de envio salvas!");
    } catch (e) {
      alert("Erro ao salvar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setSchedulerConfigSalvando(false);
    }
  };

  const recalcularRanking = async () => {
    try {
      await api.post("/campanhas/ranking/recalcular");
      alert(
        "Recálculo de ranking enfileirado! O worker processará em até 10 segundos.",
      );
      setTimeout(() => carregarRanking(), 3000);
    } catch (e) {
      alert("Erro: " + (e?.response?.data?.detail || e.message));
    }
  };

  return {
    rankingConfig,
    setRankingConfig,
    rankingConfigSalvando,
    schedulerConfig,
    setSchedulerConfig,
    schedulerConfigSalvando,
    salvarRankingConfig,
    salvarSchedulerConfig,
    recalcularRanking,
  };
}
