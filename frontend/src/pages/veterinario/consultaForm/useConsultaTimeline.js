import { useEffect, useState } from "react";

import { vetApi } from "../vetApi";

export default function useConsultaTimeline(consultaIdAtual) {
  const [timelineConsulta, setTimelineConsulta] = useState([]);
  const [carregandoTimeline, setCarregandoTimeline] = useState(false);

  async function carregarTimelineConsulta(id = consultaIdAtual) {
    if (!id) return;
    setCarregandoTimeline(true);
    try {
      const res = await vetApi.obterTimelineConsulta(id);
      setTimelineConsulta(Array.isArray(res.data?.eventos) ? res.data.eventos : []);
    } catch {
      setTimelineConsulta([]);
    } finally {
      setCarregandoTimeline(false);
    }
  }

  useEffect(() => {
    if (!consultaIdAtual) {
      setTimelineConsulta([]);
      return;
    }
    carregarTimelineConsulta(consultaIdAtual);
  }, [consultaIdAtual]);

  return {
    timelineConsulta,
    carregandoTimeline,
    carregarTimelineConsulta,
  };
}
