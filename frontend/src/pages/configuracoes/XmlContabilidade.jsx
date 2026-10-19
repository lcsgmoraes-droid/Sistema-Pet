import { useEffect, useState } from "react";
import { FileArchive, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import api from "../../api";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import XmlContabilidadeConfig from "./XmlContabilidadeConfig";
import XmlContabilidadeLote from "./XmlContabilidadeLote";
import XmlContabilidadeHistorico from "./XmlContabilidadeHistorico";
import {
  agendamentoBrasilia,
  erroPeriodo,
  mensagemErroContabilidade,
  periodoMesAnterior,
} from "./xmlContabilidadeUtils.mjs";

const BASE = "/contabilidade/xml";
const CONFIG_INICIAL = {
  email_contador: "",
  envio_automatico: false,
  envio_mensal: false,
  dia_envio_mensal: 1,
  hora_envio_mensal: "08:00",
  smtp_configurado: false,
};

function normalizarConfig(dados) {
  return { ...CONFIG_INICIAL, ...dados, email_contador: dados?.email_contador || "" };
}

function payloadConfig(config) {
  return {
    email_contador: config.email_contador.trim(),
    envio_automatico: config.envio_automatico,
    envio_mensal: config.envio_mensal,
    dia_envio_mensal: Number(config.dia_envio_mensal),
    hora_envio_mensal: config.hora_envio_mensal,
  };
}

const listaEnvios = (dados) => (Array.isArray(dados) ? dados : dados?.items || []);

export default function XmlContabilidade() {
  const [loading, setLoading] = useState(true);
  const [erroInicial, setErroInicial] = useState("");
  const [versao, setVersao] = useState(0);
  const [config, setConfig] = useState(CONFIG_INICIAL);
  const [configSalva, setConfigSalva] = useState(CONFIG_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [envios, setEnvios] = useState([]);
  const [atualizando, setAtualizando] = useState(false);
  const [erroHistorico, setErroHistorico] = useState("");
  const [periodo, setPeriodo] = useState(() => periodoMesAnterior());
  const [erroDoPeriodo, setErroDoPeriodo] = useState("");
  const [agendadoPara, setAgendadoPara] = useState("");
  const [operacao, setOperacao] = useState("");

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setErroInicial("");
    (async () => {
      try {
        const [resConfig, resEnvios] = await Promise.all([
          api.get(`${BASE}/config`),
          api.get(`${BASE}/envios`),
        ]);
        if (!ativo) return;
        const carregada = normalizarConfig(resConfig.data);
        setConfig(carregada);
        setConfigSalva(carregada);
        setEnvios(listaEnvios(resEnvios.data));
      } catch (erro) {
        const mensagem = await mensagemErroContabilidade(
          erro,
          "Não foi possível carregar os XMLs para contabilidade.",
        );
        if (ativo) setErroInicial(mensagem);
      } finally {
        if (ativo) setLoading(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, [versao]);

  const temEnvioEmAndamento = envios.some((envio) =>
    ["pendente", "processando", "agendado"].includes(envio.status),
  );
  useEffect(() => {
    if (!temEnvioEmAndamento || loading) return undefined;
    let ativo = true;
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get(`${BASE}/envios`);
        if (ativo) {
          setEnvios(listaEnvios(data));
          setErroHistorico("");
        }
      } catch {
        if (ativo)
          setErroHistorico(
            "A atualização automática do histórico falhou. Use Atualizar para tentar novamente.",
          );
      }
    }, 15000);
    return () => {
      ativo = false;
      clearInterval(timer);
    };
  }, [temEnvioEmAndamento, loading]);

  const alterado =
    JSON.stringify(payloadConfig(config)) !== JSON.stringify(payloadConfig(configSalva));
  const bloqueioEnvio = !configSalva.smtp_configurado
    ? "O serviço de e-mail precisa estar configurado para enviar."
    : !configSalva.email_contador
      ? "Informe e salve o e-mail do contador antes de enviar."
      : alterado || salvando
        ? "Salve as alterações da configuração antes de enviar."
        : "";

  async function atualizarHistorico() {
    setAtualizando(true);
    try {
      const { data } = await api.get(`${BASE}/envios`);
      setEnvios(listaEnvios(data));
      setErroHistorico("");
    } catch (erro) {
      setErroHistorico(
        await mensagemErroContabilidade(erro, "Não foi possível atualizar o histórico."),
      );
    } finally {
      setAtualizando(false);
    }
  }

  async function salvar(evento) {
    evento.preventDefault();
    const payload = payloadConfig(config);
    if ((payload.envio_automatico || payload.envio_mensal) && !payload.email_contador) {
      toast.error("Informe o e-mail do contador para ativar o envio automático.");
      return;
    }
    setSalvando(true);
    try {
      const { data } = await api.put(`${BASE}/config`, payload);
      const salva = normalizarConfig(data);
      setConfig(salva);
      setConfigSalva(salva);
      toast.success("Configuração salva.");
    } catch (erro) {
      toast.error(await mensagemErroContabilidade(erro, "Não foi possível salvar a configuração."));
    } finally {
      setSalvando(false);
    }
  }

  function validarPeriodo() {
    const mensagem = erroPeriodo(periodo);
    setErroDoPeriodo(mensagem);
    return !mensagem;
  }

  async function baixar() {
    if (!validarPeriodo()) return;
    setOperacao("baixar");
    try {
      const { data } = await api.post(
        `${BASE}/lotes/download`,
        {
          data_inicio: periodo.inicio,
          data_fim: periodo.fim,
        },
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(new Blob([data], { type: "application/zip" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `xmls_saida_${periodo.inicio}_${periodo.fim}.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast.success("Download do ZIP iniciado.");
    } catch (erro) {
      toast.error(
        await mensagemErroContabilidade(erro, "Não foi possível baixar os XMLs do período."),
      );
    } finally {
      setOperacao("");
    }
  }

  async function enviar(agendar = false) {
    if (!validarPeriodo() || bloqueioEnvio) return;
    const payload = { data_inicio: periodo.inicio, data_fim: periodo.fim };
    if (agendar) {
      try {
        payload.agendado_para = agendamentoBrasilia(agendadoPara);
      } catch (erro) {
        toast.error(erro.message);
        return;
      }
    }
    setOperacao(agendar ? "agendar" : "enviar");
    try {
      await api.post(`${BASE}/envios`, payload);
      toast.success(
        agendar
          ? "Envio agendado. Acompanhe no histórico."
          : "Envio colocado na fila. Acompanhe no histórico.",
      );
      if (agendar) setAgendadoPara("");
      await atualizarHistorico();
    } catch (erro) {
      toast.error(await mensagemErroContabilidade(erro, "Não foi possível registrar o envio."));
    } finally {
      setOperacao("");
    }
  }

  async function acaoEnvio(id, acao) {
    if (acao === "reenviar" && bloqueioEnvio) return;
    setOperacao(`${acao}-${id}`);
    try {
      await api.post(`${BASE}/envios/${encodeURIComponent(id)}/${acao}`);
      toast.success(acao === "cancelar" ? "Envio cancelado." : "Envio colocado novamente na fila.");
      await atualizarHistorico();
    } catch (erro) {
      toast.error(await mensagemErroContabilidade(erro, "Não foi possível atualizar o envio."));
    } finally {
      setOperacao("");
    }
  }

  if (loading)
    return (
      <div role="status" className="p-10 text-center text-slate-600 dark:text-slate-300">
        Carregando XMLs para contabilidade...
      </div>
    );
  if (erroInicial)
    return (
      <div className="mx-auto max-w-6xl space-y-4 p-6">
        <LinkPadrao to="/configuracoes">Voltar para Configurações</LinkPadrao>
        <Panel title="XML para contabilidade">
          <p role="alert" className="mb-4 text-sm text-red-700 dark:text-red-300">
            {erroInicial}
          </p>
          <BotaoInteracao icon={RefreshCw} onClick={() => setVersao((valor) => valor + 1)}>
            Tentar novamente
          </BotaoInteracao>
        </Panel>
      </div>
    );
  return (
    <div className="mx-auto max-w-6xl space-y-6 p-3 sm:p-6">
      <LinkPadrao to="/configuracoes">Voltar para Configurações</LinkPadrao>
      <PageHeader
        icon={FileArchive}
        title="XML para contabilidade"
        subtitle="Envie os XMLs das notas de saída ao contador, automaticamente ou por período."
      />
      <XmlContabilidadeConfig
        config={config}
        onChange={setConfig}
        onSalvar={salvar}
        salvando={salvando || Boolean(operacao)}
        alterado={alterado}
      />
      <XmlContabilidadeLote
        periodo={periodo}
        onPeriodoChange={(valor) => {
          setPeriodo(valor);
          setErroDoPeriodo("");
        }}
        erroPeriodo={erroDoPeriodo}
        agendadoPara={agendadoPara}
        onAgendamentoChange={setAgendadoPara}
        operacao={operacao}
        bloqueioEnvio={bloqueioEnvio}
        onBaixar={baixar}
        onEnviar={() => enviar()}
        onAgendar={() => enviar(true)}
      />
      <XmlContabilidadeHistorico
        envios={envios}
        atualizando={atualizando}
        erro={erroHistorico}
        onAtualizar={atualizarHistorico}
        onAcao={acaoEnvio}
        operacao={operacao}
        bloqueioEnvio={bloqueioEnvio}
      />
    </div>
  );
}
