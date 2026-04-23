import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  ClipboardList,
  Loader2,
  Pencil,
  Pill,
  Plus,
  Search,
  Syringe,
  Trash2,
  X,
} from "lucide-react";
import { vetApi } from "./vetApi";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";

function formatLista(lista) {
  if (!Array.isArray(lista) || lista.length === 0) return "-";
  return lista.join(", ");
}

function parseListaTexto(texto) {
  return String(texto || "")
    .split(/[,\n;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseNumero(value) {
  if (value == null || value === "") return undefined;
  const numero = Number(String(value).replace(",", "."));
  return Number.isFinite(numero) ? numero : undefined;
}

function Modal({ titulo, subtitulo, onClose, onSave, salvando, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-gray-800">{titulo}</h2>
            {subtitulo && <p className="mt-1 text-sm text-gray-500">{subtitulo}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal"
          >
            <X size={18} />
          </button>
        </div>
        <div className="mt-5 space-y-4">{children}</div>
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={salvando}
            className="flex-1 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </div>
    </div>
  );
}

function LinhaAcoes({ onEditar, onExcluir, removendo }) {
  return (
    <div className="flex justify-end gap-2">
      <button
        type="button"
        onClick={onEditar}
        className="inline-flex items-center gap-1 rounded-lg border border-blue-200 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50"
      >
        <Pencil size={13} />
        Editar
      </button>
      <button
        type="button"
        onClick={onExcluir}
        disabled={removendo}
        className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-60"
      >
        {removendo ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
        Excluir
      </button>
    </div>
  );
}

const ABAS = [
  { id: "medicamentos", label: "Medicamentos", icon: Pill },
  { id: "procedimentos", label: "Procedimentos", icon: ClipboardList },
  { id: "vacinas", label: "Protocolos de vacinas", icon: Syringe },
];

const FORM_MEDICAMENTO_INICIAL = {
  nome: "",
  nome_comercial: "",
  principio_ativo: "",
  fabricante: "",
  forma_farmaceutica: "",
  concentracao: "",
  especies_indicadas: "",
  indicacoes: "",
  posologia_referencia: "",
  dose_min_mgkg: "",
  dose_max_mgkg: "",
  contraindicacoes: "",
  interacoes: "",
  observacoes: "",
  eh_antibiotico: false,
  eh_controlado: false,
};

function mapMedicamentoParaForm(item) {
  return {
    nome: item?.nome || "",
    nome_comercial: item?.nome_comercial || "",
    principio_ativo: item?.principio_ativo || "",
    fabricante: item?.fabricante || "",
    forma_farmaceutica: item?.forma_farmaceutica || "",
    concentracao: item?.concentracao || "",
    especies_indicadas: Array.isArray(item?.especies_indicadas) ? item.especies_indicadas.join(", ") : "",
    indicacoes: item?.indicacoes || "",
    posologia_referencia: item?.posologia_referencia || "",
    dose_min_mgkg: item?.dose_min_mgkg ?? "",
    dose_max_mgkg: item?.dose_max_mgkg ?? "",
    contraindicacoes: item?.contraindicacoes || "",
    interacoes: item?.interacoes || "",
    observacoes: item?.observacoes || "",
    eh_antibiotico: Boolean(item?.eh_antibiotico),
    eh_controlado: Boolean(item?.eh_controlado),
  };
}

function buildMedicamentoPayload(form) {
  return {
    nome: form.nome.trim(),
    nome_comercial: form.nome_comercial.trim() || undefined,
    principio_ativo: form.principio_ativo.trim() || undefined,
    fabricante: form.fabricante.trim() || undefined,
    forma_farmaceutica: form.forma_farmaceutica.trim() || undefined,
    concentracao: form.concentracao.trim() || undefined,
    especies_indicadas: parseListaTexto(form.especies_indicadas),
    indicacoes: form.indicacoes.trim() || undefined,
    posologia_referencia: form.posologia_referencia.trim() || undefined,
    dose_min_mgkg: parseNumero(form.dose_min_mgkg),
    dose_max_mgkg: parseNumero(form.dose_max_mgkg),
    contraindicacoes: form.contraindicacoes.trim() || undefined,
    interacoes: form.interacoes.trim() || undefined,
    observacoes: form.observacoes.trim() || undefined,
    eh_antibiotico: Boolean(form.eh_antibiotico),
    eh_controlado: Boolean(form.eh_controlado),
  };
}

function CatMedicamentos() {
  const [lista, setLista] = useState([]);
  const [busca, setBusca] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [removendoId, setRemovendoId] = useState(null);
  const [form, setForm] = useState(FORM_MEDICAMENTO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setBuscando(true);
    setErro("");
    try {
      const response = await vetApi.listarMedicamentos(busca || undefined);
      setLista(Array.isArray(response.data) ? response.data : response.data?.items ?? []);
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao carregar medicamentos.");
    } finally {
      setBuscando(false);
    }
  }, [busca]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  function abrirNovo() {
    setEditando(null);
    setForm(FORM_MEDICAMENTO_INICIAL);
    setModalAberto(true);
    setErro("");
  }

  function abrirEdicao(item) {
    setEditando(item);
    setForm(mapMedicamentoParaForm(item));
    setModalAberto(true);
    setErro("");
  }

  function setCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  async function salvar() {
    if (!form.nome.trim()) return;
    setSalvando(true);
    setErro("");
    try {
      const payload = buildMedicamentoPayload(form);
      if (editando?.id) {
        await vetApi.atualizarMedicamento(editando.id, payload);
      } else {
        await vetApi.criarMedicamento(payload);
      }
      setModalAberto(false);
      setEditando(null);
      setForm(FORM_MEDICAMENTO_INICIAL);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao salvar medicamento.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(item) {
    if (!window.confirm(`Deseja excluir o medicamento "${item.nome}"?`)) return;
    setRemovendoId(item.id);
    setErro("");
    try {
      await vetApi.removerMedicamento(item.id);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao excluir medicamento.");
    } finally {
      setRemovendoId(null);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={busca}
            onChange={(event) => setBusca(event.target.value)}
            placeholder="Buscar por nome, comercial ou principio ativo..."
            className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-300"
          />
        </div>
        <button
          type="button"
          onClick={abrirNovo}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          <Plus size={14} />
          Adicionar
        </button>
      </div>

      {erro && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {buscando ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
          </div>
        ) : lista.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">Nenhum medicamento cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Medicamento</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Especies</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Posologia base</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Dose</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Acoes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lista.map((item) => (
                <tr key={item.id} className="hover:bg-teal-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{item.nome}</p>
                    <p className="text-xs text-gray-500">
                      {item.nome_comercial || item.principio_ativo || item.fabricante || "-"}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{formatLista(item.especies_indicadas)}</td>
                  <td className="px-4 py-3 text-gray-600">{item.posologia_referencia || "-"}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {item.dose_min_mgkg || item.dose_max_mgkg
                      ? `${item.dose_min_mgkg ?? "-"} a ${item.dose_max_mgkg ?? "-"} mg/kg`
                      : "-"}
                  </td>
                  <td className="px-4 py-3">
                    <LinhaAcoes
                      onEditar={() => abrirEdicao(item)}
                      onExcluir={() => excluir(item)}
                      removendo={removendoId === item.id}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modalAberto && (
        <Modal
          titulo={editando ? "Editar medicamento" : "Novo medicamento"}
          subtitulo="Cadastre ou ajuste a referencia para prescricao, dose e apoio clinico."
          onClose={() => setModalAberto(false)}
          onSave={salvar}
          salvando={salvando}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-gray-600">Nome *</label>
              <input
                type="text"
                value={form.nome}
                onChange={(event) => setCampo("nome", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Nome comercial</label>
              <input
                type="text"
                value={form.nome_comercial}
                onChange={(event) => setCampo("nome_comercial", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Principio ativo</label>
              <input
                type="text"
                value={form.principio_ativo}
                onChange={(event) => setCampo("principio_ativo", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Fabricante</label>
              <input
                type="text"
                value={form.fabricante}
                onChange={(event) => setCampo("fabricante", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Forma farmaceutica</label>
              <input
                type="text"
                value={form.forma_farmaceutica}
                onChange={(event) => setCampo("forma_farmaceutica", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="Comprimido, solucao, pomada..."
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Concentracao</label>
              <input
                type="text"
                value={form.concentracao}
                onChange={(event) => setCampo("concentracao", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="250 mg, 5%, 10 mg/ml..."
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Especies indicadas</label>
              <input
                type="text"
                value={form.especies_indicadas}
                onChange={(event) => setCampo("especies_indicadas", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="cao, gato, aves..."
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Posologia de referencia</label>
              <input
                type="text"
                value={form.posologia_referencia}
                onChange={(event) => setCampo("posologia_referencia", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="1 comp a cada 12h por 7 dias"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Dose minima (mg/kg)</label>
              <input
                type="number"
                step="0.01"
                value={form.dose_min_mgkg}
                onChange={(event) => setCampo("dose_min_mgkg", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Dose maxima (mg/kg)</label>
              <input
                type="number"
                step="0.01"
                value={form.dose_max_mgkg}
                onChange={(event) => setCampo("dose_max_mgkg", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-gray-600">Indicacoes</label>
              <textarea
                value={form.indicacoes}
                onChange={(event) => setCampo("indicacoes", event.target.value)}
                className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Contraindicacoes</label>
              <textarea
                value={form.contraindicacoes}
                onChange={(event) => setCampo("contraindicacoes", event.target.value)}
                className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Interacoes</label>
              <textarea
                value={form.interacoes}
                onChange={(event) => setCampo("interacoes", event.target.value)}
                className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes</label>
              <textarea
                value={form.observacoes}
                onChange={(event) => setCampo("observacoes", event.target.value)}
                className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={form.eh_antibiotico}
                onChange={(event) => setCampo("eh_antibiotico", event.target.checked)}
              />
              Antibiotico
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={form.eh_controlado}
                onChange={(event) => setCampo("eh_controlado", event.target.checked)}
              />
              Controlado
            </label>
          </div>
        </Modal>
      )}
    </div>
  );
}

const FORM_PROCEDIMENTO_INICIAL = {
  nome: "",
  descricao: "",
  categoria: "",
  duracao: "",
  preco: "",
  requer_anestesia: false,
  observacoes: "",
  insumos: [],
};

function mapProcedimentoParaForm(item) {
  return {
    nome: item?.nome || "",
    descricao: item?.descricao || "",
    categoria: item?.categoria || "",
    duracao: item?.duracao_minutos ?? item?.duracao_estimada_min ?? "",
    preco: item?.valor_padrao ?? "",
    requer_anestesia: Boolean(item?.requer_anestesia),
    observacoes: item?.observacoes || "",
    insumos: Array.isArray(item?.insumos)
      ? item.insumos.map((insumo) => ({
          produto_id: insumo.produto_id ? String(insumo.produto_id) : "",
          quantidade: insumo.quantidade ?? "1",
          baixar_estoque: insumo.baixar_estoque !== false,
        }))
      : [],
  };
}

function CatProcedimentos() {
  const [lista, setLista] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(FORM_PROCEDIMENTO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [removendoId, setRemovendoId] = useState(null);
  const [erro, setErro] = useState("");

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const [procedimentosResponse, produtosResponse] = await Promise.all([
        vetApi.listarCatalogoProcedimentos(),
        vetApi.listarProdutosEstoque(),
      ]);
      setLista(
        Array.isArray(procedimentosResponse.data)
          ? procedimentosResponse.data
          : procedimentosResponse.data?.items ?? []
      );
      setProdutos(Array.isArray(produtosResponse.data) ? produtosResponse.data : produtosResponse.data?.items ?? []);
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao carregar procedimentos.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  function setCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  function abrirNovo() {
    setEditando(null);
    setForm(FORM_PROCEDIMENTO_INICIAL);
    setModalAberto(true);
    setErro("");
  }

  function abrirEdicao(item) {
    setEditando(item);
    setForm(mapProcedimentoParaForm(item));
    setModalAberto(true);
    setErro("");
  }

  function atualizarInsumo(index, campo, valor) {
    setForm((prev) => {
      const insumos = [...prev.insumos];
      insumos[index] = { ...insumos[index], [campo]: valor };
      return { ...prev, insumos };
    });
  }

  function adicionarInsumo() {
    setForm((prev) => ({
      ...prev,
      insumos: [...prev.insumos, { produto_id: "", quantidade: "1", baixar_estoque: true }],
    }));
  }

  function removerInsumo(index) {
    setForm((prev) => ({
      ...prev,
      insumos: prev.insumos.filter((_, currentIndex) => currentIndex !== index),
    }));
  }

  const custoEstimadoForm = form.insumos.reduce((total, item) => {
    const produto = produtos.find((produtoAtual) => String(produtoAtual.id) === String(item.produto_id));
    return total + (Number(produto?.preco_custo || 0) * (parseNumero(item.quantidade) || 0));
  }, 0);
  const precoSugeridoForm = parseNumero(form.preco) || 0;
  const margemEstimadaForm = precoSugeridoForm - custoEstimadoForm;
  const margemPercentualForm = precoSugeridoForm > 0 ? (margemEstimadaForm / precoSugeridoForm) * 100 : 0;

  async function salvar() {
    if (!form.nome.trim()) return;
    setSalvando(true);
    setErro("");
    try {
      const payload = {
        nome: form.nome.trim(),
        descricao: form.descricao.trim() || undefined,
        categoria: form.categoria.trim() || undefined,
        valor_padrao: parseNumero(form.preco),
        duracao_minutos: form.duracao ? parseInt(form.duracao, 10) : undefined,
        requer_anestesia: Boolean(form.requer_anestesia),
        observacoes: form.observacoes.trim() || undefined,
        insumos: form.insumos
          .map((item) => ({
            produto_id: item.produto_id ? Number(item.produto_id) : null,
            quantidade: parseNumero(item.quantidade),
            baixar_estoque: item.baixar_estoque !== false,
          }))
          .filter((item) => item.produto_id && item.quantidade > 0),
      };

      if (editando?.id) {
        await vetApi.atualizarCatalogoProcedimento(editando.id, payload);
      } else {
        await vetApi.criarCatalogoProcedimento(payload);
      }
      setModalAberto(false);
      setEditando(null);
      setForm(FORM_PROCEDIMENTO_INICIAL);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao salvar procedimento.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(item) {
    if (!window.confirm(`Deseja excluir o procedimento "${item.nome}"?`)) return;
    setRemovendoId(item.id);
    setErro("");
    try {
      await vetApi.removerCatalogoProcedimento(item.id);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao excluir procedimento.");
    } finally {
      setRemovendoId(null);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={abrirNovo}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          <Plus size={14} />
          Adicionar
        </button>
      </div>

      {erro && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {carregando ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
          </div>
        ) : lista.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">Nenhum procedimento cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Procedimento</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Insumos</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Duracao</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Preco sugerido</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Margem estimada</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Acoes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lista.map((item) => (
                <tr key={item.id} className="hover:bg-teal-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{item.nome}</p>
                    <p className="text-xs text-gray-500">
                      {item.categoria || item.descricao || (item.requer_anestesia ? "Requer anestesia" : "-")}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {Array.isArray(item.insumos) && item.insumos.length > 0 ? `${item.insumos.length} item(ns)` : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {item.duracao_minutos || item.duracao_estimada_min
                      ? `${item.duracao_minutos || item.duracao_estimada_min} min`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{formatMoneyBRL(item.valor_padrao || 0)}</td>
                  <td className="px-4 py-3">
                    <p className={`font-medium ${(item.margem_estimada || 0) < 0 ? "text-red-600" : "text-emerald-700"}`}>
                      {formatMoneyBRL(item.margem_estimada || 0)}
                    </p>
                    <p className="text-xs text-gray-400">{formatPercent(item.margem_percentual_estimada || 0)}</p>
                  </td>
                  <td className="px-4 py-3">
                    <LinhaAcoes
                      onEditar={() => abrirEdicao(item)}
                      onExcluir={() => excluir(item)}
                      removendo={removendoId === item.id}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modalAberto && (
        <Modal
          titulo={editando ? "Editar procedimento" : "Novo procedimento"}
          subtitulo="Monte o procedimento com duracao, preco e insumos que devem sair do estoque."
          onClose={() => setModalAberto(false)}
          onSave={salvar}
          salvando={salvando}
        >
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Nome *</label>
                <input
                  type="text"
                  value={form.nome}
                  onChange={(event) => setCampo("nome", event.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Categoria</label>
                <input
                  type="text"
                  value={form.categoria}
                  onChange={(event) => setCampo("categoria", event.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="Consulta, coleta, curativo..."
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Duracao (min)</label>
                <input
                  type="number"
                  value={form.duracao}
                  onChange={(event) => setCampo("duracao", event.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Preco sugerido (R$)</label>
                <input
                  type="text"
                  value={form.preco}
                  onChange={(event) => setCampo("preco", event.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="0,00"
                />
              </div>
              <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.requer_anestesia}
                  onChange={(event) => setCampo("requer_anestesia", event.target.checked)}
                />
                Requer anestesia
              </label>
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Descricao</label>
                <textarea
                  value={form.descricao}
                  onChange={(event) => setCampo("descricao", event.target.value)}
                  className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes internas</label>
                <textarea
                  value={form.observacoes}
                  onChange={(event) => setCampo("observacoes", event.target.value)}
                  className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="space-y-3 rounded-xl border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-gray-800">Insumos com baixa automatica</p>
                  <p className="text-xs text-gray-500">
                    Escolha os itens do estoque que saem automaticamente quando o procedimento for usado.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={adicionarInsumo}
                  className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium hover:bg-gray-100"
                >
                  + Adicionar insumo
                </button>
              </div>

              {form.insumos.length === 0 ? (
                <p className="text-xs text-gray-500">Nenhum insumo vinculado.</p>
              ) : (
                form.insumos.map((item, index) => (
                  <div key={`insumo_${index}`} className="grid gap-2 md:grid-cols-12">
                    <select
                      value={item.produto_id}
                      onChange={(event) => atualizarInsumo(index, "produto_id", event.target.value)}
                      className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm md:col-span-7"
                    >
                      <option value="">Selecione um produto</option>
                      {produtos.map((produto) => (
                        <option key={produto.id} value={produto.id}>
                          {produto.nome} - estoque {produto.estoque_atual} {produto.unidade || "UN"}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={item.quantidade}
                      onChange={(event) => atualizarInsumo(index, "quantidade", event.target.value)}
                      className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm md:col-span-2"
                      placeholder="Qtd."
                    />
                    <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs md:col-span-2">
                      <input
                        type="checkbox"
                        checked={item.baixar_estoque !== false}
                        onChange={(event) => atualizarInsumo(index, "baixar_estoque", event.target.checked)}
                      />
                      Baixar
                    </label>
                    <button
                      type="button"
                      onClick={() => removerInsumo(index)}
                      className="rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50 md:col-span-1"
                    >
                      X
                    </button>
                  </div>
                ))
              )}

              <div className="grid gap-3 border-t border-gray-200 pt-3 md:grid-cols-3">
                <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Preco</p>
                  <p className="text-sm font-semibold text-gray-800">{formatMoneyBRL(precoSugeridoForm)}</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Custo estimado</p>
                  <p className="text-sm font-semibold text-amber-700">{formatMoneyBRL(custoEstimadoForm)}</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Margem estimada</p>
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

const FORM_PROTOCOLO_INICIAL = {
  nome: "",
  especie: "",
  dose_inicial_semanas: "",
  numero_doses_serie: "1",
  intervalo_doses_dias: "",
  reforco_anual: true,
  observacoes: "",
};

function mapProtocoloParaForm(item) {
  return {
    nome: item?.nome || "",
    especie: item?.especie || "",
    dose_inicial_semanas: item?.dose_inicial_semanas ?? "",
    numero_doses_serie: item?.numero_doses_serie ?? "1",
    intervalo_doses_dias: item?.intervalo_doses_dias ?? "",
    reforco_anual: item?.reforco_anual !== false,
    observacoes: item?.observacoes || "",
  };
}

function buildProtocoloPayload(form) {
  return {
    nome: form.nome.trim(),
    especie: form.especie.trim() || undefined,
    dose_inicial_semanas: form.dose_inicial_semanas ? parseInt(form.dose_inicial_semanas, 10) : undefined,
    numero_doses_serie: form.numero_doses_serie ? parseInt(form.numero_doses_serie, 10) : undefined,
    intervalo_doses_dias: form.intervalo_doses_dias ? parseInt(form.intervalo_doses_dias, 10) : undefined,
    reforco_anual: Boolean(form.reforco_anual),
    observacoes: form.observacoes.trim() || undefined,
  };
}

function CatProtocolosVacinas() {
  const [lista, setLista] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(FORM_PROTOCOLO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [removendoId, setRemovendoId] = useState(null);
  const [erro, setErro] = useState("");

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const response = await vetApi.listarProtocolosVacinas();
      setLista(Array.isArray(response.data) ? response.data : response.data?.items ?? []);
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao carregar protocolos.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  function abrirNovo() {
    setEditando(null);
    setForm(FORM_PROTOCOLO_INICIAL);
    setModalAberto(true);
    setErro("");
  }

  function abrirEdicao(item) {
    setEditando(item);
    setForm(mapProtocoloParaForm(item));
    setModalAberto(true);
    setErro("");
  }

  function setCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  async function salvar() {
    if (!form.nome.trim() || !form.especie.trim()) return;
    setSalvando(true);
    setErro("");
    try {
      const payload = buildProtocoloPayload(form);
      if (editando?.id) {
        await vetApi.atualizarProtocoloVacina(editando.id, payload);
      } else {
        await vetApi.criarProtocoloVacina(payload);
      }
      setModalAberto(false);
      setEditando(null);
      setForm(FORM_PROTOCOLO_INICIAL);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao salvar protocolo.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(item) {
    if (!window.confirm(`Deseja excluir o protocolo "${item.nome}"?`)) return;
    setRemovendoId(item.id);
    setErro("");
    try {
      await vetApi.removerProtocoloVacina(item.id);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao excluir protocolo.");
    } finally {
      setRemovendoId(null);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={abrirNovo}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          <Plus size={14} />
          Adicionar
        </button>
      </div>

      {erro && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {carregando ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
          </div>
        ) : lista.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">Nenhum protocolo cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Protocolo</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Especie</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Inicio</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Serie</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Reforco</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Acoes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lista.map((item) => (
                <tr key={item.id} className="hover:bg-teal-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{item.nome}</p>
                    <p className="text-xs text-gray-500">{item.observacoes || "-"}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{item.especie || "-"}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {item.dose_inicial_semanas ? `${item.dose_inicial_semanas} semana(s)` : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {item.numero_doses_serie || 1}
                    {item.intervalo_doses_dias ? ` x ${item.intervalo_doses_dias} dias` : ""}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        item.reforco_anual ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {item.reforco_anual ? "Anual" : "Nao anual"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <LinhaAcoes
                      onEditar={() => abrirEdicao(item)}
                      onExcluir={() => excluir(item)}
                      removendo={removendoId === item.id}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modalAberto && (
        <Modal
          titulo={editando ? "Editar protocolo de vacina" : "Novo protocolo de vacina"}
          subtitulo="Defina especie, serie, inicio e reforcos do protocolo."
          onClose={() => setModalAberto(false)}
          onSave={salvar}
          salvando={salvando}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Nome *</label>
              <input
                type="text"
                value={form.nome}
                onChange={(event) => setCampo("nome", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Especie *</label>
              <input
                type="text"
                value={form.especie}
                onChange={(event) => setCampo("especie", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="Cao, gato..."
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Inicio (semanas de vida)</label>
              <input
                type="number"
                value={form.dose_inicial_semanas}
                onChange={(event) => setCampo("dose_inicial_semanas", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Numero de doses</label>
              <input
                type="number"
                min="1"
                value={form.numero_doses_serie}
                onChange={(event) => setCampo("numero_doses_serie", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Intervalo entre doses (dias)</label>
              <input
                type="number"
                min="1"
                value={form.intervalo_doses_dias}
                onChange={(event) => setCampo("intervalo_doses_dias", event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={form.reforco_anual}
                onChange={(event) => setCampo("reforco_anual", event.target.checked)}
              />
              Tem reforco anual
            </label>
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes</label>
              <textarea
                value={form.observacoes}
                onChange={(event) => setCampo("observacoes", event.target.value)}
                className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default function VetCatalogo() {
  const [aba, setAba] = useState("medicamentos");

  return (
    <div className="space-y-5 p-6">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-teal-100 p-2">
          <BookOpen size={22} className="text-teal-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Catalogos</h1>
          <p className="text-sm text-gray-500">Medicamentos, procedimentos e protocolos de vacinas.</p>
        </div>
      </div>

      <div className="flex border-b border-gray-200">
        {ABAS.map((abaAtual) => {
          const Icon = abaAtual.icon;
          return (
            <button
              key={abaAtual.id}
              type="button"
              onClick={() => setAba(abaAtual.id)}
              className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                aba === abaAtual.id
                  ? "border-teal-500 text-teal-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <Icon size={14} />
              {abaAtual.label}
            </button>
          );
        })}
      </div>

      {aba === "medicamentos" && <CatMedicamentos />}
      {aba === "procedimentos" && <CatProcedimentos />}
      {aba === "vacinas" && <CatProtocolosVacinas />}
    </div>
  );
}
