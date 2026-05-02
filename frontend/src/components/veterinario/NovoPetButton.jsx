import PropTypes from "prop-types";
import { Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { buildNovoPetPath } from "../../utils/petReturnFlow";
import { actionButtonClasses } from "../ui/actionStyles";

export default function NovoPetButton({
  tutorId,
  tutorNome,
  returnTo,
  onBeforeNavigate,
  onClick,
  label = "Novo pet",
  className = "",
}) {
  const navigate = useNavigate();
  const disabled = !tutorId;

  function handleClick() {
    if (disabled) {
      return;
    }
    if (typeof onClick === "function") {
      onClick();
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
      className={actionButtonClasses({
        intent: "create",
        tone: "soft",
        size: "xs",
        className,
      })}
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
  onClick: PropTypes.func,
  label: PropTypes.string,
  className: PropTypes.string,
};
