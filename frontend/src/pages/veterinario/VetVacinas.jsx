import { useState, useEffect, useCallback } from "react";
import { Syringe, Plus, AlertCircle, CheckCircle, Search, ChevronDown } from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";

function formatData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function diasRestantes(iso) {
  if (!iso) return null;
  const diff = Math.ceil((new Date(iso) - new Date()) / 86400000);
  return diff;
}

function badgeProxDose(iso) {
  if (!iso) return null;
  const dias = diasRestantes(iso);
  if (dias < 0) return { label: `Vencida há ${Math.abs(dias)}d`, cls: "bg-red-100 text-red-700" };
  if (dias <= 7) return { label: `${dias === 0 ? "Hoje" : `em ${dias}d`}`, cls: "bg-red-100 text-red-700" };
  if (dias <= 30) return { label: `em ${dias}d`, cls: "bg-yellow-100 text-yellow-700" };
  return { label: `em ${dias}d`, cls: "bg-green-100 text-green-700" };
}

export default function VetVacinas() {
  const [aba, setAba] = useState("registros"); // "registros" | "vencendo"
  const [petSelecionado, setPetSelecionado] = useState("");
  const [pets, setPets] = useState([]);
  const [vacinas, setVacinas] = useState([]);
  const [vacinasVencendo, setVacinasVencendo] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [novaAberta, setNovaAberta] = useState(false);
  const [form, setForm] = useState({
    pet_id: "",
    nome_vacina: "",
    fabricante: "",
    lote: "",
    data_aplicacao: "",
    proxima_dose: "",
    veterinario_responsavel: "",
    observacoes: "",
  });
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    api.get("/pets", { params: { limit: 500 } })
      .then((r) => setPets(r.data?.items ?? r.data ?? []))
      .catch(() => {});
    carregarVencendo();
  }, []);

  async function carregarVencendo() {
    try {
      const res = await vetApi.vacinasVencendo(30);
      setVacinasVencendo(Array.isArray(res.data) ? res.data : (res.data?.items ?? []));
    } catch {}
  }

  const carregarVacinasPet = useCallback(async () => {
    if (!petSelecionado) { setVacinas([]); return; }
    try {
      setCarregando(true);
      const res = await vetApi.listarVacinasPet(petSelecionado);
      setVacinas(Array.isArray(res.data) ? res.data : (res.data?.items ?? []));
    } catch {
      setErro("Erro ao carregar vacinas.");
    } finally {
      setCarregando(false);
    }
  }, [petSelecionado]);

  useEffect(() => { carregarVacinasPet(); }, [carregarVacinasPet]);

  function set(campo, valor) { setForm((p) => ({ ...p, [campo]: valor })); }

  async function salvarVacina() {
    if (!form.pet_id || !form.nome_vacina || !form.data_aplicacao) return;
    setSalvando(true);
    setErro(null);
    try {
      await vetApi.registrarVacina({
        pet_id: form.pet_id,
        nome_vacina: form.nome_vacina,
        fabricante: form.fabricante || undefined,
        lote: form.lote || undefined,
        data_aplicacao: form.data_aplicacao,
        proxima_dose: form.proxima_dose || undefined,
        veterinario_responsavel: form.veterinario_responsavel || undefined,
        observacoes: form.observacoes || undefined,
      });
      setNovaAberta(false);
      setForm({ pet_id: "", nome_vacina: "", fabricante: "", lote: "", data_aplicacao: "", proxima_dose: "", veterinario_responsavel: "", observacoes: "" });
      // Recarrega a lista se for o mesmo pet
      if (form.pet_id === petSelecionado) await carregarVacinasPet();
      await carregarVencendo();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar vacina.");
    } finally {
      setSalvando(false);
    }
  }

  const petNome = (id) => pets.find((p) => p.id === id)?.nome ?? id;

  return (
    <div className="p-6 space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-xl">
            <Syringe size={22} className="text-orange-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Vacinas</h1>
        </div>
        <button
          onClick={() => setNovaAberta(true)}
          className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={15} />
          Registrar vacina
        </button>
      </div>

      {/* Abas */}
      <div className="flex border-b border-gray-200">
        {[
          { id: "registros", label: "Por pet" },
          { id: "vencendo", label: `A vencer (${vacinasVencendo.length})` },
        ].map((a) => (
          <button
            key={a.id}
            onClick={() => setAba(a.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${aba === a.id ? "border-orange-500 text-orange-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
          >
            {a.label}
          </button>
        ))}
      </div>

      {/* Erro */}
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      {/* ABA: Registros por pet */}
      {aba === "registros" && (
        <div className="space-y-4">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <select
              value={petSelecionado}
              onChange={(e) => setPetSelecionado(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-orange-300"
            >
              <option value="">Selecione um pet para ver a carteira…</option>
              {pets.map((p) => <option key={p.id} value={p.id}>{p.nome} ({p.especie ?? "pet"})</option>)}
            </select>
          </div>

          {!petSelecionado && (
            <div className="p-10 text-center bg-white border border-gray-200 rounded-xl">
              <Syringe size={36} className="mx-auto text-gray-200 mb-3" />
              <p className="text-gray-400 text-sm">Selecione um pet para ver sua carteira de vacinação.</p>
            </div>
          )}

          {petSelecionado && carregando && (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-orange-400" />
            </div>
          )}

          {petSelecionado && !carregando && (
            <>
              {vacinas.length === 0 ? (
                <div className="p-8 text-center bg-white border border-gray-200 rounded-xl">
                  <p className="text-gray-400 text-sm">Nenhuma vacina registrada para este pet.</p>
                  <button
                    onClick={() => { setForm((prev) => ({ ...prev, pet_id: petSelecionado })); setNovaAberta(true); }}
                    className="mt-3 text-sm text-orange-500 underline"
                  >
                    Registrar primeira vacina →
                  </button>
                </div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-100">
                      <tr>
                        <th className="text-left px-4 py-3 font-medium text-gray-600">Vacina</th>
                        <th className="text-left px-4 py-3 font-medium text-gray-600">Aplicação</th>
                        <th className="text-left px-4 py-3 font-medium text-gray-600">Próxima dose</th>
                        <th className="text-left px-4 py-3 font-medium text-gray-600">Lote</th>
                        <th className="text-left px-4 py-3 font-medium text-gray-600">Veterinário</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {vacinas.map((v) => {
                        const badge = badgeProxDose(v.proxima_dose);
                        return (
                          <tr key={v.id} className="hover:bg-orange-50 transition-colors">
                            <td className="px-4 py-3 font-medium text-gray-800">{v.nome_vacina}</td>
                            <td className="px-4 py-3 text-gray-600">{formatData(v.data_aplicacao)}</td>
                            <td className="px-4 py-3">
                              {v.proxima_dose ? (
                                <div className="flex items-center gap-2">
                                  <span className="text-gray-600">{formatData(v.proxima_dose)}</span>
                                  {badge && (
                                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
                                      {badge.label}
                                    </span>
                                  )}
                                </div>
                              ) : "—"}
                            </td>
                            <td className="px-4 py-3 text-gray-500">{v.lote ?? "—"}</td>
                            <td className="px-4 py-3 text-gray-500">{v.veterinario_responsavel ?? "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ABA: Vacinas a vencer */}
      {aba === "vencendo" && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          {vacinasVencendo.length === 0 ? (
            <div className="p-10 text-center">
              <CheckCircle size={36} className="mx-auto text-green-300 mb-3" />
              <p className="text-gray-400 text-sm">Nenhuma vacina a vencer nos próximos 30 dias. Ótimo!</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Pet</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Vacina</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Próxima dose</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {vacinasVencendo.map((v) => {
                  const badge = badgeProxDose(v.proxima_dose);
                  return (
                    <tr key={v.id} className="hover:bg-orange-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-800">{v.pet_nome ?? "—"}</td>
                      <td className="px-4 py-3 text-gray-700">{v.nome_vacina}</td>
                      <td className="px-4 py-3 text-gray-600">{formatData(v.proxima_dose)}</td>
                      <td className="px-4 py-3">
                        {badge && (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
                            {badge.label}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modal nova vacina */}
      {novaAberta && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h2 className="font-bold text-gray-800">Registrar vacina</h2>
            <div className="grid grid-cols-2 gap-3">
              {/* Pet */}
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Pet *</label>
                <select
                  value={form.pet_id}
                  onChange={(e) => set("pet_id", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                >
                  <option value="">Selecione…</option>
                  {pets.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
                </select>
              </div>
              {/* Vacina */}
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Nome da vacina *</label>
                <input type="text" value={form.nome_vacina} onChange={(e) => set("nome_vacina", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="Ex: V10, Antirrábica, Gripe felina…" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Fabricante</label>
                <input type="text" value={form.fabricante} onChange={(e) => set("fabricante", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Lote</label>
                <input type="text" value={form.lote} onChange={(e) => set("lote", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Data de aplicação *</label>
                <input type="date" value={form.data_aplicacao} onChange={(e) => set("data_aplicacao", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Próxima dose</label>
                <input type="date" value={form.proxima_dose} onChange={(e) => set("proxima_dose", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Veterinário responsável</label>
                <input type="text" value={form.veterinario_responsavel} onChange={(e) => set("veterinario_responsavel", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Observações</label>
                <textarea value={form.observacoes} onChange={(e) => set("observacoes", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-16" />
              </div>
            </div>
            {erro && <p className="text-xs text-red-600">{erro}</p>}
            <div className="flex gap-3 pt-1">
              <button onClick={() => setNovaAberta(false)}
                className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancelar</button>
              <button
                onClick={salvarVacina}
                disabled={salvando || !form.pet_id || !form.nome_vacina || !form.data_aplicacao}
                className="flex-1 px-4 py-2 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-60"
              >
                {salvando ? "Salvando…" : "Registrar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
