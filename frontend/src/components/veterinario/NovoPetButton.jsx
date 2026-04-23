import PropTypes from "prop-types";
import { Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { buildNovoPetPath } from "../../utils/petReturnFlow";

export default function NovoPetButton({
  tutorId,
  tutorNome,
  returnTo,
  onBeforeNavigate,
  label = "Novo pet",
  className = "",
}) {
  const navigate = useNavigate();
  const disabled = !tutorId;

  function handleClick() {
    if (disabled) {
      return;
    }
    onBeforeNavigate?.();
    navigate(
      buildNovoPetPath({
        tutorId,
        tutorNome,
        returnTo,
      })
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      title={disabled ? "Selecione o tutor primeiro" : "Cadastrar um novo pet para este tutor"}
      className={`inline-flex items-center gap-1 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-xs font-medium text-cyan-700 transition-colors hover:bg-cyan-100 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400 ${className}`}
    >
      <Plus size={13} />
      {label}
    </button>
  );
}

NovoPetButton.propTypes = {
  tutorId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  tutorNome: PropTypes.string,
  returnTo: PropTypes.string,
  onBeforeNavigate: PropTypes.func,
  label: PropTypes.string,
  className: PropTypes.string,
};
