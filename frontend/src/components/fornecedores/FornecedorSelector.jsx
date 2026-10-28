import { normalizarBusca } from "../../utils/buscaEntidades";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Plus } from "lucide-react";
import BuscaPessoa from "../v2/BuscaPessoa/BuscaPessoa";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
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
  inputClassName: _inputClassName = "",
  label = "Fornecedor",
  minChars = 1,
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
    const consulta = normalizarBusca(termo);
    const base = fornecedores;
    if (!consulta) return base.slice(0, 20);

    return base
      .filter((fornecedor) => {
        const haystack = [
          fornecedor?.codigo,
          fornecedor?.nome,
          fornecedor?.razao_social,
          fornecedor?.nome_fantasia,
          fornecedor?.cpf,
          fornecedor?.cnpj,
          fornecedor?.telefone,
          fornecedor?.celular,
        ]
          .filter(Boolean)
          .join(" ");
        return consulta.split(" ").every((palavra) => normalizarBusca(haystack).includes(palavra));
      })
      .slice(0, 20);
  }, [fornecedores, termo]);

  const sugestoesGrupos = useMemo(() => {
    if (!onSelectGrupo) return [];

    const consulta = normalizarBusca(termo);
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
          .join(" ");

        return consulta.split(" ").every((palavra) => normalizarBusca(haystack).includes(palavra));
      })
      .slice(0, 8);
  }, [gruposFornecedores, onSelectGrupo, termo]);

  const sugestoes = useMemo(
    () => mergeFornecedores(sugestoesRemotas, sugestoesLocais),
    [sugestoesLocais, sugestoesRemotas],
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
      <BuscaPessoa
        value={termo}
        label={showLabel ? label : undefined}
        required={required}
        disabled={disabled}
        placeholder={placeholder}
        minChars={0}
        onChange={handleChange}
        onFocus={() => setAberto(true)}
        onKeyDown={onKeyDown}
        showSuggestions={aberto}
        loading={buscando}
        suggestions={[
          ...sugestoesGrupos.map((grupo) => ({
            id: `grupo-${grupo.id}`,
            nome: `Grupo: ${grupo.nome}`,
            _grupoFornecedor: grupo,
          })),
          ...sugestoes,
        ]}
        onSelect={(opcao) =>
          opcao._grupoFornecedor
            ? selecionarGrupo(opcao._grupoFornecedor)
            : selecionarFornecedor(opcao)
        }
      />
      <div className="mt-2 flex flex-wrap gap-2">
        {termo && (
          <BotaoCancelar tamanho="pequeno" onClick={limparFornecedor} disabled={disabled}>
            Limpar fornecedor
          </BotaoCancelar>
        )}
        {allowCreate && (
          <BotaoInteracao
            tamanho="pequeno"
            icon={Plus}
            onClick={() => setModalNovoAberto(true)}
            disabled={disabled}
          >
            Novo fornecedor
          </BotaoInteracao>
        )}
      </div>

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
