import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../../../api";
import { useAuth } from "../../../contexts/AuthContext";
import { isAdminRole } from "../../../auth/userRole";
import { mensagemCashback, MODELO_CASHBACK, registrarEAbrirWhatsApp } from "./cashbackCrmUtils";

const BASE = "/campanhas/cashback/clientes";
const PAGINACAO_INICIAL = { pagina: 1, paginas: 1, total: 0, por_pagina: 25 };
const resumoInicial = { total_clientes: 0, saldo_total: 0, sem_contato: 0, retornos_pendentes: 0 };

function mensagemErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : error?.message || padrao;
}

export default function useCashbackCrm() {
  const { user } = useAuth();
  const podeEditar = isAdminRole(user) || Boolean(user?.permissions?.includes("clientes.editar"));
  const travaAcao = useRef(false);
  const tentativa = useRef(null);
  const [clientes, setClientes] = useState([]);
  const [resumo, setResumo] = useState(resumoInicial);
  const [paginacao, setPaginacao] = useState(PAGINACAO_INICIAL);
  const [pagina, setPagina] = useState(1);
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [status, setStatus] = useState("");
  const [retorno, setRetorno] = useState("todos");
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");
  const [revisao, setRevisao] = useState(0);
  const [modelo, setModelo] = useState(MODELO_CASHBACK);
  const [selecionado, setSelecionado] = useState(null);
  const [mensagem, setMensagem] = useState("");
  const [form, setForm] = useState({
    status: "sem_contato",
    observacao: "",
    proximo_contato_em: "",
  });
  const [contatos, setContatos] = useState([]);
  const [paginaHistorico, setPaginaHistorico] = useState(1);
  const [paginacaoHistorico, setPaginacaoHistorico] = useState(PAGINACAO_INICIAL);
  const [carregandoHistorico, setCarregandoHistorico] = useState(true);
  const [historicoInicializado, setHistoricoInicializado] = useState(false);
  const [erroHistorico, setErroHistorico] = useState("");
  const [ocupado, setOcupado] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setBuscaAplicada(busca.trim());
      setPagina(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [busca]);

  useEffect(() => {
    let ativo = true;
    const abort = new AbortController();
    setLoading(true);
    setErro("");
    (async () => {
      try {
        const response = await api.get(BASE, {
          params: {
            busca: buscaAplicada,
            status: status || undefined,
            retorno_pendente: retorno === "pendentes",
            pagina,
            por_pagina: 25,
          },
          signal: abort.signal,
        });
        if (!ativo) return;
        const novosClientes = response.data.clientes || [];
        setClientes(novosClientes);
        setSelecionado((atual) =>
          atual
            ? novosClientes.find((cliente) => cliente.cliente_id === atual.cliente_id) || atual
            : null,
        );
        setResumo(response.data.resumo || resumoInicial);
        setPaginacao(response.data.paginacao || PAGINACAO_INICIAL);
        const ultimaPagina = Math.max(1, response.data.paginacao?.paginas || 1);
        if (pagina > ultimaPagina) setPagina(ultimaPagina);
      } catch (error) {
        if (ativo)
          setErro(mensagemErro(error, "Não foi possível carregar os clientes com cashback."));
      } finally {
        if (ativo) setLoading(false);
      }
    })();
    return () => {
      ativo = false;
      abort.abort();
    };
  }, [buscaAplicada, pagina, retorno, revisao, status]);

  useEffect(() => {
    if (!selecionado) return undefined;
    let ativo = true;
    const abort = new AbortController();
    setCarregandoHistorico(true);
    setErroHistorico("");
    (async () => {
      try {
        const response = await api.get(`${BASE}/${selecionado.cliente_id}/contatos`, {
          params: { pagina: paginaHistorico, por_pagina: 25 },
          signal: abort.signal,
        });
        if (!ativo) return;
        setContatos(response.data.contatos || []);
        setPaginacaoHistorico(response.data.paginacao || PAGINACAO_INICIAL);
        setHistoricoInicializado(true);
      } catch (error) {
        if (ativo) setErroHistorico(mensagemErro(error, "Não foi possível carregar o histórico."));
      } finally {
        if (ativo) setCarregandoHistorico(false);
      }
    })();
    return () => {
      ativo = false;
      abort.abort();
    };
  }, [selecionado?.cliente_id, paginaHistorico, revisao]);

  const abrirCliente = (cliente) => {
    setSelecionado(cliente);
    setMensagem(mensagemCashback(modelo, cliente));
    setForm({
      status: cliente.status || "sem_contato",
      observacao: "",
      proximo_contato_em: cliente.proximo_contato_em || "",
    });
    setPaginaHistorico(1);
    setContatos([]);
    setCarregandoHistorico(true);
    setHistoricoInicializado(false);
    setErroHistorico("");
  };

  const atualizarAposContato = ({ contato, cliente }) => {
    setSelecionado((atual) => ({
      ...atual,
      ...cliente,
      status: cliente?.status ?? contato.status,
      proximo_contato_em: cliente ? cliente.proximo_contato_em : contato.proximo_contato_em,
    }));
    setForm((atual) => ({
      ...atual,
      status: cliente?.status ?? contato.status,
      proximo_contato_em: (cliente ? cliente.proximo_contato_em : contato.proximo_contato_em) || "",
      observacao: "",
    }));
    setPaginaHistorico(1);
    setRevisao((atual) => atual + 1);
  };

  const payloadIdempotente = (acao, payload) => {
    const identificador = JSON.stringify([selecionado.cliente_id, acao, payload]);
    if (tentativa.current?.identificador !== identificador) {
      tentativa.current = { identificador, chave: crypto.randomUUID() };
    }
    return { ...payload, chave_cliente: tentativa.current.chave };
  };

  const abrirWhatsApp = async () => {
    if (!selecionado || !mensagem.trim() || travaAcao.current || !podeEditar) return;
    if (mensagem.length > 2000) {
      toast.error("A mensagem deve ter até 2000 caracteres.");
      return;
    }
    travaAcao.current = true;
    setOcupado("whatsapp");
    try {
      const resultado = await registrarEAbrirWhatsApp({
        abrirAba: () => window.open("about:blank", "_blank"),
        registrar: async () =>
          (
            await api.post(
              `${BASE}/${selecionado.cliente_id}/contatos/whatsapp`,
              payloadIdempotente("whatsapp", { mensagem: mensagem.trim() }),
            )
          ).data,
      });
      tentativa.current = null;
      atualizarAposContato(resultado);
      toast.success("Conversa aberta e registrada no histórico.");
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível abrir o WhatsApp."));
    } finally {
      travaAcao.current = false;
      setOcupado("");
    }
  };

  const salvarAcompanhamento = async () => {
    if (!selecionado || travaAcao.current || !podeEditar) return;
    if (form.status === "retornar_depois" && !form.proximo_contato_em) {
      toast.error("Informe a data do próximo retorno.");
      return;
    }
    travaAcao.current = true;
    setOcupado("salvar");
    try {
      const response = await api.post(
        `${BASE}/${selecionado.cliente_id}/acompanhamento`,
        payloadIdempotente("acompanhamento", {
          ...form,
          observacao: form.observacao.trim() || null,
          proximo_contato_em: form.proximo_contato_em || null,
        }),
      );
      tentativa.current = null;
      atualizarAposContato(response.data);
      toast.success("Acompanhamento salvo no histórico.");
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível salvar o acompanhamento."));
    } finally {
      travaAcao.current = false;
      setOcupado("");
    }
  };

  return {
    clientes,
    resumo,
    paginacao,
    pagina,
    setPagina,
    busca,
    setBusca,
    status,
    podeEditar,
    mudarStatus: (valor) => {
      setStatus(valor);
      setPagina(1);
    },
    retorno,
    mudarRetorno: (valor) => {
      setRetorno(valor);
      setPagina(1);
    },
    loading,
    erro,
    recarregar: () => setRevisao((atual) => atual + 1),
    modelo,
    setModelo,
    selecionado,
    abrirCliente,
    fecharCliente: () => {
      if (!travaAcao.current) setSelecionado(null);
    },
    mensagem,
    setMensagem,
    form,
    setForm,
    contatos,
    paginaHistorico,
    setPaginaHistorico,
    paginacaoHistorico,
    carregandoHistorico,
    historicoInicializado,
    erroHistorico,
    ocupado,
    abrirWhatsApp,
    salvarAcompanhamento,
  };
}
