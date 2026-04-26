import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { resolveMediaUrl } from "../../../utils/mediaUrl";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";

const initialFoto = {
  tipo: "entrada",
  url: "",
  descricao: "",
};

export default function BanhoTosaFotosPanel({ atendimentoId, onChanged }) {
  const fileInputRef = useRef(null);
  const [fotos, setFotos] = useState([]);
  const [fotoForm, setFotoForm] = useState(initialFoto);
  const [arquivo, setArquivo] = useState(null);
  const [saving, setSaving] = useState(false);

  async function carregarFotos() {
    if (!atendimentoId) return;
    try {
      const response = await banhoTosaApi.listarFotosAtendimento(atendimentoId);
      setFotos(Array.isArray(response.data) ? response.data : []);
    } catch {
      setFotos([]);
    }
  }

  useEffect(() => {
    carregarFotos();
  }, [atendimentoId]);

  function updateFoto(field, value) {
    setFotoForm((prev) => ({ ...prev, [field]: value }));
  }

  async function salvarUpload(event) {
    event.preventDefault();
    if (!arquivo) {
      toast.error("Selecione uma foto para enviar.");
      return;
    }

    const formData = new FormData();
    formData.append("tipo", fotoForm.tipo);
    formData.append("descricao", fotoForm.descricao || "");
    formData.append("arquivo", arquivo);

    setSaving(true);
    try {
      await banhoTosaApi.uploadFotoAtendimento(atendimentoId, formData);
      toast.success("Foto enviada.");
      resetarFormulario();
      await carregarFotos();
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel enviar foto."));
    } finally {
      setSaving(false);
    }
  }

  async function salvarUrl(event) {
    event.preventDefault();
    if (!fotoForm.url.trim()) {
      toast.error("Informe a URL da foto.");
      return;
    }

    setSaving(true);
    try {
      await banhoTosaApi.registrarFotoAtendimento(atendimentoId, fotoForm);
      toast.success("Foto registrada.");
      resetarFormulario();
      await carregarFotos();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel registrar foto."));
    } finally {
      setSaving(false);
    }
  }

  async function removerFoto(foto) {
    setSaving(true);
    try {
      await banhoTosaApi.removerFotoAtendimento(atendimentoId, foto.id);
      toast.success("Foto removida.");
      await carregarFotos();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel remover foto."));
    } finally {
      setSaving(false);
    }
  }

  function resetarFormulario() {
    setFotoForm(initialFoto);
    setArquivo(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5">
      <Header eyebrow="Fotos" title="Entrada, ocorrencia e resultado" />
      <form onSubmit={salvarUpload} className="mt-4 space-y-3">
        <FotoCampos form={fotoForm} onChange={updateFoto} />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(event) => setArquivo(event.target.files?.[0] || null)}
          className="block w-full rounded-2xl border border-dashed border-orange-200 bg-orange-50 px-3 py-3 text-sm font-semibold text-slate-700 file:mr-4 file:rounded-xl file:border-0 file:bg-orange-500 file:px-4 file:py-2 file:text-sm file:font-bold file:text-white"
        />
        <button
          type="submit"
          disabled={saving}
          className="rounded-2xl bg-orange-500 px-5 py-2 text-sm font-bold text-white transition hover:bg-orange-600 disabled:opacity-60"
        >
          Enviar foto
        </button>
      </form>

      <form onSubmit={salvarUrl} className="mt-4 space-y-3 rounded-2xl bg-slate-50 p-3">
        <TextField label="URL externa opcional" value={fotoForm.url} onChange={(value) => updateFoto("url", value)} />
        <button
          type="submit"
          disabled={saving}
          className="rounded-2xl bg-slate-900 px-4 py-2 text-xs font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          Registrar por URL
        </button>
      </form>

      <GaleriaFotos fotos={fotos} saving={saving} onRemover={removerFoto} />
    </section>
  );
}

function FotoCampos({ form, onChange }) {
  return (
    <div className="grid gap-3 sm:grid-cols-[0.6fr_1.4fr]">
      <SelectField label="Tipo" value={form.tipo} onChange={(value) => onChange("tipo", value)}>
        <option value="entrada">Entrada</option>
        <option value="antes">Antes</option>
        <option value="depois">Depois</option>
        <option value="ocorrencia">Ocorrencia</option>
      </SelectField>
      <TextField label="Descricao" value={form.descricao} onChange={(value) => onChange("descricao", value)} />
    </div>
  );
}

function GaleriaFotos({ fotos, saving, onRemover }) {
  if (fotos.length === 0) {
    return (
      <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
        Nenhuma foto registrada ainda.
      </p>
    );
  }

  return (
    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      {fotos.map((foto) => (
        <div key={foto.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
          <a href={resolveMediaUrl(foto.url)} target="_blank" rel="noreferrer">
            <img
              src={resolveMediaUrl(foto.thumbnail_url || foto.url)}
              alt={foto.descricao || foto.tipo}
              className="h-32 w-full object-cover"
            />
          </a>
          <div className="p-3 text-sm">
            <p className="font-black capitalize text-slate-900">{foto.tipo}</p>
            <p className="truncate text-slate-500">{foto.descricao || foto.url}</p>
            <button
              type="button"
              disabled={saving}
              onClick={() => onRemover(foto)}
              className="mt-2 text-xs font-bold uppercase tracking-[0.12em] text-rose-600 disabled:opacity-50"
            >
              Remover
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function Header({ eyebrow, title }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">{eyebrow}</p>
      <h3 className="mt-2 text-lg font-black text-slate-900">{title}</h3>
    </div>
  );
}

function SelectField({ label, value, onChange, children }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100">
        {children}
      </select>
    </label>
  );
}

function TextField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input type="text" value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100" />
    </label>
  );
}
