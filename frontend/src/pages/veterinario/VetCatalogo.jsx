import { useState, useEffect, useCallback } from "react";
import { BookOpen, Plus, Search, AlertCircle, Pill, Syringe, ClipboardList } from "lucide-react";
import { vetApi } from "./vetApi";

// ---------- Helpers ----------
function Modal({ titulo, onClose, onSave, salvando, children }) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <h2 className="font-bold text-gray-800">{titulo}</h2>
        {children}
        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancelar</button>
          <button onClick={onSave} disabled={salvando}
            className="flex-1 px-4 py-2 text-sm bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-60">
            {salvando ? "Salvando…" : "Salvar"}
          </button>
        </div>
      </div>
    </div>
  );
}

const ABAS = [
  { id: "medicamentos", label: "Medicamentos", icon: Pill },
  { id: "procedimentos", label: "Procedimentos", icon: ClipboardList },
  { id: "vacinas", label: "Protocolos de vacinas", icon: Syringe },
];

// =========================================================
// ABA: MEDICAMENTOS
// =========================================================
function CatMedicamentos() {
  const [lista, setLista] = useState([]);
  const [busca, setBusca] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({
    nome: "", principio_ativo: "", especie: "",
    dose_min: "", dose_max: "", unidade_dose: "mg/kg",
    via_administracao: "oral", contraindicacoes: "", interacoes: "",
  });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);

  const buscar = useCallback(async () => {
    setBuscando(true);
    try {
      const res = await vetApi.listarMedicamentos(busca || undefined);
      setLista(Array.isArray(res.data) ? res.data : (res.data?.items ?? []));
    } catch { setErro("Erro ao buscar medicamentos."); }
    finally { setBuscando(false); }
  }, [busca]);

  useEffect(() => { buscar(); }, [buscar]);

  function set(c, v) { setForm((p) => ({ ...p, [c]: v })); }

  async function salvar() {
    if (!form.nome) return;
    setSalvando(true);
    try {
      await vetApi.criarMedicamento({
        nome: form.nome,
        principio_ativo: form.principio_ativo || undefined,
        especie_alvo: form.especie || undefined,
        dose_minima_mg_kg: form.dose_min ? parseFloat(form.dose_min) : undefined,
        dose_maxima_mg_kg: form.dose_max ? parseFloat(form.dose_max) : undefined,
        unidade_dose: form.unidade_dose || undefined,
        via_administracao: form.via_administracao || undefined,
        contraindicacoes: form.contraindicacoes || undefined,
        interacoes_medicamentosas: form.interacoes || undefined,
      });
      setModal(false);
      setForm({ nome: "", principio_ativo: "", especie: "", dose_min: "", dose_max: "", unidade_dose: "mg/kg", via_administracao: "oral", contraindicacoes: "", interacoes: "" });
      await buscar();
    } catch (e) { setErro(e?.response?.data?.detail ?? "Erro ao salvar."); }
    finally { setSalvando(false); }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" value={busca} onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome ou princípio ativo…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-300" />
        </div>
        <button onClick={() => setModal(true)}
          className="flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          <Plus size={14} /> Adicionar
        </button>
      </div>

      {erro && <p className="text-xs text-red-600">{erro}</p>}

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {buscando ? (
          <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-teal-400" /></div>
        ) : lista.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">Nenhum medicamento cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Princípio ativo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Espécie</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Dose</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Via</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lista.map((m) => (
                <tr key={m.id} className="hover:bg-teal-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{m.nome}</td>
                  <td className="px-4 py-3 text-gray-600">{m.principio_ativo ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{m.especie_alvo ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {m.dose_minima_mg_kg && m.dose_maxima_mg_kg
                      ? `${m.dose_minima_mg_kg}–${m.dose_maxima_mg_kg} ${m.unidade_dose ?? "mg/kg"}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{m.via_administracao ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <Modal titulo="Novo medicamento" onClose={() => setModal(false)} onSave={salvar} salvando={salvando}>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Nome *</label>
              <input type="text" value={form.nome} onChange={(e) => set("nome", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Princípio ativo</label>
              <input type="text" value={form.principio_ativo} onChange={(e) => set("principio_ativo", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Espécie alvo</label>
              <input type="text" value={form.especie} onChange={(e) => set("especie", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Ex: Cão, Gato…" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Dose mínima</label>
              <input type="number" value={form.dose_min} onChange={(e) => set("dose_min", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="mg/kg" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Dose máxima</label>
              <input type="number" value={form.dose_max} onChange={(e) => set("dose_max", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="mg/kg" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Via</label>
              <select value={form.via_administracao} onChange={(e) => set("via_administracao", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white">
                <option value="oral">Oral</option>
                <option value="iv">IV</option><option value="im">IM</option>
                <option value="sc">SC</option><option value="topico">Tópico</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Contraindicações</label>
              <textarea value={form.contraindicacoes} onChange={(e) => set("contraindicacoes", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-16" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Interações medicamentosas</label>
              <textarea value={form.interacoes} onChange={(e) => set("interacoes", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-16" />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// =========================================================
// ABA: PROCEDIMENTOS
// =========================================================
function CatProcedimentos() {
  const [lista, setLista] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ nome: "", descricao: "", duracao: "", preco: "" });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);

  async function carregar() {
    try {
      const res = await vetApi.listarCatalogoProcedimentos();
      setLista(Array.isArray(res.data) ? res.data : (res.data?.items ?? []));
    } catch { setErro("Erro ao carregar."); }
    finally { setCarregando(false); }
  }

  useEffect(() => { carregar(); }, []);

  function set(c, v) { setForm((p) => ({ ...p, [c]: v })); }

  async function salvar() {
    if (!form.nome) return;
    setSalvando(true);
    try {
      await vetApi.criarCatalogoProcedimento({
        nome: form.nome,
        descricao: form.descricao || undefined,
        duracao_estimada_min: form.duracao ? parseInt(form.duracao) : undefined,
        preco_sugerido: form.preco ? parseFloat(form.preco.replace(",", ".")) : undefined,
      });
      setModal(false);
      setForm({ nome: "", descricao: "", duracao: "", preco: "" });
      await carregar();
    } catch (e) { setErro(e?.response?.data?.detail ?? "Erro ao salvar."); }
    finally { setSalvando(false); }
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button onClick={() => setModal(true)}
          className="flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          <Plus size={14} /> Adicionar
        </button>
      </div>
      {erro && <p className="text-xs text-red-600">{erro}</p>}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {carregando ? (
          <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-teal-400" /></div>
        ) : lista.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">Nenhum procedimento cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Procedimento</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Duração estimada</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Preço sugerido</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lista.map((p) => (
                <tr key={p.id} className="hover:bg-teal-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{p.nome}</p>
                    {p.descricao && <p className="text-xs text-gray-400">{p.descricao}</p>}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{p.duracao_estimada_min ? `${p.duracao_estimada_min} min` : "—"}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {p.preco_sugerido
                      ? `R$ ${p.preco_sugerido.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <Modal titulo="Novo procedimento" onClose={() => setModal(false)} onSave={salvar} salvando={salvando}>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Nome *</label>
              <input type="text" value={form.nome} onChange={(e) => set("nome", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Descrição</label>
              <textarea value={form.descricao} onChange={(e) => set("descricao", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-16" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Duração (min)</label>
                <input type="number" value={form.duracao} onChange={(e) => set("duracao", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Preço sugerido (R$)</label>
                <input type="text" value={form.preco} onChange={(e) => set("preco", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="0,00" />
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// =========================================================
// ABA: PROTOCOLOS DE VACINAS
// =========================================================
function CatProtocolosVacinas() {
  const [lista, setLista] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ nome: "", especie: "", dose_inicial: "", reforcoDias: "", obrigatoria: false, descricao: "" });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);

  async function carregar() {
    try {
      const res = await vetApi.listarProtocolosVacinas();
      setLista(Array.isArray(res.data) ? res.data : (res.data?.items ?? []));
    } catch { setErro("Erro ao carregar."); }
    finally { setCarregando(false); }
  }

  useEffect(() => { carregar(); }, []);

  function set(c, v) { setForm((p) => ({ ...p, [c]: v })); }

  async function salvar() {
    if (!form.nome || !form.especie) return;
    setSalvando(true);
    try {
      await vetApi.criarCatalogoProcedimento(null); // não disponível — usa endpoint correto abaixo
      // NOTE: O endpoint real está em /vet/catalogo/protocolos-vacinas (POST já implementado)
      // Mas pelo vetApi só temos listarProtocolosVacinas sem um criarProtocolo separado.
      // Adicionamos chamada direta:
      const { api } = await import("../../services/api");
      await api.post("/vet/catalogo/protocolos-vacinas", {
        nome: form.nome,
        especie_alvo: form.especie,
        idade_primeira_dose_dias: form.dose_inicial ? parseInt(form.dose_inicial) : undefined,
        intervalo_reforco_dias: form.reforcoDias ? parseInt(form.reforcoDias) : undefined,
        obrigatoria: form.obrigatoria,
        descricao: form.descricao || undefined,
      });
      setModal(false);
      setForm({ nome: "", especie: "", dose_inicial: "", reforcoDias: "", obrigatoria: false, descricao: "" });
      await carregar();
    } catch (e) { setErro(e?.response?.data?.detail ?? "Erro ao salvar."); }
    finally { setSalvando(false); }
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button onClick={() => setModal(true)}
          className="flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          <Plus size={14} /> Adicionar
        </button>
      </div>
      {erro && <p className="text-xs text-red-600">{erro}</p>}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {carregando ? (
          <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-teal-400" /></div>
        ) : lista.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">Nenhum protocolo cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Vacina</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Espécie</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">1ª dose (dias)</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Reforço (dias)</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Obrigatória</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lista.map((v) => (
                <tr key={v.id} className="hover:bg-teal-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{v.nome}</td>
                  <td className="px-4 py-3 text-gray-600">{v.especie_alvo ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{v.idade_primeira_dose_dias ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{v.intervalo_reforco_dias ? `${v.intervalo_reforco_dias}d` : "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${v.obrigatoria ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-500"}`}>
                      {v.obrigatoria ? "Sim" : "Não"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <Modal titulo="Novo protocolo de vacina" onClose={() => setModal(false)} onSave={salvar} salvando={salvando}>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Nome *</label>
                <input type="text" value={form.nome} onChange={(e) => set("nome", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Espécie *</label>
                <input type="text" value={form.especie} onChange={(e) => set("especie", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Cão, Gato…" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">1ª dose (dias de vida)</label>
                <input type="number" value={form.dose_inicial} onChange={(e) => set("dose_inicial", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Reforço (dias)</label>
                <input type="number" value={form.reforcoDias} onChange={(e) => set("reforcoDias", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.obrigatoria} onChange={(e) => set("obrigatoria", e.target.checked)} className="rounded" />
              <span className="text-sm text-gray-700">Vacina obrigatória</span>
            </label>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Descrição</label>
              <textarea value={form.descricao} onChange={(e) => set("descricao", e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-16" />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// =========================================================
// COMPONENTE PRINCIPAL
// =========================================================
export default function VetCatalogo() {
  const [aba, setAba] = useState("medicamentos");

  return (
    <div className="p-6 space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-teal-100 rounded-xl">
          <BookOpen size={22} className="text-teal-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Catálogos</h1>
          <p className="text-sm text-gray-500">Medicamentos, procedimentos e protocolos de vacinas</p>
        </div>
      </div>

      {/* Abas */}
      <div className="flex border-b border-gray-200">
        {ABAS.map((a) => {
          const Icon = a.icon;
          return (
            <button
              key={a.id}
              onClick={() => setAba(a.id)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${aba === a.id ? "border-teal-500 text-teal-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            >
              <Icon size={14} />
              {a.label}
            </button>
          );
        })}
      </div>

      {/* Conteúdo */}
      {aba === "medicamentos" && <CatMedicamentos />}
      {aba === "procedimentos" && <CatProcedimentos />}
      {aba === "vacinas" && <CatProtocolosVacinas />}
    </div>
  );
}
