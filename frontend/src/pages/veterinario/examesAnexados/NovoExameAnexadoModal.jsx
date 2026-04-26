import { AlertCircle, X } from "lucide-react";

import NovoExameDadosSection from "./NovoExameDadosSection";
import NovoExameTutorPetSection from "./NovoExameTutorPetSection";

export default function NovoExameAnexadoModal({
  isOpen,
  consultaId,
  erroNovo,
  tutorFormSelecionado,
  setTutorFormSelecionado,
  form,
  setForm,
  petsDoTutor,
  retornoNovoPet,
  onClose,
  onSalvar,
  salvandoNovo,
  setArquivoNovo,
}) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl rounded-2xl bg-white p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-bold text-gray-800">Novo exame</h2>
            <p className="mt-1 text-sm text-gray-500">
              Registre a solicitacao do exame com tutor e pet ja vinculados.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal"
          >
            <X size={18} />
          </button>
        </div>

        {erroNovo && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            <AlertCircle size={16} />
            <span>{erroNovo}</span>
          </div>
        )}

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {consultaId && (
            <div className="sm:col-span-2 rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-800">
              Este exame ficara vinculado a consulta <strong>#{consultaId}</strong>.
            </div>
          )}

          <NovoExameTutorPetSection
            form={form}
            onClose={onClose}
            petsDoTutor={petsDoTutor}
            retornoNovoPet={retornoNovoPet}
            setForm={setForm}
            setTutorFormSelecionado={setTutorFormSelecionado}
            tutorFormSelecionado={tutorFormSelecionado}
          />

          <NovoExameDadosSection
            form={form}
            setArquivoNovo={setArquivoNovo}
            setForm={setForm}
          />
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onSalvar}
            disabled={salvandoNovo || !form.pet_id || !form.nome}
            className="flex-1 rounded-lg bg-orange-500 px-4 py-2 text-sm text-white hover:bg-orange-600 disabled:opacity-60"
          >
            {salvandoNovo ? "Salvando..." : "Registrar exame"}
          </button>
        </div>
      </div>
    </div>
  );
}
