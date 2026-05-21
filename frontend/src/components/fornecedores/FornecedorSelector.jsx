import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Building2, ChevronDown, Plus, Search, X } from "lucide-react";
import { buscarClientes, criarCliente } from "../../api/clientes";
import ActionButton from "../ui/ActionButton";

export function getFornecedorNome(fornecedor) {
  return (
    fornecedor?.nome ||
    fornecedor?.razao_social ||
    fornecedor?.nome_fantasia ||
    fornecedor?.fantasia ||
    ""
  );
}

function getFornecedorMeta(fornecedor) {
  return [fornecedor?.cpf || fornecedor?.cnpj, fornecedor?.telefone || fornecedor?.celular]
    .filter(Boolean)
    .join(" - ");
}

function getGrupoFornecedorMeta(grupo) {
  const total = Array.isArray(grupo?.fornecedor_ids)
    ? grupo.fornecedor_ids.length
    : (Array.isArray(grupo?.fornecedores) ? grupo.fornecedores.length : 0);
  const partes = [];

  if (grupo?.fornecedor_principal_nome) {
    partes.push(`Principal: ${grupo.fornecedor_principal_nome}`);
  }

  if (total > 0) {
    partes.push(`${total} fornecedor${total === 1 ? "" : "es"}`);
  }

  return partes.join(" - ");
}

function mergeFornecedores(...listas) {
  const porId = new Map();
  listas.flat().forEach((fornecedor) => {
    if (!fornecedor?.id || porId.has(String(fornecedor.id))) return;
    porId.set(String(fornecedor.id), fornecedor);
  });
  return Array.from(porId.values());
}

function NovoFornecedorRapidoModal({
  nomeInicial,
  onClose,
  onCreated,
}) {
  const [formData, setFormData] = useState({
    nome: nomeInicial || "",
    cpf: "",
    cnpj: "",
    telefone: "",
    email: "",
  });
  const [tipoPessoa, setTipoPessoa] = useState("PF");
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    event.stopPropagation();
    const nome = formData.nome.trim();

    if (!nome) {
      setErro("Informe o nome do fornecedor.");
      return;
    }

    if (tipoPessoa === "PJ" && !formData.cnpj.trim()) {
      setErro("Informe o CNPJ para pessoa jurídica.");
      return;
    }

    setLoading(true);
    setErro("");

    try {
      const fornecedor = await criarCliente({
        tipo_cadastro: "fornecedor",
        tipo_pessoa: tipoPessoa,
        nome,
        razao_social: tipoPessoa === "PJ" ? nome : null,
        nome_fantasia: tipoPessoa === "PJ" ? nome : null,
        cpf: tipoPessoa === "PF" ? formData.cpf.trim() || null : null,
        cnpj: tipoPessoa === "PJ" ? formData.cnpj.trim() || null : null,
        telefone: formData.telefone || null,
        email: formData.email || null,
      });

      onCreated?.(fornecedor);
    } catch (error) {
      setErro(
        error.response?.data?.detail ||
          error.response?.data?.message ||
          "Erro ao cadastrar fornecedor.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Novo fornecedor
              </h3>
              <p className="text-xs text-slate-500">
                Cadastro rápido para continuar o fluxo.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-5">
          {erro ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {erro}
            </div>
          ) : null}

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Nome do fornecedor *
            </label>
            <input
              autoFocus
              type="text"
              value={formData.nome}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, nome: event.target.value }))
              }
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              Tipo de pessoa
            </label>
            <div className="grid grid-cols-2 gap-2 rounded-lg bg-slate-100 p-1">
              {[
                { value: "PF", label: "Pessoa Física" },
                { value: "PJ", label: "Pessoa Jurídica" },
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    setTipoPessoa(option.value);
                    setErro("");
                  }}
                  className={[
                    "rounded-md px-3 py-2 text-sm font-medium transition",
                    tipoPessoa === option.value
                      ? "bg-white text-emerald-700 shadow-sm"
                      : "text-slate-600 hover:bg-white/70",
                  ].join(" ")}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                {tipoPessoa === "PF" ? "CPF" : "CNPJ *"}
              </label>
              <input
                type="text"
                value={tipoPessoa === "PF" ? formData.cpf : formData.cnpj}
                onChange={(event) =>
                  setFormData((prev) => ({
                    ...prev,
                    [tipoPessoa === "PF" ? "cpf" : "cnpj"]: event.target.value,
                  }))
                }
                placeholder={tipoPessoa === "PF" ? "CPF do fornecedor" : "CNPJ do fornecedor"}
                className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Telefone
              </label>
              <input
                type="text"
                value={formData.telefone}
                onChange={(event) =>
                  setFormData((prev) => ({
                    ...prev,
                    telefone: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              E-mail
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, email: event.target.value }))
              }
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <ActionButton
              type="button"
              tone="soft"
              intent="neutral"
              onClick={onClose}
              disabled={loading}
            >
              Cancelar
            </ActionButton>
            <ActionButton
              type="submit"
              intent="create"
              icon={Plus}
              loading={loading}
            >
              Cadastrar
            </ActionButton>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function FornecedorSelector({
  allowCreate = true,
  className = "",
  disabled = false,
  fornecedores = [],
  gruposFornecedores = [],
  fornecedorId,
  fornecedorSelecionado,
  inputClassName = "",
  label = "Fornecedor",
  minChars = 2,
  onClear,
  onFornecedorCriado,
  onInputChange,
  onKeyDown,
  onSelect,
  onSelectGrupo,
  placeholder = "Digite o nome, CPF, CNPJ ou telefone...",
  required = false,
  searchRemote = true,
  showLabel = true,
  value,
}) {
  const containerRef = useRef(null);
  const fornecedorLocal = useMemo(
    () =>
      fornecedorSelecionado ||
      fornecedores.find((fornecedor) => String(fornecedor.id) === String(fornecedorId)) ||
      null,
    [fornecedorId, fornecedorSelecionado, fornecedores],
  );
  const nomeSelecionado = getFornecedorNome(fornecedorLocal);
  const [termo, setTermo] = useState(value ?? nomeSelecionado ?? "");
  const [sugestoesRemotas, setSugestoesRemotas] = useState([]);
  const [aberto, setAberto] = useState(false);
  const [buscando, setBuscando] = useState(false);
  const [modalNovoAberto, setModalNovoAberto] = useState(false);
  const portalRoot = typeof document !== "undefined" ? document.body : null;

  useEffect(() => {
    if (value !== undefined) {
      setTermo(value || "");
      return;
    }

    if (nomeSelecionado) {
      setTermo(nomeSelecionado);
    }
  }, [nomeSelecionado, value]);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (!containerRef.current?.contains(event.target)) {
        setAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  useEffect(() => {
    const consulta = termo.trim();
    if (disabled || !searchRemote || consulta.length < minChars) {
      setSugestoesRemotas([]);
      setBuscando(false);
      return undefined;
    }

    let cancelado = false;
    setBuscando(true);

    const timer = setTimeout(async () => {
      try {
        const resultado = await buscarClientes({
          tipo_cadastro: "fornecedor",
          search: consulta,
          limit: 20,
        });
        if (!cancelado) {
          setSugestoesRemotas(Array.isArray(resultado) ? resultado : []);
        }
      } catch {
        if (!cancelado) {
          setSugestoesRemotas([]);
        }
      } finally {
        if (!cancelado) {
          setBuscando(false);
        }
      }
    }, 220);

    return () => {
      cancelado = true;
      clearTimeout(timer);
    };
  }, [disabled, minChars, searchRemote, termo]);

  const sugestoesLocais = useMemo(() => {
    const consulta = termo.trim().toLocaleLowerCase("pt-BR");
    const base = fornecedores.slice(0, 80);
    if (!consulta) return base.slice(0, 20);

    return base
      .filter((fornecedor) => {
        const haystack = [
          fornecedor?.nome,
          fornecedor?.razao_social,
          fornecedor?.nome_fantasia,
          fornecedor?.cpf,
          fornecedor?.cnpj,
          fornecedor?.telefone,
          fornecedor?.celular,
        ]
          .filter(Boolean)
          .join(" ")
          .toLocaleLowerCase("pt-BR");
        return haystack.includes(consulta);
      })
      .slice(0, 20);
  }, [fornecedores, termo]);

  const sugestoesGrupos = useMemo(() => {
    if (!onSelectGrupo) return [];

    const consulta = termo.trim().toLocaleLowerCase("pt-BR");
    const base = gruposFornecedores
      .filter((grupo) => grupo?.id && grupo?.ativo !== false)
      .sort((a, b) => String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"));

    if (!consulta) {
      return base.slice(0, 8);
    }

    return base
      .filter((grupo) => {
        const fornecedoresGrupo = Array.isArray(grupo?.fornecedores)
          ? grupo.fornecedores
          : [];
        const haystack = [
          grupo?.nome,
          grupo?.descricao,
          grupo?.fornecedor_principal_nome,
          ...fornecedoresGrupo.flatMap((fornecedor) => [
            getFornecedorNome(fornecedor),
            fornecedor?.cnpj,
            fornecedor?.cpf,
          ]),
        ]
          .filter(Boolean)
          .join(" ")
          .toLocaleLowerCase("pt-BR");

        return haystack.includes(consulta);
      })
      .slice(0, 8);
  }, [gruposFornecedores, onSelectGrupo, termo]);

  const sugestoes = useMemo(
    () => mergeFornecedores(sugestoesRemotas, sugestoesLocais),
    [sugestoesLocais, sugestoesRemotas],
  );
  const termoLimpo = termo.trim();
  const existeExato = sugestoes.some(
    (fornecedor) =>
      getFornecedorNome(fornecedor).toLocaleLowerCase("pt-BR") ===
      termoLimpo.toLocaleLowerCase("pt-BR"),
  ) || sugestoesGrupos.some(
    (grupo) =>
      String(grupo?.nome || "").toLocaleLowerCase("pt-BR") ===
      termoLimpo.toLocaleLowerCase("pt-BR"),
  );
  const mostrarNovo = allowCreate && termoLimpo.length >= minChars && !existeExato;
  const mostrarSugestoes = aberto && !disabled && (
    sugestoesGrupos.length > 0 ||
    sugestoes.length > 0 ||
    mostrarNovo ||
    buscando
  );

  const selecionarFornecedor = (fornecedor) => {
    const nome = getFornecedorNome(fornecedor);
    setTermo(nome);
    setAberto(false);
    onInputChange?.(nome);
    onSelect?.(fornecedor);
  };

  const selecionarGrupo = (grupo) => {
    const nome = grupo?.nome || "";
    setTermo(nome);
    setAberto(false);
    onInputChange?.(nome);
    onSelectGrupo?.(grupo);
  };

  const limparFornecedor = () => {
    setTermo("");
    setAberto(false);
    setSugestoesRemotas([]);
    onInputChange?.("");
    onClear?.();
  };

  const handleChange = (novoTermo) => {
    setTermo(novoTermo);
    setAberto(true);
    onInputChange?.(novoTermo);
  };

  const handleFornecedorCriado = (fornecedor) => {
    setModalNovoAberto(false);
    selecionarFornecedor(fornecedor);
    onFornecedorCriado?.(fornecedor);
  };

  return (
    <div className={`relative ${className}`.trim()} ref={containerRef}>
      {showLabel ? (
        <label className="mb-1 block text-sm font-medium text-slate-700">
          {label}
          {required ? <span className="text-red-600"> *</span> : null}
        </label>
      ) : null}

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={termo}
          onChange={(event) => handleChange(event.target.value)}
          onFocus={() => setAberto(true)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          className={[
            "h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-24 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500",
            inputClassName,
          ]
            .filter(Boolean)
            .join(" ")}
          autoComplete="off"
        />

        <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
          {termo ? (
            <button
              type="button"
              onClick={limparFornecedor}
              disabled={disabled}
              className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
              title="Limpar fornecedor"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
          {allowCreate ? (
            <button
              type="button"
              onClick={() => setModalNovoAberto(true)}
              disabled={disabled}
              className="rounded-md p-1 text-emerald-600 transition hover:bg-emerald-50 hover:text-emerald-800 disabled:opacity-50"
              title="Novo fornecedor"
            >
              <Plus className="h-4 w-4" />
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => setAberto((prev) => !prev)}
            disabled={disabled}
            className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
            title="Abrir lista de fornecedores"
          >
            <ChevronDown className={`h-4 w-4 transition ${aberto ? "rotate-180" : ""}`} />
          </button>
        </div>
      </div>

      {mostrarSugestoes ? (
        <div className="absolute z-30 mt-2 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
          {buscando ? (
            <div className="px-4 py-3 text-sm text-slate-500">
              Buscando fornecedores...
            </div>
          ) : null}

          {sugestoesGrupos.map((grupo) => (
            <button
              key={`grupo-${grupo.id}`}
              type="button"
              onClick={() => selecionarGrupo(grupo)}
              className="w-full border-b border-emerald-100 bg-emerald-50/60 px-4 py-3 text-left last:border-b-0 hover:bg-emerald-50"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0 flex-1 truncate font-medium text-emerald-950">
                  Grupo: {grupo.nome}
                </div>
                <span className="shrink-0 rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-semibold text-emerald-700">
                  grupo
                </span>
              </div>
              {getGrupoFornecedorMeta(grupo) ? (
                <div className="mt-0.5 text-xs text-emerald-700">
                  {getGrupoFornecedorMeta(grupo)}
                </div>
              ) : null}
            </button>
          ))}

          {sugestoes.map((fornecedor) => (
            <button
              key={fornecedor.id}
              type="button"
              onClick={() => selecionarFornecedor(fornecedor)}
              className="w-full border-b border-slate-100 px-4 py-3 text-left last:border-b-0 hover:bg-slate-50"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0 flex-1 truncate font-medium text-slate-900">
                  {getFornecedorNome(fornecedor)}
                </div>
                {fornecedor.codigo ? (
                  <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-600">
                    #{fornecedor.codigo}
                  </span>
                ) : null}
              </div>
              {getFornecedorMeta(fornecedor) ? (
                <div className="mt-0.5 text-xs text-slate-500">
                  {getFornecedorMeta(fornecedor)}
                </div>
              ) : null}
            </button>
          ))}

          {mostrarNovo ? (
            <button
              type="button"
              onClick={() => setModalNovoAberto(true)}
              className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium text-emerald-700 hover:bg-emerald-50"
            >
              <Plus className="h-4 w-4" />
              Cadastrar "{termoLimpo}" como fornecedor
            </button>
          ) : null}
        </div>
      ) : null}

      {modalNovoAberto && portalRoot ? createPortal(
        <NovoFornecedorRapidoModal
          nomeInicial={termo}
          onClose={() => setModalNovoAberto(false)}
          onCreated={handleFornecedorCriado}
        />,
        portalRoot,
      ) : null}
    </div>
  );
}
