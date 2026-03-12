import { useState, useEffect, useCallback } from "react";
import { BedDouble, Plus, Activity, ArrowUpCircle, AlertCircle, Clock } from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";

function formatData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}
function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

const STATUS_CORES = {
  ativa: "bg-blue-100 text-blue-700",
  alta: "bg-green-100 text-green-700",
  transferida: "bg-yellow-100 text-yellow-700",
  obito: "bg-red-100 text-red-700",
};

export default function VetInternacoes() {
  const [aba, setAba] = useState("ativas"); // "ativas" | "historico"
  const [internacoes, setInternacoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [expandida, setExpandida] = useState(null); // id da internação aberta
  const [evolucoes, setEvolucoes] = useState({}); // { [internacaoId]: [...] }
  const [modalNova, setModalNova] = useState(false);
  const [modalAlta, setModalAlta] = useState(null); // id
  const [modalEvolucao, setModalEvolucao] = useState(null); // id
  const [pets, setPets] = useState([]);
  const [formNova, setFormNova] = useState({ pet_id: "", motivo: "", box: "", responsavel: "" });
  const [formAlta, setFormAlta] = useState("");
  const [formEvolucao, setFormEvolucao] = useState({ temperatura: "", fc: "", fr: "", observacoes: "" });
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    api.get("/pets", { params: { limit: 500 } }).then((r) => setPets(r.data?.items ?? r.data ?? [])).catch(() => {});
  }, []);

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      const status = aba === "ativas" ? "ativa" : undefined;
      const res = await vetApi.listarInternacoes(status);
      setInternacoes(Array.isArray(res.data) ? res.data : (res.data?.items ?? []));
    } catch {
      setErro("Erro ao carregar internações.");
    } finally {
      setCarregando(false);
    }
  }, [aba]);

  useEffect(() => { carregar(); }, [carregar]);

  async function abrirDetalhe(id) {
    setExpandida(expandida === id ? null : id);
    if (expandida !== id && !evolucoes[id]) {
      try {
        // Usa a listagem de evolucoes via endpoint de internação (rota /vet/internacoes/{id} retorna evoluções)
        const res = await vetApi.listarInternacoes();
        const intern = (Array.isArray(res.data) ? res.data : res.data?.items ?? []).find((i) => i.id === id);
        setEvolucoes((prev) => ({ ...prev, [id]: intern?.evolucoes ?? [] }));
      } catch {}
    }
  }

  async function criarInternacao() {
    if (!formNova.pet_id || !formNova.motivo) return;
    setSalvando(true);
    try {
      await vetApi.criarInternacao({
        pet_id: formNova.pet_id,
        motivo_internacao: formNova.motivo,
        box: formNova.box || undefined,
        veterinario_responsavel_id: undefined,
      });
      setModalNova(false);
      setFormNova({ pet_id: "", motivo: "", box: "", responsavel: "" });
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao criar internação.");
    } finally {
      setSalvando(false);
    }
  }

  async function darAlta() {
    if (!modalAlta) return;
    setSalvando(true);
    try {
      await vetApi.darAlta(modalAlta, formAlta || undefined);
      setModalAlta(null);
      setFormAlta("");
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao dar alta.");
    } finally {
      setSalvando(false);
    }
  }

  async function registrarEvolucao() {
    if (!modalEvolucao) return;
    setSalvando(true);
    try {
      await vetApi.registrarEvolucao(modalEvolucao, {
        temperatura: formEvolucao.temperatura ? parseFloat(formEvolucao.temperatura) : undefined,
        freq_cardiaca: formEvolucao.fc ? parseInt(formEvolucao.fc) : undefined,
        freq_respiratoria: formEvolucao.fr ? parseInt(formEvolucao.fr) : undefined,
        observacoes: formEvolucao.observacoes || undefined,
      });
      setModalEvolucao(null);
      setFormEvolucao({ temperatura: "", fc: "", fr: "", observacoes: "" });
      setEvolucoes((prev) => ({ ...prev, [modalEvolucao]: undefined })); // limpa cache
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar evolução.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="p-6 space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-xl">
            <BedDouble size={22} className="text-purple-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Internações</h1>
        </div>
        <button
          onClick={() => setModalNova(true)}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={15} />
          Nova internação
        </button>
      </div>

      {/* Abas */}
      <div className="flex border-b border-gray-200">
        {[{ id: "ativas", label: "Ativas" }, { id: "historico", label: "Histórico" }].map((a) => (
          <button key={a.id} onClick={() => setAba(a.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${aba === a.id ? "border-purple-500 text-purple-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {a.label}
          </button>
        ))}
      </div>

      {/* Erro */}
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
          <button className="ml-auto" onClick={() => setErro(null)}>✕</button>
        </div>
      )}

      {/* Lista */}
      {carregando ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
        </div>
      ) : internacoes.length === 0 ? (
        <div className="p-10 text-center bg-white border border-gray-200 rounded-xl">
          <BedDouble size={36} className="mx-auto text-gray-200 mb-3" />
          <p className="text-gray-400 text-sm">Nenhuma internação {aba === "ativas" ? "ativa" : "registrada"}.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {internacoes.map((intern) => {
            const aberta = expandida === intern.id;
            return (
              <div key={intern.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                {/* Linha principal */}
                <div
                  className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => abrirDetalhe(intern.id)}
                >
                  <BedDouble size={18} className="text-purple-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-800">{intern.pet_nome ?? `Pet #${(intern.pet_id ?? "").slice(0, 6)}`}</p>
                    <p className="text-xs text-gray-400 truncate">{intern.motivo_internacao}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-gray-400">Entrada: {formatData(intern.data_entrada)}</p>
                    {intern.box && <p className="text-xs text-gray-500">Box: {intern.box}</p>}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CORES[intern.status] ?? "bg-gray-100"}`}>
                    {intern.status}
                  </span>
                  {intern.status === "ativa" && (
                    <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => setModalEvolucao(intern.id)}
                        className="flex items-center gap-1 text-xs px-2 py-1 border border-blue-200 text-blue-600 rounded-lg hover:bg-blue-50"
                      >
                        <Activity size={12} />
                        Evolução
                      </button>
                      <button
                        onClick={() => setModalAlta(intern.id)}
                        className="flex items-center gap-1 text-xs px-2 py-1 border border-green-200 text-green-600 rounded-lg hover:bg-green-50"
                      >
                        <ArrowUpCircle size={12} />
                        Alta
                      </button>
                    </div>
                  )}
                </div>

                {/* Evoluções (expansível) */}
                {aberta && (
                  <div className="border-t border-gray-100 bg-gray-50 px-5 py-4">
                    <p className="text-xs font-semibold text-gray-500 mb-3">Evoluções</p>
                    {(evolucoes[intern.id] ?? []).length === 0 ? (
                      <p className="text-xs text-gray-400">Nenhuma evolução registrada ainda.</p>
                    ) : (
                      <div className="space-y-2">
                        {(evolucoes[intern.id] ?? []).map((ev, i) => (
                          <div key={i} className="bg-white border border-gray-100 rounded-lg px-3 py-2 text-xs">
                            <div className="flex items-center gap-2 text-gray-400 mb-1">
                              <Clock size={10} />
                              <span>{formatDateTime(ev.data_hora)}</span>
                            </div>
                            <div className="flex gap-4 text-gray-600">
                              {ev.temperatura && <span>Temp: {ev.temperatura}°C</span>}
                              {ev.freq_cardiaca && <span>FC: {ev.freq_cardiaca} bpm</span>}
                              {ev.freq_respiratoria && <span>FR: {ev.freq_respiratoria} rpm</span>}
                            </div>
                            {ev.observacoes && <p className="text-gray-500 mt-1">{ev.observacoes}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modal nova internação */}
      {modalNova && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-bold text-gray-800">Nova internação</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Pet *</label>
                <select value={formNova.pet_id} onChange={(e) => setFormNova((p) => ({ ...p, pet_id: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white">
                  <option value="">Selecione…</option>
                  {pets.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Motivo da internação *</label>
                <textarea value={formNova.motivo} onChange={(e) => setFormNova((p) => ({ ...p, motivo: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Box / Baia</label>
                <input type="text" value={formNova.box} onChange={(e) => setFormNova((p) => ({ ...p, box: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Ex: Box 3" />
              </div>
            </div>
            <div className="flex gap-3 pt-1">
              <button onClick={() => setModalNova(false)} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancelar</button>
              <button onClick={criarInternacao} disabled={salvando || !formNova.pet_id || !formNova.motivo}
                className="flex-1 px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-60">
                {salvando ? "Salvando…" : "Internar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal dar alta */}
      {modalAlta && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-bold text-gray-800">Dar alta</h2>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Observações de alta</label>
              <textarea value={formAlta} onChange={(e) => setFormAlta(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-28"
                placeholder="Instruções para o tutor, condição na saída…" />
            </div>
            <div className="flex gap-3 pt-1">
              <button onClick={() => setModalAlta(null)} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancelar</button>
              <button onClick={darAlta} disabled={salvando}
                className="flex-1 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60">
                {salvando ? "Processando…" : "Confirmar alta"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal evolução */}
      {modalEvolucao && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-bold text-gray-800">Registrar evolução</h2>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Temp. (°C)</label>
                <input type="number" step="0.1" value={formEvolucao.temperatura} onChange={(e) => setFormEvolucao((p) => ({ ...p, temperatura: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">FC (bpm)</label>
                <input type="number" value={formEvolucao.fc} onChange={(e) => setFormEvolucao((p) => ({ ...p, fc: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">FR (rpm)</label>
                <input type="number" value={formEvolucao.fr} onChange={(e) => setFormEvolucao((p) => ({ ...p, fr: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Observações</label>
              <textarea value={formEvolucao.observacoes} onChange={(e) => setFormEvolucao((p) => ({ ...p, observacoes: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20" />
            </div>
            <div className="flex gap-3 pt-1">
              <button onClick={() => setModalEvolucao(null)} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancelar</button>
              <button onClick={registrarEvolucao} disabled={salvando}
                className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60">
                {salvando ? "Salvando…" : "Registrar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
