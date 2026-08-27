import { Activity, Clock3, Radio, RefreshCw, WifiOff } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";

import api from "../../api";
import RastreamentoLista from "./RastreamentoLista";
import RastreamentoMapa from "./RastreamentoMapa";
import RastreamentoSimulador from "./RastreamentoSimulador";
import "./RastreamentoAoVivo.css";
import { filtrarRotasEmAndamento } from "./rotasEntregaUtils";
import {
  adicionarPontoTrilha,
  coordenadasDaRota,
  gerarPontosSimulacao,
  obterEstadoSinal,
  simuladorRastreioHabilitado,
} from "./rastreamentoAoVivoUtils";

const INTERVALO_ATUALIZACAO_MS = 4_000;
const INTERVALO_SIMULACAO_MS = 1_800;

function aguardar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function obterLocalizacaoNavegador() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Este navegador não oferece acesso à localização."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: coords.latitude, longitude: coords.longitude }),
      () => reject(new Error("Permita a localização do navegador para iniciar a simulação.")),
      { enableHighAccuracy: true, timeout: 12_000, maximumAge: 60_000 },
    );
  });
}

export default function RastreamentoAoVivo() {
  const [rotas, setRotas] = useState([]);
  const [trilhas, setTrilhas] = useState({});
  const [rotaSelecionadaId, setRotaSelecionadaId] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [ultimaConsulta, setUltimaConsulta] = useState(null);
  const [simulacao, setSimulacao] = useState({ ativa: false, progresso: 0, erro: "" });
  const consultaEmAndamentoRef = useRef(false);
  const cancelarSimulacaoRef = useRef(false);
  const montadoRef = useRef(true);

  const carregarRotas = useCallback(async ({ silencioso = false } = {}) => {
    if (consultaEmAndamentoRef.current) return;
    consultaEmAndamentoRef.current = true;
    try {
      const response = await api.get("/rotas-entrega/");
      const emAndamento = filtrarRotasEmAndamento(response.data);
      if (!montadoRef.current) return;
      setRotas(emAndamento);
      setErro("");
      setUltimaConsulta(new Date());
      setRotaSelecionadaId((atual) => {
        if (emAndamento.some((rota) => String(rota.id) === String(atual))) return atual;
        return emAndamento[0]?.id ?? null;
      });
      setTrilhas((anteriores) => {
        const proximas = {};
        emAndamento.forEach((rota) => {
          const id = String(rota.id);
          proximas[id] = adicionarPontoTrilha(anteriores[id] || [], coordenadasDaRota(rota));
        });
        return proximas;
      });
    } catch (requestError) {
      if (!montadoRef.current) return;
      setErro(requestError?.response?.data?.detail || "Não foi possível atualizar o rastreamento.");
    } finally {
      consultaEmAndamentoRef.current = false;
      if (!silencioso && montadoRef.current) setCarregando(false);
    }
  }, []);

  useEffect(() => {
    montadoRef.current = true;
    void carregarRotas();
    const interval = setInterval(
      () => void carregarRotas({ silencioso: true }),
      INTERVALO_ATUALIZACAO_MS,
    );
    return () => {
      montadoRef.current = false;
      cancelarSimulacaoRef.current = true;
      clearInterval(interval);
    };
  }, [carregarRotas]);

  const resumo = useMemo(() => {
    const estados = rotas.map((rota) => obterEstadoSinal(rota).key);
    return {
      total: rotas.length,
      aoVivo: estados.filter((estado) => estado === "ao_vivo").length,
      atrasado: estados.filter((estado) => estado === "atrasado").length,
      offline: estados.filter((estado) => ["offline", "sem_sinal"].includes(estado)).length,
    };
  }, [rotas, ultimaConsulta]);

  const rotasOrdenadas = useMemo(() => {
    const prioridade = { ao_vivo: 0, atrasado: 1, offline: 2, sem_sinal: 3 };
    return [...rotas].sort(
      (a, b) => prioridade[obterEstadoSinal(a).key] - prioridade[obterEstadoSinal(b).key],
    );
  }, [rotas, ultimaConsulta]);

  const selecionarRota = useCallback((rotaId) => setRotaSelecionadaId(rotaId), []);

  async function iniciarSimulacao(rotaId) {
    if (!simuladorRastreioHabilitado(import.meta.env)) return;
    const rota = rotas.find((item) => String(item.id) === String(rotaId));
    if (!rota) return;

    cancelarSimulacaoRef.current = false;
    setRotaSelecionadaId(rota.id);
    setSimulacao({ ativa: true, progresso: 0, erro: "" });

    try {
      const origem = coordenadasDaRota(rota) || (await obterLocalizacaoNavegador());
      const pontos = gerarPontosSimulacao(origem);
      for (let index = 0; index < pontos.length; index += 1) {
        if (cancelarSimulacaoRef.current || !montadoRef.current) break;
        const ponto = pontos[index];
        await api.post(`/rotas-entrega/${rota.id}/atualizar-localizacao`, null, {
          params: { lat: ponto.latitude, lon: ponto.longitude },
        });
        if (!montadoRef.current) break;
        setSimulacao({ ativa: true, progresso: index + 1, erro: "" });
        await carregarRotas({ silencioso: true });
        if (index < pontos.length - 1) await aguardar(INTERVALO_SIMULACAO_MS);
      }

      if (!cancelarSimulacaoRef.current && montadoRef.current) {
        toast.success("Trajeto simulado concluído.");
      }
    } catch (simulationError) {
      if (montadoRef.current) {
        setSimulacao({
          ativa: false,
          progresso: 0,
          erro:
            simulationError?.response?.data?.detail ||
            simulationError?.message ||
            "Não foi possível executar a simulação.",
        });
      }
      return;
    }

    if (montadoRef.current) {
      setSimulacao((atual) => ({ ...atual, ativa: false }));
    }
  }

  function pararSimulacao() {
    cancelarSimulacaoRef.current = true;
    setSimulacao((atual) => ({ ...atual, ativa: false }));
    toast("Simulação interrompida.");
  }

  const simuladorAtivoNoAmbiente = simuladorRastreioHabilitado(import.meta.env);

  return (
    <div className="mx-auto max-w-[1600px] space-y-5 p-4 md:p-8">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-700">
            Entregas · Operação
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950">Rastreamento ao vivo</h1>
          <p className="mt-1 text-sm text-slate-600">
            Acompanhe as motos em movimento. A tela atualiza automaticamente a cada 4 segundos.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void carregarRotas()}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
        >
          <RefreshCw size={16} /> Atualizar agora
        </button>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ["Rotas na rua", resumo.total, Activity, "#0f172a"],
          ["Ao vivo", resumo.aoVivo, Radio, "#16a34a"],
          ["Sinal atrasado", resumo.atrasado, Clock3, "#d97706"],
          ["Sem sinal", resumo.offline, WifiOff, "#dc2626"],
        ].map(([label, value, Icone, cor]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-black text-slate-950">{value}</p>
              </div>
              <Icone size={23} style={{ color: cor }} />
            </div>
          </div>
        ))}
      </div>

      {simuladorAtivoNoAmbiente ? (
        <RastreamentoSimulador
          rotas={rotas}
          simulacao={simulacao}
          onIniciar={(rotaId) => void iniciarSimulacao(rotaId)}
          onParar={pararSimulacao}
        />
      ) : null}

      {erro ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {erro} O último estado conhecido continua visível.
        </div>
      ) : null}

      {carregando ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-slate-500">
          Carregando entregas em andamento...
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
          <aside className="max-h-[620px] overflow-y-auto pr-1">
            <RastreamentoLista
              rotas={rotasOrdenadas}
              rotaSelecionadaId={rotaSelecionadaId}
              onSelecionar={selecionarRota}
            />
          </aside>
          <RastreamentoMapa
            rotas={rotas}
            trilhas={trilhas}
            rotaSelecionadaId={rotaSelecionadaId}
            onSelecionar={selecionarRota}
          />
        </div>
      )}

      <p className="text-center text-xs text-slate-400">
        Última consulta: {ultimaConsulta ? ultimaConsulta.toLocaleTimeString("pt-BR") : "—"}. A
        trilha exibida pertence a esta sessão; o servidor preserva a posição atual da rota.
      </p>
    </div>
  );
}
