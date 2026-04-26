import { useCallback, useEffect, useMemo, useState } from "react";

import { vetApi } from "../vetApi";
import { CONSULTAS_POR_PAGINA, filtrarConsultas } from "./consultasUtils";

export function useVetConsultas() {
  const [consultas, setConsultas] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      setErro(null);
      const res = await vetApi.listarConsultas({
        skip: (pagina - 1) * CONSULTAS_POR_PAGINA,
        limit: CONSULTAS_POR_PAGINA,
        status: filtroStatus || undefined,
      });
      const data = res.data;

      if (Array.isArray(data)) {
        setConsultas(data);
        setTotal(data.length);
      } else {
        setConsultas(data.items ?? []);
        setTotal(data.total ?? 0);
      }
    } catch {
      setErro("Nao foi possivel carregar as consultas.");
    } finally {
      setCarregando(false);
    }
  }, [pagina, filtroStatus]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const consultasFiltradas = useMemo(
    () => filtrarConsultas(consultas, busca),
    [busca, consultas]
  );
  const totalPaginas = Math.ceil(total / CONSULTAS_POR_PAGINA);

  function alterarStatus(status) {
    setFiltroStatus(status);
    setPagina(1);
  }

  return {
    alterarStatus,
    busca,
    carregando,
    consultasFiltradas,
    erro,
    filtroStatus,
    pagina,
    setBusca,
    setPagina,
    total,
    totalPaginas,
  };
}
