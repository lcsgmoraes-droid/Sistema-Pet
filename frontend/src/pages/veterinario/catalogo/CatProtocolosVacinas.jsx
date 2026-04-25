import { useEffect, useState } from "react";
import { AlertCircle, Loader2, Plus } from "lucide-react";
import { vetApi } from "../vetApi";
import { LinhaAcoes, Modal } from "./shared";

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

export default function CatProtocolosVacinas() {
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
