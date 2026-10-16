import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Plus, Search, X } from "lucide-react";
import { buscarClientes } from "../../api/clientes";
import PessoaFormularioModal from "../clientes/PessoaFormularioModal";

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
    : Array.isArray(grupo?.fornecedores)
      ? grupo.fornecedores.length
      : 0;
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

// Wrapper fino em cima da modal única de Pessoa — cadastro rápido de fornecedor a
// partir do combobox usa o mesmo formulário/modal do resto do sistema, pré-marcado
// como fornecedor com o termo buscado já no nome.
function NovoFornecedorRapidoModal({ nomeInicial, onClose, onCreated }) {
  return (
    <PessoaFormularioModal
      onFechar={onClose}
      onSalvo={onCreated}
      prefill={{ is_fornecedor: true, nome: nomeInicial || "" }}
    />
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
          is_fornecedor: true,
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
        const fornecedoresGrupo = Array.isArray(grupo?.fornecedores) ? grupo.fornecedores : [];
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
  const existeExato =
    sugestoes.some(
      (fornecedor) =>
        getFornecedorNome(fornecedor).toLocaleLowerCase("pt-BR") ===
        termoLimpo.toLocaleLowerCase("pt-BR"),
    ) ||
    sugestoesGrupos.some(
      (grupo) =>
        String(grupo?.nome || "").toLocaleLowerCase("pt-BR") ===
        termoLimpo.toLocaleLowerCase("pt-BR"),
    );
  const mostrarNovo = allowCreate && termoLimpo.length >= minChars && !existeExato;
  const mostrarSugestoes =
    aberto &&
    !disabled &&
    (sugestoesGrupos.length > 0 || sugestoes.length > 0 || mostrarNovo || buscando);

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
            <div className="px-4 py-3 text-sm text-slate-500">Buscando fornecedores...</div>
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
                <div className="mt-0.5 text-xs text-slate-500">{getFornecedorMeta(fornecedor)}</div>
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

      {modalNovoAberto && portalRoot
        ? createPortal(
            <NovoFornecedorRapidoModal
              nomeInicial={termo}
              onClose={() => setModalNovoAberto(false)}
              onCreated={handleFornecedorCriado}
            />,
            portalRoot,
          )
        : null}
    </div>
  );
}
