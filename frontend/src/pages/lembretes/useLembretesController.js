import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import api from "../../api";
import { useModulos } from "../../contexts/ModulosContext";

export default function useLembretesController() {
  const { moduloAtivo } = useModulos();
  const navigate = useNavigate();
  const [lembretes, setLembretes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [alertasCampanhas, setAlertasCampanhas] = useState(null);
  const [dresPendentes, setDresPendentes] = useState(0);
  const [autocadastrosBling, setAutocadastrosBling] = useState({ total: 0, items: [] });
  const [validadePendencias, setValidadePendencias] = useState([]);
  const [validadeConfig, setValidadeConfig] = useState({
    carregado: false,
    ativa: null,
    dias: 15,
  });
  const [processandoValidade, setProcessandoValidade] = useState(false);

  const campanhasAtivo = moduloAtivo("campanhas");
  const financeiroErpAtivo = moduloAtivo("financeiro_erp");
  const blingAtivo = moduloAtivo("bling");

  const carregarAutocadastrosBling = useCallback(async () => {
    try {
      const res = await api.get("/integracoes/bling/nf/autocadastros-recentes", {
        params: { horas: 24, limite: 20 },
      });
      setAutocadastrosBling({
        total: Number(res.data?.total || 0),
        items: Array.isArray(res.data?.items) ? res.data.items : [],
      });
    } catch {
      setAutocadastrosBling({ total: 0, items: [] });
    }
  }, []);

  const carregarAlertasCampanhas = useCallback(async () => {
    try {
      const res = await api.get("/campanhas/dashboard");
      setAlertasCampanhas(res.data);
    } catch {
      // Alertas de campanhas sao informativos.
    }
  }, []);

  const carregarDresPendentes = useCallback(async () => {
    try {
      const res = await api.get("/dre/classificar/pendentes");
      setDresPendentes(res.data?.total_pendentes || 0);
    } catch {
      // Silencioso: o card e apenas um aviso.
    }
  }, []);

  const carregarValidadePendencias = useCallback(
    async ({ processar = false, mostrarToast = false } = {}) => {
      let configAtual = { carregado: false, ativa: null, dias: 15 };

      try {
        const configRes = await api.get("/empresa/config-estoque");
        configAtual = {
          carregado: true,
          ativa: Boolean(configRes.data?.protecao_validade_ativa),
          dias: Number(configRes.data?.dias_alerta_validade || 15),
        };
        setValidadeConfig(configAtual);
      } catch {
        setValidadeConfig((prev) => ({ ...prev, carregado: false, ativa: null }));
      }

      if (processar && configAtual.ativa === true) {
        setProcessandoValidade(true);
        try {
          const processRes = await api.post("/estoque/validade/processar");
          const processados = Number(processRes.data?.processados || 0);
          if (mostrarToast) {
            toast.success(
              processados > 0
                ? `${processados} lote(s) removido(s) do estoque vendavel`
                : "Nenhum lote novo em risco encontrado",
            );
          }
        } catch (error) {
          console.error("Erro ao processar validade:", error);
          if (mostrarToast) toast.error("Nao foi possivel verificar validade agora");
        } finally {
          setProcessandoValidade(false);
        }
      } else if (processar && mostrarToast && configAtual.ativa === false) {
        toast("Ative a protecao por validade nas configuracoes de estoque.");
      }

      try {
        const res = await api.get("/estoque/validade/pendencias");
        setValidadePendencias(Array.isArray(res.data?.items) ? res.data.items : []);
      } catch {
        setValidadePendencias([]);
      }
    },
    [],
  );

  const carregarLembretes = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/lembretes/pendentes");
      setLembretes(response.data.lembretes || []);
    } catch (error) {
      console.error("Erro ao carregar lembretes:", error);
      toast.error("Erro ao carregar lembretes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregarLembretes();
    if (campanhasAtivo) void carregarAlertasCampanhas();
    else setAlertasCampanhas(null);
    if (financeiroErpAtivo) void carregarDresPendentes();
    else setDresPendentes(0);
    if (blingAtivo) void carregarAutocadastrosBling();
    else setAutocadastrosBling({ total: 0, items: [] });
    void carregarValidadePendencias({ processar: true });

    const interval = setInterval(() => {
      void carregarLembretes();
      if (blingAtivo) void carregarAutocadastrosBling();
      void carregarValidadePendencias();
    }, 60000);
    return () => clearInterval(interval);
  }, [
    blingAtivo,
    campanhasAtivo,
    carregarAlertasCampanhas,
    carregarAutocadastrosBling,
    carregarDresPendentes,
    carregarLembretes,
    carregarValidadePendencias,
    financeiroErpAtivo,
  ]);

  const completarLembrete = useCallback(
    async (lembrete_id) => {
      try {
        await api.post(`/lembretes/${lembrete_id}/completar`, {});
        toast.success("Lembrete marcado como completado");
        void carregarLembretes();
      } catch {
        toast.error("Erro ao completar lembrete");
      }
    },
    [carregarLembretes],
  );

  const renovarLembrete = useCallback(
    async (lembrete_id) => {
      try {
        await api.post(`/lembretes/${lembrete_id}/renovar`, {});
        toast.success("Lembrete renovado com sucesso");
        void carregarLembretes();
      } catch {
        toast.error("Erro ao renovar lembrete");
      }
    },
    [carregarLembretes],
  );

  const cancelarLembrete = useCallback(
    async (lembrete_id) => {
      if (!window.confirm("Tem certeza que deseja cancelar este lembrete?")) return;
      try {
        await api.delete(`/lembretes/${lembrete_id}`);
        toast.success("Lembrete cancelado");
        void carregarLembretes();
      } catch {
        toast.error("Erro ao cancelar lembrete");
      }
    },
    [carregarLembretes],
  );

  const resolverValidade = useCallback(
    async (item, acao) => {
      const endpoints = {
        descartar: "descartar",
        trocar: "trocar-fornecedor",
        retornar: "retornar-vendavel",
      };
      const mensagens = {
        descartar: "Registrar este lote como descartado e prejuizo?",
        trocar: "Registrar este lote como trocado com o fornecedor?",
        retornar: "Retornar este lote para o estoque vendavel?",
      };

      if (!endpoints[acao]) return;
      if (!window.confirm(mensagens[acao])) return;

      try {
        await api.post(`/estoque/validade/${item.id}/${endpoints[acao]}`, {
          observacao: null,
        });
        toast.success("Pendencia de validade atualizada");
        void carregarValidadePendencias();
      } catch (error) {
        console.error("Erro ao resolver pendencia de validade:", error);
        toast.error("Erro ao atualizar pendencia de validade");
      }
    },
    [carregarValidadePendencias],
  );

  const vencidos = useMemo(() => lembretes.filter((l) => l.dias_restantes < 0), [lembretes]);
  const proximosEmBreve = useMemo(
    () => lembretes.filter((l) => l.dias_restantes <= 7),
    [lembretes],
  );
  const futuros = useMemo(() => lembretes.filter((l) => l.dias_restantes > 7), [lembretes]);
  const semPendencias = lembretes.length === 0 && validadePendencias.length === 0;
  const validadeInativa = validadeConfig.carregado && validadeConfig.ativa === false;
  const validadeAtivaSemPendencias =
    validadeConfig.ativa === true && validadePendencias.length === 0;

  return {
    alertasCampanhas,
    autocadastrosBling,
    cancelarLembrete,
    carregarValidadePendencias,
    completarLembrete,
    dresPendentes,
    futuros,
    irConfiguracoesEstoque: () => navigate("/configuracoes/estoque"),
    irDre: () => navigate("/financeiro/dre"),
    irProdutoBling: (item) => navigate(`/produtos?busca=${encodeURIComponent(item.codigo || "")}`),
    lembretes,
    loading,
    processandoValidade,
    proximosEmBreve,
    renovarLembrete,
    resolverValidade,
    semPendencias,
    validadeAtivaSemPendencias,
    validadeConfig,
    validadeInativa,
    validadePendencias,
    vencidos,
  };
}
