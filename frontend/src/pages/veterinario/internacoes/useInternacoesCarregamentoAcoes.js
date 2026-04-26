import { useCallback } from "react";

import { vetApi } from "../vetApi";

export function useInternacoesCarregamentoAcoes({
  aba,
  expandida,
  filtroDataAltaFim,
  filtroDataAltaInicio,
  filtroPessoaHistorico,
  filtroPetHistorico,
  setCarregando,
  setCarregandoHistoricoPet,
  setErro,
  setEvolucoes,
  setExpandida,
  setHistoricoPet,
  setInternacoes,
  setModalHistoricoPet,
  setProcedimentosInternacao,
}) {
  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      const params =
        aba === "ativas"
          ? { status: "internado" }
          : {
              status: "alta",
              data_saida_inicio: filtroDataAltaInicio || undefined,
              data_saida_fim: filtroDataAltaFim || undefined,
              cliente_id: filtroPessoaHistorico || undefined,
              pet_id: filtroPetHistorico || undefined,
            };
      const res = await vetApi.listarInternacoes(params);
      setInternacoes(Array.isArray(res.data) ? res.data : res.data?.items ?? []);
    } catch {
      setErro("Erro ao carregar internações.");
    } finally {
      setCarregando(false);
    }
  }, [
    aba,
    filtroDataAltaFim,
    filtroDataAltaInicio,
    filtroPessoaHistorico,
    filtroPetHistorico,
    setCarregando,
    setErro,
    setInternacoes,
  ]);

  const carregarDetalheInternacao = useCallback(
    async (id, manterExpandido = true) => {
      try {
        const res = await vetApi.obterInternacao(id);
        setEvolucoes((prev) => ({ ...prev, [id]: res.data?.evolucoes ?? [] }));
        setProcedimentosInternacao((prev) => ({ ...prev, [id]: res.data?.procedimentos ?? [] }));
        if (manterExpandido) setExpandida(id);
      } catch {}
    },
    [setEvolucoes, setExpandida, setProcedimentosInternacao]
  );

  const abrirDetalhe = useCallback(
    async (id) => {
      const fechando = expandida === id;
      setExpandida(fechando ? null : id);
      if (!fechando) {
        await carregarDetalheInternacao(id, true);
      }
    },
    [carregarDetalheInternacao, expandida, setExpandida]
  );

  const abrirHistoricoPet = useCallback(
    async (petId, petNome) => {
      setCarregandoHistoricoPet(true);
      setModalHistoricoPet({ petId, petNome });
      setHistoricoPet([]);
      try {
        const res = await vetApi.historicoInternacoesPet(petId);
        setHistoricoPet(Array.isArray(res.data?.historico) ? res.data.historico : []);
      } catch (e) {
        setErro(e?.response?.data?.detail ?? "Erro ao carregar histórico do pet.");
        setHistoricoPet([]);
      } finally {
        setCarregandoHistoricoPet(false);
      }
    },
    [setCarregandoHistoricoPet, setErro, setHistoricoPet, setModalHistoricoPet]
  );

  return {
    abrirDetalhe,
    abrirHistoricoPet,
    carregar,
    carregarDetalheInternacao,
  };
}
