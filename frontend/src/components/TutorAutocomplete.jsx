import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Search } from "lucide-react";
import { buscarClientes } from "../api/clientes";

function buscarClienteExato(termo, clientes) {
  const termoLimpo = String(termo || "").trim().toLowerCase();
  if (!termoLimpo) return null;

  return clientes.find((cliente) => {
    const id = String(cliente?.id || "").trim().toLowerCase();
    const codigo = String(cliente?.codigo || "").trim().toLowerCase();
    const nome = String(cliente?.nome || "").trim().toLowerCase();
    const cpf = String(cliente?.cpf || "").trim().toLowerCase();
    const telefone = String(cliente?.telefone || "").trim().toLowerCase();
    return [id, codigo, nome, cpf, telefone].includes(termoLimpo);
  }) || null;
}

export default function TutorAutocomplete({
  label,
  placeholder = "Digite nome, CPF ou telefone do tutor...",
  selectedTutor,
  onSelect,
  disabled = false,
  inputId,
}) {
  const [busca, setBusca] = useState("");
  const [sugestoes, setSugestoes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [focado, setFocado] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    setBusca(selectedTutor?.nome || "");
  }, [selectedTutor?.id, selectedTutor?.nome]);

  useEffect(() => {
    if (disabled) {
      setSugestoes([]);
      setLoading(false);
      return;
    }

    if (busca.trim().length < 1) {
      setSugestoes([]);
      setLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const termoOriginal = busca.trim();
        const termoDigitos = Array.from(termoOriginal).filter((char) => /\d/.test(char)).join("");
        const termoBusca = termoDigitos.length >= 8 ? termoDigitos : termoOriginal;
        const clientes = await buscarClientes({ search: termoBusca, limit: 20 });
        setSugestoes(Array.isArray(clientes) ? clientes : []);
      } catch {
        setSugestoes([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [busca, disabled]);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (!containerRef.current?.contains(event.target)) {
        setFocado(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  const mostrarSugestoes = focado && !disabled && busca.trim().length >= 1;
  let conteudoSugestoes = null;

  if (loading) {
    conteudoSugestoes = <div className="px-4 py-3 text-sm text-gray-500">Buscando tutores...</div>;
  } else if (sugestoes.length > 0) {
    conteudoSugestoes = sugestoes.map((cliente) => (
      <button
        key={cliente.id}
        type="button"
        onClick={() => {
          onSelect(cliente);
          setBusca(cliente.nome || "");
          setFocado(false);
          setSugestoes([]);
        }}
        className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b last:border-b-0"
      >
        <div className="flex items-center justify-between gap-2">
          <div className="font-medium text-gray-900 flex-1">{cliente.nome}</div>
          {cliente.codigo ? (
            <div className="text-xs font-mono bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded flex-shrink-0">
              #{cliente.codigo}
            </div>
          ) : null}
        </div>
        <div className="text-sm text-gray-500">
          {cliente.cpf ? `CPF: ${cliente.cpf}` : "Sem CPF"}
          {cliente.telefone ? ` • ${cliente.telefone}` : ""}
        </div>
        {cliente.pets?.length ? (
          <div className="text-xs text-blue-600 mt-1">{cliente.pets.length} pet(s)</div>
        ) : null}
      </button>
    ));
  } else {
    conteudoSugestoes = <div className="px-4 py-3 text-sm text-gray-500">Nenhum tutor encontrado</div>;
  }

  return (
    <div ref={containerRef} className="relative">
      {label ? <label htmlFor={inputId} className="block text-xs font-medium text-gray-600 mb-1">{label}</label> : null}
      <div className="relative">
        <input
          id={inputId}
          type="text"
          value={busca}
          onFocus={() => setFocado(true)}
          onChange={(e) => {
            const valor = e.target.value;
            setBusca(valor);
            if (selectedTutor && valor !== selectedTutor.nome) {
              onSelect(null);
            }
          }}
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;
            const clienteExato = buscarClienteExato(busca, sugestoes);
            if (!clienteExato) return;
            e.preventDefault();
            onSelect(clienteExato);
            setBusca(clienteExato.nome || "");
            setFocado(false);
            setSugestoes([]);
          }}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 pl-10 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 disabled:bg-gray-100 disabled:text-gray-400"
          disabled={disabled}
          autoComplete="off"
        />
        <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
      </div>

      {mostrarSugestoes && (
        <div className="absolute z-20 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {conteudoSugestoes}
        </div>
      )}
    </div>
  );
}

TutorAutocomplete.propTypes = {
  label: PropTypes.string,
  placeholder: PropTypes.string,
  selectedTutor: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    nome: PropTypes.string,
  }),
  onSelect: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  inputId: PropTypes.string,
};