import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import TutorAutocomplete from "../TutorAutocomplete";
import NovoPetButton from "./NovoPetButton";

function normalizeText(value) {
  return String(value || "").trim();
}

function petDescription(pet) {
  const especie = normalizeText(pet?.especie);
  const codigo = normalizeText(pet?.codigo);
  const partes = [];

  if (especie && !/\?/.test(especie)) {
    partes.push(especie);
  }
  if (codigo) {
    partes.push(codigo);
  }

  return partes.length ? partes.join(" - ") : "Pet";
}

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

  const petSelecionado = useMemo(
    () => listaPets.find((pet) => String(pet.id) === String(petId)) || null,
    [listaPets, petId]
  );

  const canSelectPet = Boolean(tutorId) && !loadingPets && !disabled && !disabledPet;

  function setExpandedValue(valueOrUpdater) {
    const nextValue =
      typeof valueOrUpdater === "function"
        ? valueOrUpdater(expanded)
        : valueOrUpdater;

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
    onSelectPet?.(String(pet.id));
    setExpandedValue(false);
  }

  function resolvePetLabel() {
    if (!tutorId) return "Selecione o tutor primeiro";
    if (loadingPets) return "Carregando pets...";
    if (petSelecionado) return petSelecionado.nome;
    return "Selecione o pet";
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

      <div className="block">
        {showPetLabel ? (
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
            {petLabel}
          </span>
        ) : null}
        <div className="mt-1 overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center gap-3 border-b border-slate-100 px-3 py-2">
            <button
              type="button"
              onClick={() => canSelectPet && setExpandedValue((prev) => !prev)}
              disabled={!canSelectPet}
              className="min-w-0 flex-1 text-left text-sm text-slate-900 disabled:text-slate-400"
            >
              <span className="block truncate font-semibold">{resolvePetLabel()}</span>
              {petSelecionado ? (
                <span className="block truncate text-xs font-normal text-slate-500">
                  {petDescription(petSelecionado)}
                </span>
              ) : null}
            </button>

            <NovoPetButton
              tutorId={tutorId}
              tutorNome={tutorSelecionado?.nome}
              returnTo={returnTo}
              onBeforeNavigate={onBeforeNovoPet}
              onClick={onNovoPetClick}
            />

            <span className="whitespace-nowrap text-xs text-slate-500">
              {tutorId ? `${listaPets.length} pet(s)` : "Sem tutor"}
            </span>
          </div>

          {expanded && tutorId && !loadingPets ? (
            <div className="max-h-52 overflow-y-auto p-2">
              {listaPets.length > 0 ? (
                <div className="space-y-1">
                  {listaPets.map((pet) => {
                    const active = String(petId) === String(pet.id);
                    return (
                      <button
                        key={pet.id}
                        type="button"
                        onClick={() => handleSelectPet(pet)}
                        className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                          active
                            ? "border border-cyan-200 bg-cyan-50 text-cyan-800"
                            : "border border-transparent text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        <span className="block font-semibold">{pet.nome}</span>
                        <span className="block text-xs text-slate-500">
                          {petDescription(pet)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <p className="px-2 py-3 text-xs text-amber-600">
                  Nenhum pet ativo vinculado a esse tutor.
                </p>
              )}
            </div>
          ) : null}
        </div>
      </div>
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
