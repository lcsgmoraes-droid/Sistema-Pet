import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Calendar, Plus, ChevronLeft, ChevronRight, AlertCircle, Clock, Activity } from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";

const STATUS_COLOR = {
  aguardando: "border-l-yellow-400 bg-yellow-50",
  em_atendimento: "border-l-blue-400 bg-blue-50",
  finalizado: "border-l-green-400 bg-green-50",
  cancelado: "border-l-gray-300 bg-gray-50",
};

const STATUS_BADGE = {
  aguardando: "bg-yellow-100 text-yellow-800",
  em_atendimento: "bg-blue-100 text-blue-800",
  finalizado: "bg-green-100 text-green-700",
  cancelado: "bg-gray-100 text-gray-500",
};

const STATUS_LABEL = {
  aguardando: "Aguardando",
  em_atendimento: "Em atendimento",
  finalizado: "Finalizado",
  cancelado: "Cancelado",
};

function isoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDias(d, n) {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function inicioMes(d) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function fimMes(d) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

function inicioDaGradeMensal(d) {
  const primeiro = inicioMes(d);
  return addDias(primeiro, -primeiro.getDay());
}

export default function VetAgenda() {
  const navigate = useNavigate();
  const [dataRef, setDataRef] = useState(new Date());
  const [modo, setModo] = useState("dia"); // "dia" | "semana" | "mes"
  const [agendamentos, setAgendamentos] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [novoAberto, setNovoAberto] = useState(false);
  const [pets, setPets] = useState([]);
  const [formNovo, setFormNovo] = useState({ pet_id: "", data_hora: "", motivo: "", emergencia: false });
  const [salvandoNovo, setSalvandoNovo] = useState(false);

  const inicioSemana = (modo === "semana" || modo === "mes")
    ? addDias(dataRef, -dataRef.getDay())
    : dataRef;
  const fimSemana = (modo === "semana" || modo === "mes")
    ? addDias(inicioSemana, 6)
    : dataRef;

  const dataInicioConsulta = modo === "mes" ? inicioMes(dataRef) : inicioSemana;
  const dataFimConsulta = modo === "mes" ? fimMes(dataRef) : fimSemana;

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      setErro(null);
      const res = await vetApi.listarAgendamentos({
        data_inicio: isoDate(dataInicioConsulta),
        data_fim: isoDate(dataFimConsulta),
      });
      const data = res.data;
      setAgendamentos(Array.isArray(data) ? data : (data.items ?? []));
    } catch {
      setErro("Erro ao carregar agenda.");
    } finally {
      setCarregando(false);
    }
  }, [dataInicioConsulta, dataFimConsulta]);

  useEffect(() => { carregar(); }, [carregar]);

  useEffect(() => {
    api.get("/vet/pets", { params: { limit: 500 } })
      .then((r) => setPets(r.data?.items ?? r.data ?? []))
      .catch(() => {});
  }, []);

  function nav(direcao) {
    if (modo === "mes") {
      setDataRef((d) => new Date(d.getFullYear(), d.getMonth() + direcao, 1));
      return;
    }
    const delta = modo === "dia" ? 1 : 7;
    setDataRef((d) => addDias(d, direcao * delta));
  }

  function formatTitulo() {
    if (modo === "dia") {
      return dataRef.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });
    }
    if (modo === "mes") {
      return dataRef.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
    }
    return `${inicioSemana.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })} – ${fimSemana.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })}`;
  }

  // Filtra agendamentos para um dia específico
  function agsDia(data) {
    const key = isoDate(data);
    return agendamentos.filter((a) => (a.data_hora ?? "").startsWith(key))
      .sort((a, b) => (a.data_hora ?? "").localeCompare(b.data_hora ?? ""));
  }

  async function criarAgendamento() {
    if (!formNovo.pet_id || !formNovo.data_hora) return;
    setSalvandoNovo(true);
    try {
      await vetApi.criarAgendamento({
        pet_id: formNovo.pet_id,
        data_hora: formNovo.data_hora,
        motivo: formNovo.motivo || undefined,
        emergencia: formNovo.emergencia,
      });
      setNovoAberto(false);
      setFormNovo({ pet_id: "", data_hora: "", motivo: "", emergencia: false });
      await carregar();
    } catch {
      setErro("Erro ao criar agendamento.");
    } finally {
      setSalvandoNovo(false);
    }
  }

  const diasVisiveis = modo === "semana"
    ? Array.from({ length: 7 }, (_, i) => addDias(inicioSemana, i))
    : [dataRef];

  const diasMes = modo === "mes"
    ? Array.from({ length: 42 }, (_, i) => addDias(inicioDaGradeMensal(dataRef), i))
    : [];

  return (
    <div className="p-6 space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-xl">
            <Calendar size={22} className="text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Agenda</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex border border-gray-200 rounded-lg overflow-hidden text-sm">
            <button onClick={() => setModo("dia")} className={`px-3 py-1.5 ${modo === "dia" ? "bg-blue-600 text-white" : "hover:bg-gray-50"}`}>Dia</button>
            <button onClick={() => setModo("semana")} className={`px-3 py-1.5 ${modo === "semana" ? "bg-blue-600 text-white" : "hover:bg-gray-50"}`}>Semana</button>
            <button onClick={() => setModo("mes")} className={`px-3 py-1.5 ${modo === "mes" ? "bg-blue-600 text-white" : "hover:bg-gray-50"}`}>Mês</button>
          </div>
          <button
            onClick={() => setNovoAberto(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={15} />
            Agendar
          </button>
        </div>
      </div>

      {/* Navigação de data */}
      <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3">
        <button onClick={() => nav(-1)} className="p-1 hover:bg-gray-100 rounded-full">
          <ChevronLeft size={18} className="text-gray-600" />
        </button>
        <button
          onClick={() => setDataRef(new Date())}
          className="flex-1 text-center text-sm font-medium text-gray-700 capitalize"
        >
          {formatTitulo()}
        </button>
        <button onClick={() => nav(1)} className="p-1 hover:bg-gray-100 rounded-full">
          <ChevronRight size={18} className="text-gray-600" />
        </button>
      </div>

      {/* Erro */}
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      {/* Grade */}
      {carregando ? (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      ) : modo === "mes" ? (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="grid grid-cols-7 bg-gray-50 border-b border-gray-200">
            {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].map((nomeDia) => (
              <div key={nomeDia} className="px-3 py-2 text-xs font-semibold text-gray-600 text-center">{nomeDia}</div>
            ))}
          </div>

          <div className="grid grid-cols-7">
            {diasMes.map((dia) => {
              const ags = agsDia(dia);
              const ehHoje = isoDate(dia) === isoDate(new Date());
              const foraDoMes = dia.getMonth() !== dataRef.getMonth();
              return (
                <div
                  key={isoDate(dia)}
                  className={`min-h-[110px] border-b border-r border-gray-100 p-2 ${foraDoMes ? "bg-gray-50" : "bg-white"}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-xs font-medium ${ehHoje ? "text-blue-700" : foraDoMes ? "text-gray-400" : "text-gray-700"}`}>
                      {String(dia.getDate()).padStart(2, "0")}
                    </span>
                    {ags.length > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">{ags.length}</span>
                    )}
                  </div>

                  <div className="space-y-1">
                    {ags.slice(0, 2).map((ag) => (
                      <button
                        key={ag.id}
                        type="button"
                        onClick={() => {
                          if (ag.consulta_id) navigate(`/veterinario/consultas/${ag.consulta_id}`);
                        }}
                        className={`w-full text-left text-[11px] px-1.5 py-1 rounded border-l-2 ${STATUS_COLOR[ag.status] ?? "border-l-gray-200 bg-white"}`}
                      >
                        <p className="truncate">{ag.data_hora?.slice(11, 16)} • {ag.pet_nome ?? `Pet #${String(ag.pet_id ?? "").slice(0, 6)}`}</p>
                      </button>
                    ))}
                    {ags.length > 2 && <p className="text-[10px] text-gray-400">+{ags.length - 2} mais</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className={`grid gap-4 ${modo === "semana" ? "grid-cols-7" : "grid-cols-1"}`}>
          {diasVisiveis.map((dia) => {
            const ags = agsDia(dia);
            const ehHoje = isoDate(dia) === isoDate(new Date());
            return (
              <div key={isoDate(dia)} className={`bg-white border rounded-xl overflow-hidden ${ehHoje ? "border-blue-300" : "border-gray-200"}`}>
                {/* Título do dia */}
                <div className={`px-3 py-2 text-xs font-semibold border-b ${ehHoje ? "bg-blue-600 text-white" : "bg-gray-50 text-gray-600"}`}>
                  <span className="capitalize">{dia.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit" })}</span>
                  {ags.length > 0 && (
                    <span className={`ml-1 px-1.5 py-0.5 rounded-full text-xs ${ehHoje ? "bg-white text-blue-700" : "bg-blue-100 text-blue-700"}`}>
                      {ags.length}
                    </span>
                  )}
                </div>
                {/* Agendamentos */}
                <div className="divide-y divide-gray-50 min-h-[80px]">
                  {ags.length === 0 && (
                    <p className="text-xs text-gray-300 text-center py-4">livre</p>
                  )}
                  {ags.map((ag) => (
                    <div
                      key={ag.id}
                      onClick={() => {
                        if (ag.consulta_id) navigate(`/veterinario/consultas/${ag.consulta_id}`);
                      }}
                      className={`px-3 py-2 border-l-4 cursor-pointer hover:opacity-80 transition-opacity ${STATUS_COLOR[ag.status] ?? "border-l-gray-200 bg-white"}`}
                    >
                      <div className="flex items-center gap-1 mb-0.5">
                        <Clock size={10} className="text-gray-400" />
                        <span className="text-xs text-gray-500">{ag.data_hora?.slice(11, 16)}</span>
                        {ag.emergencia && <Activity size={10} className="text-red-500 ml-auto" />}
                      </div>
                      <p className="text-xs font-medium text-gray-700 truncate">
                        {ag.pet_nome ?? `Pet #${String(ag.pet_id ?? "").slice(0, 6)}`}
                      </p>
                      <p className="text-xs text-gray-400 truncate">{ag.motivo ?? "—"}</p>
                      <span className={`mt-1 inline-flex text-xs px-1.5 py-0.5 rounded-full font-medium ${STATUS_BADGE[ag.status] ?? "bg-gray-100"}`}>
                        {STATUS_LABEL[ag.status] ?? ag.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal novo agendamento */}
      {novoAberto && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-bold text-gray-800">Novo agendamento</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Pet*</label>
                <select
                  value={formNovo.pet_id}
                  onChange={(e) => setFormNovo((p) => ({ ...p, pet_id: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                >
                  <option value="">Selecione o pet…</option>
                  {pets.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Data e hora*</label>
                <input
                  type="datetime-local"
                  value={formNovo.data_hora}
                  onChange={(e) => setFormNovo((p) => ({ ...p, data_hora: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Motivo</label>
                <input
                  type="text"
                  value={formNovo.motivo}
                  onChange={(e) => setFormNovo((p) => ({ ...p, motivo: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="Ex: Consulta de rotina, pós-cirúrgico…"
                />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formNovo.emergencia}
                  onChange={(e) => setFormNovo((p) => ({ ...p, emergencia: e.target.checked }))}
                  className="rounded"
                />
                <span className="text-sm text-gray-700">Emergência</span>
              </label>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setNovoAberto(false)}
                className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={criarAgendamento}
                disabled={salvandoNovo || !formNovo.pet_id || !formNovo.data_hora}
                className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
              >
                {salvandoNovo ? "Salvando…" : "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
