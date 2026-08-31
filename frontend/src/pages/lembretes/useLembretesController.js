import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import api from "../../api";
import { useModulos } from "../../contexts/ModulosContext";
import { confirmarCorePet } from "../../services/corepetDialog";
import { contarPorPrazo, filtrarLembretes, whatsappUrl } from "./lembretesUtils";

const initialValidityConfig = { carregado: false, ativa: null, dias: 15 };

function errorDetail(error, fallback) {
  return error?.response?.data?.detail || fallback;
}

export default function useLembretesController() {
  const { moduloAtivo } = useModulos();
  const navigate = useNavigate();
  const [abaAtiva, setAbaAtiva] = useState("recompras");
  const [lembretes, setLembretes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [alertasCampanhas, setAlertasCampanhas] = useState(null);
  const [validadePendencias, setValidadePendencias] = useState([]);
  const [validadeConfig, setValidadeConfig] = useState(initialValidityConfig);
  const [processandoValidade, setProcessandoValidade] = useState(false);
  const [filtroPrazo, setFiltroPrazo] = useState("todos");
  const [filtroTipo, setFiltroTipo] = useState("todos");
  const [busca, setBusca] = useState("");
  const [contatoAberto, setContatoAberto] = useState(null);
  const [mensagemContato, setMensagemContato] = useState("");
  const [contatos, setContatos] = useState([]);
  const [carregandoContatos, setCarregandoContatos] = useState(false);
  const [acaoContato, setAcaoContato] = useState("");
  const [relatorio, setRelatorio] = useState(null);

  const campanhasAtivo = moduloAtivo("campanhas");

  const carregarLembretes = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/lembretes/pendentes");
      setLembretes(response.data?.lembretes || []);
    } catch (error) {
      console.error("Erro ao carregar lembretes:", error);
      toast.error("Erro ao carregar lembretes");
    } finally {
      setLoading(false);
    }
  }, []);

  const carregarAlertasCampanhas = useCallback(async () => {
    try {
      const response = await api.get("/campanhas/dashboard");
      setAlertasCampanhas(response.data);
    } catch {
      setAlertasCampanhas(null);
    }
  }, []);

  const carregarRelatorio = useCallback(async () => {
    try {
      const response = await api.get("/lembretes/relatorios/resumo", {
        params: { dias: 30 },
      });
      setRelatorio(response.data);
    } catch {
      setRelatorio(null);
    }
  }, []);

  const carregarValidadePendencias = useCallback(
    async ({ processar = false, mostrarToast = false } = {}) => {
      let configAtual = initialValidityConfig;
      try {
        const configRes = await api.get("/empresa/config-estoque");
        configAtual = {
          carregado: true,
          ativa: Boolean(configRes.data?.protecao_validade_ativa),
          dias: Number(configRes.data?.dias_alerta_validade || 15),
        };
        setValidadeConfig(configAtual);
      } catch {
        setValidadeConfig((previous) => ({ ...previous, carregado: false, ativa: null }));
      }

      if (processar && configAtual.ativa === true) {
        setProcessandoValidade(true);
        try {
          const processRes = await api.post("/estoque/validade/processar");
          const processed = Number(processRes.data?.processados || 0);
          if (mostrarToast) {
            toast.success(
              processed > 0
                ? `${processed} lote(s) removido(s) do estoque vendável`
                : "Nenhum lote novo em risco encontrado",
            );
          }
        } catch (error) {
          console.error("Erro ao processar validade:", error);
          if (mostrarToast) toast.error("Não foi possível verificar a validade agora");
        } finally {
          setProcessandoValidade(false);
        }
      } else if (processar && mostrarToast && configAtual.ativa === false) {
        toast("Ative a proteção por validade nas configurações de estoque.");
      }

      try {
        const response = await api.get("/estoque/validade/pendencias");
        setValidadePendencias(Array.isArray(response.data?.items) ? response.data.items : []);
      } catch {
        setValidadePendencias([]);
      }
    },
    [],
  );

  useEffect(() => {
    void carregarLembretes();
    void carregarRelatorio();
    if (campanhasAtivo) void carregarAlertasCampanhas();
    else setAlertasCampanhas(null);
    void carregarValidadePendencias({ processar: true });
    const interval = setInterval(() => {
      void carregarLembretes();
      void carregarRelatorio();
      void carregarValidadePendencias();
    }, 60000);
    return () => clearInterval(interval);
  }, [
    campanhasAtivo,
    carregarAlertasCampanhas,
    carregarLembretes,
    carregarRelatorio,
    carregarValidadePendencias,
  ]);

  const completarLembrete = useCallback(
    async (id) => {
      try {
        await api.post(`/lembretes/${id}/completar`, {});
        toast.success("Recompra registrada");
        await Promise.all([carregarLembretes(), carregarRelatorio()]);
      } catch (error) {
        toast.error(errorDetail(error, "Erro ao registrar recompra"));
      }
    },
    [carregarLembretes, carregarRelatorio],
  );

  const renovarLembrete = useCallback(
    async (id) => {
      try {
        await api.post(`/lembretes/${id}/renovar`, {});
        toast.success("Próximo lembrete criado");
        void carregarLembretes();
      } catch (error) {
        toast.error(errorDetail(error, "Erro ao renovar lembrete"));
      }
    },
    [carregarLembretes],
  );

  const cancelarLembrete = useCallback(
    async (id) => {
      if (!(await confirmarCorePet("Tem certeza que deseja cancelar este lembrete?"))) return;
      try {
        await api.delete(`/lembretes/${id}`);
        toast.success("Lembrete cancelado");
        void carregarLembretes();
      } catch (error) {
        toast.error(errorDetail(error, "Erro ao cancelar lembrete"));
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
        descartar: "Registrar este lote como descartado e prejuízo?",
        trocar: "Registrar este lote como trocado com o fornecedor?",
        retornar: "Retornar este lote para o estoque vendável?",
      };
      if (!endpoints[acao] || !(await confirmarCorePet(mensagens[acao]))) return;
      try {
        await api.post(`/estoque/validade/${item.id}/${endpoints[acao]}`, {
          observacao: null,
        });
        toast.success("Pendência de validade atualizada");
        void carregarValidadePendencias();
      } catch (error) {
        console.error("Erro ao resolver pendência de validade:", error);
        toast.error("Erro ao atualizar pendência de validade");
      }
    },
    [carregarValidadePendencias],
  );

  const carregarContatos = useCallback(async (id) => {
    setCarregandoContatos(true);
    try {
      const response = await api.get(`/lembretes/${id}/contatos`);
      setContatos(response.data?.contatos || []);
    } catch {
      setContatos([]);
    } finally {
      setCarregandoContatos(false);
    }
  }, []);

  const abrirContato = useCallback(
    (lembrete) => {
      setContatoAberto(lembrete);
      setMensagemContato(lembrete.mensagem_sugerida || "");
      setContatos([]);
      void carregarContatos(lembrete.id);
    },
    [carregarContatos],
  );

  const atualizarAposContato = useCallback(
    async (id) => {
      await Promise.all([carregarContatos(id), carregarLembretes(), carregarRelatorio()]);
    },
    [carregarContatos, carregarLembretes, carregarRelatorio],
  );

  const enviarPush = useCallback(
    async (lembrete, mensagem = lembrete.mensagem_sugerida) => {
      setAcaoContato(`push-${lembrete.id}`);
      try {
        await api.post(`/lembretes/${lembrete.id}/notificar-app`, {
          mensagem,
          chave_cliente: crypto.randomUUID(),
        });
        toast.success("Notificação adicionada à fila de envio");
        await atualizarAposContato(lembrete.id);
      } catch (error) {
        toast.error(errorDetail(error, "Não foi possível enviar a notificação"));
      } finally {
        setAcaoContato("");
      }
    },
    [atualizarAposContato],
  );

  const abrirWhatsApp = useCallback(async () => {
    if (!contatoAberto) return;
    const url = whatsappUrl(contatoAberto.cliente_telefone, mensagemContato);
    if (!url) {
      toast.error("Cliente sem telefone válido");
      return;
    }
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      toast.error("O navegador bloqueou a nova aba do WhatsApp");
      return;
    }
    popup.opener = null;
    setAcaoContato("whatsapp");
    try {
      await api.post(`/lembretes/${contatoAberto.id}/contatos/whatsapp`, {
        mensagem: mensagemContato,
        chave_cliente: crypto.randomUUID(),
      });
      popup.location.replace(url);
      toast.success("Conversa aberta e registrada no histórico");
      await atualizarAposContato(contatoAberto.id);
    } catch (error) {
      popup.close();
      toast.error(errorDetail(error, "Não foi possível abrir o WhatsApp"));
    } finally {
      setAcaoContato("");
    }
  }, [atualizarAposContato, contatoAberto, mensagemContato]);

  const copiarMensagem = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(mensagemContato);
      toast.success("Mensagem copiada");
    } catch {
      toast.error("Não foi possível copiar a mensagem");
    }
  }, [mensagemContato]);

  const vencidos = useMemo(() => lembretes.filter((item) => item.dias_restantes < 0), [lembretes]);
  const proximosEmBreve = useMemo(
    () => lembretes.filter((item) => item.dias_restantes >= 0 && item.dias_restantes <= 7),
    [lembretes],
  );
  const contadoresPrazo = useMemo(() => contarPorPrazo(lembretes), [lembretes]);
  const lembretesFiltrados = useMemo(
    () => filtrarLembretes(lembretes, { busca, prazo: filtroPrazo, tipo: filtroTipo }),
    [busca, filtroPrazo, filtroTipo, lembretes],
  );

  return {
    abaAtiva,
    acaoContato,
    alertasCampanhas,
    abrirContato,
    abrirWhatsApp,
    busca,
    cancelarLembrete,
    carregandoContatos,
    carregarValidadePendencias,
    completarLembrete,
    contatoAberto,
    contatos,
    contadoresPrazo,
    copiarMensagem,
    enviarPush,
    fecharContato: () => setContatoAberto(null),
    filtroPrazo,
    filtroTipo,
    irConfiguracoesEstoque: () => navigate("/configuracoes/estoque"),
    lembretes,
    lembretesFiltrados,
    loading,
    mensagemContato,
    processandoValidade,
    proximosEmBreve,
    relatorio,
    renovarLembrete,
    resolverValidade,
    setAbaAtiva,
    setBusca,
    setFiltroPrazo,
    setFiltroTipo,
    setMensagemContato,
    validadeAtivaSemPendencias: validadeConfig.ativa === true && validadePendencias.length === 0,
    validadeConfig,
    validadeInativa: validadeConfig.carregado && validadeConfig.ativa === false,
    validadePendencias,
    vencidos,
  };
}
