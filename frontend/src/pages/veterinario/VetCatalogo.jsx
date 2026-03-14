import { useState, useEffect, useCallback } from "react";
import { BookOpen, Plus, Search, AlertCircle, Pill, Syringe, ClipboardList } from "lucide-react";
import { vetApi } from "./vetApi";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";

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
  const [produtos, setProdutos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ nome: "", descricao: "", duracao: "", preco: "", insumos: [] });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);

  async function carregar() {
    try {
      const [resProcedimentos, resProdutos] = await Promise.all([
        vetApi.listarCatalogoProcedimentos(),
        vetApi.listarProdutosEstoque(),
      ]);
      setLista(Array.isArray(resProcedimentos.data) ? resProcedimentos.data : (resProcedimentos.data?.items ?? []));
      setProdutos(Array.isArray(resProdutos.data) ? resProdutos.data : (resProdutos.data?.items ?? []));
    } catch { setErro("Erro ao carregar."); }
    finally { setCarregando(false); }
  }

  useEffect(() => { carregar(); }, []);

  const custoEstimadoForm = form.insumos.reduce((total, item) => {
    const produto = produtos.find((prod) => String(prod.id) === String(item.produto_id));
    const quantidade = Number(String(item.quantidade || 0).replace(",", ".")) || 0;
    const custoUnitario = Number(produto?.preco_custo || 0);
    return total + (custoUnitario * quantidade);
  }, 0);
  const precoSugeridoForm = Number(String(form.preco || 0).replace(",", ".")) || 0;
  const margemEstimadaForm = precoSugeridoForm - custoEstimadoForm;
  const margemPercentualForm = precoSugeridoForm > 0 ? (margemEstimadaForm / precoSugeridoForm) * 100 : 0;

  function set(c, v) { setForm((p) => ({ ...p, [c]: v })); }

  function atualizarInsumo(idx, campo, valor) {
    setForm((prev) => {
      const insumos = [...prev.insumos];
      insumos[idx] = { ...insumos[idx], [campo]: valor };
      return { ...prev, insumos };
    });
  }

  function adicionarInsumo() {
    setForm((prev) => ({
      ...prev,
      insumos: [...prev.insumos, { produto_id: "", quantidade: "1", baixar_estoque: true }],
    }));
  }

  function removerInsumo(idx) {
    setForm((prev) => ({
      ...prev,
      insumos: prev.insumos.filter((_, index) => index !== idx),
    }));
  }

  async function salvar() {
    if (!form.nome) return;
    setSalvando(true);
    try {
      await vetApi.criarCatalogoProcedimento({
        nome: form.nome,
        descricao: form.descricao || undefined,
        duracao_minutos: form.duracao ? parseInt(form.duracao) : undefined,
        valor_padrao: form.preco ? parseFloat(form.preco.replace(",", ".")) : undefined,
        insumos: form.insumos
          .map((item) => ({
            produto_id: item.produto_id ? Number(item.produto_id) : null,
            quantidade: item.quantidade ? Number(String(item.quantidade).replace(",", ".")) : null,
            baixar_estoque: item.baixar_estoque !== false,
          }))
          .filter((item) => item.produto_id && item.quantidade > 0),
      });
      setModal(false);
      setForm({ nome: "", descricao: "", duracao: "", preco: "", insumos: [] });
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">Insumos</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Duração estimada</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Preço sugerido</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Custo est.</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Margem est.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lista.map((p) => (
                <tr key={p.id} className="hover:bg-teal-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{p.nome}</p>
                    {p.descricao && <p className="text-xs text-gray-400">{p.descricao}</p>}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {Array.isArray(p.insumos) && p.insumos.length > 0
                      ? `${p.insumos.length} item(ns)`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{p.duracao_estimada_min ? `${p.duracao_estimada_min} min` : "—"}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {p.valor_padrao != null
                      ? formatMoneyBRL(p.valor_padrao)
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{formatMoneyBRL(p.custo_estimado || 0)}</td>
                  <td className="px-4 py-3">
                    <p className={`font-medium ${(p.margem_estimada || 0) < 0 ? "text-red-600" : "text-emerald-700"}`}>
                      {formatMoneyBRL(p.margem_estimada || 0)}
                    </p>
                    <p className="text-xs text-gray-400">{formatPercent(p.margem_percentual_estimada || 0)}</p>
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

            <div className="space-y-2 rounded-xl border border-gray-200 p-3 bg-gray-50">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-700">Insumos com baixa automática</p>
                  <p className="text-xs text-gray-500">Escolha produtos do estoque que devem sair ao registrar o procedimento.</p>
                </div>
                <button type="button" onClick={adicionarInsumo} className="text-xs px-3 py-1.5 rounded-lg bg-white border border-gray-200 hover:bg-gray-100">
                  + Adicionar insumo
                </button>
              </div>

              {form.insumos.length === 0 ? (
                <p className="text-xs text-gray-500">Nenhum insumo vinculado.</p>
              ) : form.insumos.map((item, idx) => (
                <div key={`insumo_${idx}`} className="grid grid-cols-12 gap-2 items-center">
                  <select
                    value={item.produto_id}
                    onChange={(e) => atualizarInsumo(idx, "produto_id", e.target.value)}
                    className="col-span-7 border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                  >
                    <option value="">Selecione um produto</option>
                    {produtos.map((produto) => (
                      <option key={produto.id} value={produto.id}>
                        {produto.nome} • estoque {produto.estoque_atual} {produto.unidade || "UN"}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={item.quantidade}
                    onChange={(e) => atualizarInsumo(idx, "quantidade", e.target.value)}
                    className="col-span-3 border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                    placeholder="Qtd."
                  />
                  <button type="button" onClick={() => removerInsumo(idx)} className="col-span-2 text-xs px-2 py-2 rounded-lg border border-red-200 text-red-600 hover:bg-red-50">
                    Remover
                  </button>
                </div>
              ))}

              <div className="grid grid-cols-3 gap-3 pt-2 border-t border-gray-200">
                <div className="rounded-lg bg-white border border-gray-200 px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Preço</p>
                  <p className="text-sm font-semibold text-gray-800">{formatMoneyBRL(precoSugeridoForm)}</p>
                </div>
                <div className="rounded-lg bg-white border border-gray-200 px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Custo est.</p>
                  <p className="text-sm font-semibold text-amber-700">{formatMoneyBRL(custoEstimadoForm)}</p>
                </div>
                <div className="rounded-lg bg-white border border-gray-200 px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Margem est.</p>
                  <p className={`text-sm font-semibold ${margemEstimadaForm < 0 ? "text-red-600" : "text-emerald-700"}`}>
                    {formatMoneyBRL(margemEstimadaForm)}
                  </p>
                  <p className="text-[11px] text-gray-400">{formatPercent(margemPercentualForm)}</p>
                </div>
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
      await vetApi.criarProtocoloVacina({
        nome: form.nome,
        especie: form.especie,
        numero_doses_serie: 1,
        intervalo_doses_dias: form.reforcoDias ? parseInt(form.reforcoDias) : undefined,
        reforco_anual: form.obrigatoria,
        observacoes: [
          form.dose_inicial ? `Primeira dose sugerida: ${form.dose_inicial} dias` : null,
          form.descricao || null,
        ].filter(Boolean).join(' | ') || undefined,
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
