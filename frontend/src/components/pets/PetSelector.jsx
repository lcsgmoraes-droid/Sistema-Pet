import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import NovoPetButton from "./NovoPetButton";
import NovoPetModal from "./NovoPetModal";

function normalizeText(value) {
  return String(value || "").trim();
}

export function describePet(pet) {
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

export default function PetSelector({
  tutorSelecionado,
  tutorId: tutorIdProp,
  tutorNome,
  petId,
  pets,
  expanded: expandedProp,
  loadingPets = false,
  disabled = false,
  showPetLabel = true,
  showNovoPetButton = true,
  allowEmpty = false,
  petLabel = "Pet",
  placeholder = "Selecione o pet",
  emptyOptionLabel = "Sem pet especifico",
  emptyStateLabel = "Nenhum pet ativo vinculado a esse tutor.",
  returnTo,
  sugestoesEspecies = [],
  className = "",
  onSelectPet,
  onPetCreated,
  onExpandedChange,
  onBeforeNovoPet,
  onNovoPetClick,
}) {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const [modalNovoPetAberto, setModalNovoPetAberto] = useState(false);
  const [petCriadoLocal, setPetCriadoLocal] = useState(null);
  const listaPetsOriginal = Array.isArray(pets) ? pets : [];
  const tutorId = tutorIdProp || tutorSelecionado?.id;
  const isExpandedControlled = typeof expandedProp === "boolean";
  const expanded = isExpandedControlled ? expandedProp : internalExpanded;
  const tutorParaModal = useMemo(
    () => ({
      ...(tutorSelecionado || {}),
      id: tutorId,
      nome: tutorNome || tutorSelecionado?.nome,
    }),
    [tutorId, tutorNome, tutorSelecionado],
  );

  useEffect(() => {
    setPetCriadoLocal(null);
  }, [tutorId]);

  const listaPets = useMemo(() => {
    if (!petCriadoLocal?.id) return listaPetsOriginal;

    const petTutorId = petCriadoLocal.cliente_id || petCriadoLocal.tutor_id || tutorId;
    if (String(petTutorId) !== String(tutorId)) return listaPetsOriginal;

    const jaExiste = listaPetsOriginal.some((pet) => String(pet.id) === String(petCriadoLocal.id));
    if (jaExiste) return listaPetsOriginal;

    return [petCriadoLocal, ...listaPetsOriginal];
  }, [listaPetsOriginal, petCriadoLocal, tutorId]);

  const petSelecionado = useMemo(
    () => listaPets.find((pet) => String(pet.id) === String(petId)) || null,
    [listaPets, petId],
  );

  const canSelectPet = Boolean(tutorId) && !loadingPets && !disabled;

  function setExpandedValue(valueOrUpdater) {
    const nextValue =
      typeof valueOrUpdater === "function" ? valueOrUpdater(expanded) : valueOrUpdater;

    if (isExpandedControlled) {
      onExpandedChange?.(nextValue);
      return;
    }
    setInternalExpanded(nextValue);
    onExpandedChange?.(nextValue);
  }

  function handleSelectPet(pet) {
    onSelectPet?.(pet);
    setExpandedValue(false);
  }

  function handleNovoPetClick() {
    if (typeof onNovoPetClick === "function") {
      onNovoPetClick();
      return;
    }
    setModalNovoPetAberto(true);
  }

  function handlePetCreated(pet) {
    setPetCriadoLocal(pet);
    onPetCreated?.(pet);
    handleSelectPet(pet);
    setModalNovoPetAberto(false);
  }

  function resolvePetLabel() {
    if (!tutorId) return "Selecione o tutor primeiro";
    if (loadingPets) return "Carregando pets...";
    if (petSelecionado) return petSelecionado.nome;
    return placeholder;
  }

  return (
    <div className={`block ${className}`}>
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
                {describePet(petSelecionado)}
              </span>
            ) : null}
          </button>

          {showNovoPetButton ? (
            <NovoPetButton
              tutorId={tutorId}
              tutorNome={tutorNome || tutorSelecionado?.nome}
              returnTo={returnTo}
              onBeforeNavigate={onBeforeNovoPet}
              onClick={handleNovoPetClick}
            />
          ) : null}

          <span className="whitespace-nowrap text-xs text-slate-500">
            {tutorId ? `${listaPets.length} pet(s)` : "Sem tutor"}
          </span>
        </div>

        {expanded && tutorId && !loadingPets ? (
          <div className="max-h-52 overflow-y-auto p-2">
            {allowEmpty ? (
              <button
                type="button"
                onClick={() => handleSelectPet(null)}
                className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                  !petSelecionado
                    ? "border border-cyan-200 bg-cyan-50 text-cyan-800"
                    : "border border-transparent text-slate-700 hover:bg-slate-50"
                }`}
              >
                <span className="block font-semibold">{emptyOptionLabel}</span>
              </button>
            ) : null}

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
                      <span className="block text-xs text-slate-500">{describePet(pet)}</span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="px-2 py-3 text-xs text-amber-600">{emptyStateLabel}</p>
            )}
          </div>
        ) : null}
      </div>

      <NovoPetModal
        isOpen={modalNovoPetAberto}
        tutor={tutorParaModal}
        sugestoesEspecies={sugestoesEspecies}
        onClose={() => setModalNovoPetAberto(false)}
        onCreated={handlePetCreated}
      />
    </div>
  );
}

PetSelector.propTypes = {
  tutorSelecionado: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    nome: PropTypes.string,
  }),
  tutorId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  tutorNome: PropTypes.string,
  petId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  pets: PropTypes.arrayOf(PropTypes.object),
  expanded: PropTypes.bool,
  loadingPets: PropTypes.bool,
  disabled: PropTypes.bool,
  showPetLabel: PropTypes.bool,
  showNovoPetButton: PropTypes.bool,
  allowEmpty: PropTypes.bool,
  petLabel: PropTypes.string,
  placeholder: PropTypes.string,
  emptyOptionLabel: PropTypes.string,
  emptyStateLabel: PropTypes.string,
  returnTo: PropTypes.string,
  sugestoesEspecies: PropTypes.arrayOf(PropTypes.string),
  className: PropTypes.string,
  onSelectPet: PropTypes.func,
  onPetCreated: PropTypes.func,
  onExpandedChange: PropTypes.func,
  onBeforeNovoPet: PropTypes.func,
  onNovoPetClick: PropTypes.func,
};
