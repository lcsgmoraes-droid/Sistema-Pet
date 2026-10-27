import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { buscarClientes } from "../api/clientes";
import BuscaPessoa from "./v2/BuscaPessoa/BuscaPessoa";

// Adaptador dos formularios de tutor para a mesma celula de pessoas do PDV.
export default function TutorAutocomplete({
  label,
  placeholder = "Código, nome, CPF ou telefone do tutor...",
  selectedTutor,
  onSelect,
  disabled = false,
  inputId,
}) {
  const [busca, setBusca] = useState(selectedTutor?.nome || "");
  const [sugestoes, setSugestoes] = useState([]);
  const [loading, setLoading] = useState(false);
  const digitando = useRef(false);

  useEffect(() => {
    if (!digitando.current) setBusca(selectedTutor?.nome || "");
    digitando.current = false;
  }, [selectedTutor?.id, selectedTutor?.nome]);

  useEffect(() => {
    let ativo = true;
    const termo = busca.trim();
    if (disabled || !termo || (selectedTutor && busca === selectedTutor.nome)) {
      setSugestoes([]);
      setLoading(false);
      return undefined;
    }
    setSugestoes([]);
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const clientes = await buscarClientes({ search: termo, limit: 20 });
        if (ativo) setSugestoes(Array.isArray(clientes) ? clientes : []);
      } catch {
        if (ativo) setSugestoes([]);
      } finally {
        if (ativo) setLoading(false);
      }
    }, 220);
    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [busca, disabled, selectedTutor]);

  return (
    <BuscaPessoa
      inputId={inputId}
      label={label}
      placeholder={placeholder}
      value={busca}
      disabled={disabled}
      loading={loading}
      suggestions={sugestoes}
      showSuggestions={!selectedTutor}
      onChange={(valor) => {
        setBusca(valor);
        if (selectedTutor && valor !== selectedTutor.nome) {
          digitando.current = true;
          onSelect(null);
        }
      }}
      onSelect={(tutor) => {
        setBusca(tutor.nome || "");
        setSugestoes([]);
        onSelect(tutor);
      }}
    />
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
