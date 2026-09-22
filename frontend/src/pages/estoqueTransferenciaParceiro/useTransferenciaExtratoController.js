import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import { criarExtratoTransferenciaVazio } from "./extratoTransferenciaUtils";

export default function useTransferenciaExtratoController({
  filtrosAplicados,
  pessoaSelecionada,
} = {}) {
  const [extrato, setExtrato] = useState(() => criarExtratoTransferenciaVazio());
  const [loadingExtrato, setLoadingExtrato] = useState(false);
  const [erroExtrato, setErroExtrato] = useState("");
  const [focoExtrato, setFocoExtrato] = useState("todos");
  const extratoRef = useRef(null);
  const requestIdRef = useRef(0);

  const parceiroId = String(filtrosAplicados?.parceiro_id || "");
  const pessoaId = String(pessoaSelecionada?.id || "");
  const pessoaFiltroAplicada = Boolean(pessoaId && pessoaId === parceiroId);
  const statusFiltro = filtrosAplicados?.status_filtro || "";
  const dataInicio = filtrosAplicados?.data_inicio || "";
  const dataFim = filtrosAplicados?.data_fim || "";

  const carregarExtrato = useCallback(
    async (filtros = null) => {
      const parceiroIdAtual = String(filtros?.parceiro_id || parceiroId || "");
      if (!pessoaId || pessoaId !== parceiroIdAtual) {
        requestIdRef.current += 1;
        setExtrato(criarExtratoTransferenciaVazio());
        setLoadingExtrato(false);
        setErroExtrato("");
        return;
      }

      const requestId = ++requestIdRef.current;
      try {
        setLoadingExtrato(true);
        setErroExtrato("");
        const response = await api.get("/estoque/transferencia-parceiro/extrato", {
          params: {
            parceiro_id: parceiroIdAtual,
            status_filtro: filtros?.status_filtro || statusFiltro || undefined,
            data_inicio: filtros?.data_inicio || dataInicio || undefined,
            data_fim: filtros?.data_fim || dataFim || undefined,
          },
        });
        if (requestId === requestIdRef.current) setExtrato(response.data);
      } catch (error) {
        console.error("Erro ao carregar extrato da pessoa:", error);
        if (requestId === requestIdRef.current) {
          setExtrato(criarExtratoTransferenciaVazio());
          setErroExtrato("Nao foi possivel carregar o extrato desta pessoa.");
          toast.error("Nao foi possivel carregar o extrato da pessoa.");
        }
      } finally {
        if (requestId === requestIdRef.current) setLoadingExtrato(false);
      }
    },
    [dataFim, dataInicio, parceiroId, pessoaId, statusFiltro],
  );

  useEffect(() => {
    void carregarExtrato();
  }, [carregarExtrato]);

  const abrirExtrato = (foco = "todos") => {
    if (!pessoaFiltroAplicada) {
      toast("Selecione uma pessoa para abrir o extrato detalhado.");
      return;
    }
    setFocoExtrato(foco);
    window.requestAnimationFrame(() => {
      extratoRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  return {
    extrato,
    loadingExtrato,
    erroExtrato,
    focoExtrato,
    setFocoExtrato,
    extratoRef,
    pessoaFiltroAplicada,
    abrirExtrato,
    recarregarExtrato: carregarExtrato,
  };
}
