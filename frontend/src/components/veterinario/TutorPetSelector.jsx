import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import TutorAutocomplete from "../TutorAutocomplete";
import PetSelector from "../pets/PetSelector";

export default function TutorPetSelector({
  tutorSelecionado,
  petId,
  pets,
  expanded: expandedProp,
  loadingPets = false,
  disabled = false,
  disabledTutor = false,
  disabledPet = false,
  showTutorField = true,
  showPetLabel = true,
  autoExpandOnTutorChange = true,
  tutorLabel = "Tutor",
  petLabel = "Pet",
  tutorInputId,
  tutorPlaceholder = "Digite nome, CPF ou telefone do tutor...",
  returnTo,
  className = "",
  onSelectTutor,
  onSelectPet,
  onExpandedChange,
  onBeforeNovoPet,
  onNovoPetClick,
}) {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const listaPets = Array.isArray(pets) ? pets : [];
  const tutorId = tutorSelecionado?.id;
  const isExpandedControlled = typeof expandedProp === "boolean";
  const expanded = isExpandedControlled ? expandedProp : internalExpanded;

  function setExpandedValue(valueOrUpdater) {
    const nextValue =
      typeof valueOrUpdater === "function" ? valueOrUpdater(expanded) : valueOrUpdater;

    if (isExpandedControlled) {
      onExpandedChange?.(nextValue);
      return;
    }
    setInternalExpanded(nextValue);
  }

  useEffect(() => {
    if (!tutorId) {
      setExpandedValue(false);
      return;
    }

    if (autoExpandOnTutorChange && !disabled && !disabledPet) {
      setExpandedValue(true);
    }
  }, [autoExpandOnTutorChange, disabled, disabledPet, tutorId]);

  function handleSelectTutor(tutor) {
    onSelectTutor?.(tutor);
    if (!tutor?.id) {
      onSelectPet?.("");
      setExpandedValue(false);
      return;
    }
    setExpandedValue(true);
  }

  function handleSelectPet(pet) {
    onSelectPet?.(pet ? String(pet.id) : "");
    setExpandedValue(false);
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {showTutorField ? (
        <TutorAutocomplete
          label={tutorLabel}
          inputId={tutorInputId}
          selectedTutor={tutorSelecionado}
          onSelect={handleSelectTutor}
          placeholder={tutorPlaceholder}
          disabled={disabled || disabledTutor}
        />
      ) : null}

      <PetSelector
        tutorSelecionado={tutorSelecionado}
        petId={petId}
        pets={listaPets}
        expanded={expanded}
        loadingPets={loadingPets}
        disabled={disabled || disabledPet}
        showPetLabel={showPetLabel}
        petLabel={petLabel}
        returnTo={returnTo}
        onSelectPet={handleSelectPet}
        onExpandedChange={setExpandedValue}
        onBeforeNovoPet={onBeforeNovoPet}
        onNovoPetClick={onNovoPetClick}
      />
    </div>
  );
}

TutorPetSelector.propTypes = {
  tutorSelecionado: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    nome: PropTypes.string,
  }),
  petId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  pets: PropTypes.arrayOf(PropTypes.object),
  expanded: PropTypes.bool,
  loadingPets: PropTypes.bool,
  disabled: PropTypes.bool,
  disabledTutor: PropTypes.bool,
  disabledPet: PropTypes.bool,
  showTutorField: PropTypes.bool,
  showPetLabel: PropTypes.bool,
  autoExpandOnTutorChange: PropTypes.bool,
  tutorLabel: PropTypes.string,
  petLabel: PropTypes.string,
  tutorInputId: PropTypes.string,
  tutorPlaceholder: PropTypes.string,
  returnTo: PropTypes.string,
  className: PropTypes.string,
  onSelectTutor: PropTypes.func,
  onSelectPet: PropTypes.func,
  onExpandedChange: PropTypes.func,
  onBeforeNovoPet: PropTypes.func,
  onNovoPetClick: PropTypes.func,
};
