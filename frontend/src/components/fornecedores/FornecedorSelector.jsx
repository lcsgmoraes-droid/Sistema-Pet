import { useEffect, useMemo, useRef, useState } from "react";
import { Building2, Plus, Search, X } from "lucide-react";
import { buscarClientes, criarCliente } from "../../api/clientes";
import ActionButton from "../ui/ActionButton";

function getFornecedorNome(fornecedor) {
  return (
    fornecedor?.nome ||
    fornecedor?.razao_social ||
    fornecedor?.nome_fantasia ||
    fornecedor?.fantasia ||
    ""
  );
}

function getFornecedorMeta(fornecedor) {
  return [fornecedor?.cnpj, fornecedor?.telefone || fornecedor?.celular]
    .filter(Boolean)
    .join(" - ");
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
    cnpj: "",
    telefone: "",
    email: "",
  });
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nome = formData.nome.trim();

    if (!nome) {
      setErro("Informe o nome do fornecedor.");
      return;
    }

    setLoading(true);
    setErro("");

    try {
      const fornecedor = await criarCliente({
        tipo_cadastro: "fornecedor",
        tipo_pessoa: "PJ",
        nome,
        razao_social: nome,
        nome_fantasia: nome,
        cnpj: formData.cnpj || null,
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
                Cadastro rapido para continuar o fluxo.
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

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                CNPJ
              </label>
              <input
                type="text"
                value={formData.cnpj}
                onChange={(event) =>
                  setFormData((prev) => ({ ...prev, cnpj: event.target.value }))
                }
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
  fornecedorId,
  fornecedorSelecionado,
  inputClassName = "",
  label = "Fornecedor",
  minChars = 2,
  onClear,
  onFornecedorCriado,
  onInputChange,
  onSelect,
  placeholder = "Digite o nome, CNPJ ou telefone...",
  required = false,
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
    if (disabled || consulta.length < minChars) {
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
  }, [disabled, minChars, termo]);

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

  const sugestoes = useMemo(
    () => mergeFornecedores(sugestoesRemotas, sugestoesLocais),
    [sugestoesLocais, sugestoesRemotas],
  );
  const termoLimpo = termo.trim();
  const existeExato = sugestoes.some(
    (fornecedor) =>
      getFornecedorNome(fornecedor).toLocaleLowerCase("pt-BR") ===
      termoLimpo.toLocaleLowerCase("pt-BR"),
  );
  const mostrarNovo = allowCreate && termoLimpo.length >= minChars && !existeExato;
  const mostrarSugestoes = aberto && !disabled && (sugestoes.length > 0 || mostrarNovo || buscando);

  const selecionarFornecedor = (fornecedor) => {
    const nome = getFornecedorNome(fornecedor);
    setTermo(nome);
    setAberto(false);
    onInputChange?.(nome);
    onSelect?.(fornecedor);
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
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          className={[
            "h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-20 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500",
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
        </div>
      </div>

      {mostrarSugestoes ? (
        <div className="absolute z-30 mt-2 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
          {buscando ? (
            <div className="px-4 py-3 text-sm text-slate-500">
              Buscando fornecedores...
            </div>
          ) : null}

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

      {modalNovoAberto ? (
        <NovoFornecedorRapidoModal
          nomeInicial={termo}
          onClose={() => setModalNovoAberto(false)}
          onCreated={handleFornecedorCriado}
        />
      ) : null}
    </div>
  );
}
