import { useEffect, useMemo, useState } from "react";

import { vetApi } from "../vetApi";
import { hojeIso } from "./examesAnexadosUtils";

export function useExamesAnexadosList() {
  const [periodo, setPeriodo] = useState("hoje");
  const [dataInicio, setDataInicio] = useState(hojeIso());
  const [dataFim, setDataFim] = useState(hojeIso());
  const [tutorBusca, setTutorBusca] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState({ items: [], total: 0 });

  const itens = useMemo(() => (Array.isArray(dados.items) ? dados.items : []), [dados]);

  async function carregar() {
    try {
      setCarregando(true);
      setErro("");

      const params = {
        periodo,
        tutor: tutorBusca.trim() || undefined,
      };

      if (periodo === "periodo") {
        params.data_inicio = dataInicio;
        params.data_fim = dataFim;
      }

      const res = await vetApi.listarExamesAnexados(params);
      setDados(res.data || { items: [], total: 0 });
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao carregar exames anexados.");
      setDados({ items: [], total: 0 });
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  function limparFiltros() {
    setPeriodo("hoje");
    setDataInicio(hojeIso());
    setDataFim(hojeIso());
    setTutorBusca("");
  }

  return {
    carregar,
    carregando,
    dados,
    dataFim,
    dataInicio,
    erro,
    itens,
    limparFiltros,
    periodo,
    setDados,
    setDataFim,
    setDataInicio,
    setPeriodo,
    setTutorBusca,
    tutorBusca,
  };
}
