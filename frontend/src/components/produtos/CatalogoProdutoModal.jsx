import { AlertCircle, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";

import {
  createCategoria,
  createDepartamento,
  createMarca,
  updateCategoria,
  updateDepartamento,
  updateMarca,
} from "../../api/produtos";
import ActionButton from "../ui/ActionButton";

const CONFIGS = {
  marca: {
    singular: "marca",
    tituloNovo: "Nova Marca",
    tituloEditar: "Editar Marca",
    placeholder: "Ex: Royal Canin, Premier, Zee.Dog...",
    create: createMarca,
    update: updateMarca,
  },
  departamento: {
    singular: "departamento",
    tituloNovo: "Novo Departamento",
    tituloEditar: "Editar Departamento",
    placeholder: "Ex: Alimentacao, Higiene, Acessorios...",
    create: createDepartamento,
    update: updateDepartamento,
  },
  categoria: {
    singular: "categoria",
    tituloNovo: "Nova Categoria",
    tituloEditar: "Editar Categoria",
    placeholder: "Ex: Racoes, Brinquedos, Medicamentos...",
    create: createCategoria,
    update: updateCategoria,
  },
};

function montarEstadoInicial(tipo, item, initialValues) {
  const base = {
    nome: item?.nome || initialValues?.nome || "",
    descricao: item?.descricao || initialValues?.descricao || "",
  };

  if (tipo !== "categoria") return base;

  return {
    ...base,
    categoria_pai_id: item?.categoria_pai_id ?? initialValues?.categoria_pai_id ?? null,
    departamento_id: item?.departamento_id ?? initialValues?.departamento_id ?? null,
    ordem: item?.ordem ?? initialValues?.ordem ?? 0,
  };
}

function adicionarOuAtualizar(lista, item) {
  const semDuplicado = lista.filter((atual) => String(atual.id) !== String(item.id));
  return [...semDuplicado, item].sort((a, b) =>
    String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"),
  );
}

function obterMensagemErro(error, config) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const mensagens = detail.map((item) => item?.msg).filter(Boolean);
    if (mensagens.length) return mensagens.join(" ");
  }
  return `Nao foi possivel salvar a ${config.singular}. Tente novamente.`;
}

export default function CatalogoProdutoModal({
  departamentos = [],
  initialValues = {},
  item = null,
  onClose,
  onDepartamentoCriado,
  onSaved,
  tipo,
  zIndexClass = "z-50",
}) {
  const config = CONFIGS[tipo];
  const [formData, setFormData] = useState(() => montarEstadoInicial(tipo, item, initialValues));
  const [departamentosLocais, setDepartamentosLocais] = useState(departamentos);
  const [modalDepartamentoAberto, setModalDepartamentoAberto] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    setDepartamentosLocais(departamentos);
  }, [departamentos]);

  if (!config) return null;

  const isEditando = Boolean(item?.id);
  const isSubcategoria = tipo === "categoria" && Boolean(formData.categoria_pai_id);
  const titulo = isEditando
    ? config.tituloEditar
    : isSubcategoria
      ? "Nova Subcategoria"
      : config.tituloNovo;

  const fechar = () => {
    if (!salvando) onClose?.();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    event.stopPropagation();
    setErro("");

    const nome = formData.nome.trim();
    if (!nome) {
      setErro("Informe o nome antes de salvar.");
      return;
    }

    const payload =
      tipo === "categoria"
        ? {
            nome,
            descricao: formData.descricao.trim() || null,
            categoria_pai_id: formData.categoria_pai_id || null,
            departamento_id: formData.departamento_id || null,
            ordem: Number(formData.ordem) || 0,
          }
        : {
            nome,
            descricao: formData.descricao.trim() || null,
          };

    try {
      setSalvando(true);
      const response = isEditando
        ? await config.update(item.id, payload)
        : await config.create(payload);

      sessionStorage.removeItem("produtos_catalogos_cache_v1");
      await onSaved?.(response.data);
      onClose?.();
    } catch (error) {
      console.error(`Erro ao salvar ${config.singular}:`, error);
      setErro(obterMensagemErro(error, config));
    } finally {
      setSalvando(false);
    }
  };

  const handleDepartamentoCriado = async (departamento) => {
    setDepartamentosLocais((atuais) => adicionarOuAtualizar(atuais, departamento));
    setFormData((atual) => ({ ...atual, departamento_id: departamento.id }));
    await onDepartamentoCriado?.(departamento);
  };

  return (
    <>
      <div
        className={`fixed inset-0 ${zIndexClass} flex items-center justify-center bg-black/50 p-4`}
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) fechar();
        }}
      >
        <div
          className="w-full max-w-md rounded-xl bg-white shadow-2xl dark:bg-slate-900"
          role="dialog"
          aria-modal="true"
          aria-labelledby={`catalogo-modal-${tipo}-titulo`}
        >
          <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5 dark:border-slate-700">
            <div>
              <h2
                id={`catalogo-modal-${tipo}-titulo`}
                className="text-xl font-bold text-slate-900 dark:text-slate-100"
              >
                {titulo}
              </h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Salve aqui e continue o cadastro sem trocar de tela.
              </p>
            </div>
            <button
              type="button"
              onClick={fechar}
              disabled={salvando}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50 dark:hover:bg-slate-800 dark:hover:text-slate-200"
              title="Fechar"
              aria-label="Fechar modal"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 p-6">
            {erro ? (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{erro}</span>
              </div>
            ) : null}

            <div>
              <label
                htmlFor={`catalogo-${tipo}-nome`}
                className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Nome *
              </label>
              <input
                id={`catalogo-${tipo}-nome`}
                type="text"
                value={formData.nome}
                onChange={(event) =>
                  setFormData((atual) => ({ ...atual, nome: event.target.value }))
                }
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus:ring-cyan-400"
                placeholder={config.placeholder}
                autoFocus
                required
                disabled={salvando}
              />
            </div>

            {tipo === "categoria" ? (
              <div>
                <div className="mb-1 flex items-center justify-between gap-2">
                  <label
                    htmlFor="catalogo-categoria-departamento"
                    className="block text-sm font-medium text-slate-700 dark:text-slate-300"
                  >
                    Departamento
                  </label>
                  <button
                    type="button"
                    onClick={() => setModalDepartamentoAberto(true)}
                    disabled={salvando}
                    className="inline-flex h-7 items-center gap-1 rounded-md border border-emerald-200 bg-white px-2 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-50 disabled:opacity-50 dark:border-emerald-800 dark:bg-slate-900 dark:text-emerald-300 dark:hover:bg-emerald-950/40"
                    title="Cadastrar departamento"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Novo
                  </button>
                </div>
                <select
                  id="catalogo-categoria-departamento"
                  value={formData.departamento_id || ""}
                  onChange={(event) =>
                    setFormData((atual) => ({
                      ...atual,
                      departamento_id: event.target.value ? Number(event.target.value) : null,
                    }))
                  }
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus:ring-cyan-400"
                  disabled={salvando}
                >
                  <option value="">Sem departamento</option>
                  {departamentosLocais.map((departamento) => (
                    <option key={departamento.id} value={departamento.id}>
                      {departamento.nome}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}

            <div>
              <label
                htmlFor={`catalogo-${tipo}-descricao`}
                className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Descricao
              </label>
              <textarea
                id={`catalogo-${tipo}-descricao`}
                value={formData.descricao}
                onChange={(event) =>
                  setFormData((atual) => ({ ...atual, descricao: event.target.value }))
                }
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus:ring-cyan-400"
                placeholder={`Descricao opcional da ${config.singular}`}
                rows={3}
                disabled={salvando}
              />
            </div>

            {tipo === "categoria" ? (
              <>
                <div>
                  <label
                    htmlFor="catalogo-categoria-ordem"
                    className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
                  >
                    Ordem
                  </label>
                  <input
                    id="catalogo-categoria-ordem"
                    type="number"
                    min="0"
                    value={formData.ordem}
                    onChange={(event) =>
                      setFormData((atual) => ({ ...atual, ordem: event.target.value }))
                    }
                    className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus:ring-cyan-400"
                    disabled={salvando}
                  />
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Menor valor aparece primeiro.
                  </p>
                </div>

                {isSubcategoria ? (
                  <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-200">
                    Esta sera uma subcategoria.
                  </div>
                ) : null}
              </>
            ) : null}

            <div className="flex justify-end gap-3 border-t border-slate-200 pt-4 dark:border-slate-700">
              <ActionButton
                type="button"
                onClick={fechar}
                intent="neutral"
                tone="soft"
                disabled={salvando}
              >
                Cancelar
              </ActionButton>
              <ActionButton
                type="submit"
                intent={isEditando ? "edit" : "create"}
                loading={salvando}
              >
                {isEditando ? "Salvar" : "Criar"}
              </ActionButton>
            </div>
          </form>
        </div>
      </div>

      {modalDepartamentoAberto ? (
        <CatalogoProdutoModal
          tipo="departamento"
          onClose={() => setModalDepartamentoAberto(false)}
          onSaved={handleDepartamentoCriado}
          zIndexClass="z-[60]"
        />
      ) : null}
    </>
  );
}
