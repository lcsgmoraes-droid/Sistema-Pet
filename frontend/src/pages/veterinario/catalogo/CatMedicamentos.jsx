import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Loader2, Plus, Search } from "lucide-react";
import { vetApi } from "../vetApi";
import { formatLista, LinhaAcoes, Modal, parseListaTexto, parseNumero } from "./shared";

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

export default function CatMedicamentos() {
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
