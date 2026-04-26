import { AlertCircle, X } from "lucide-react";
import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";

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
              Registre a solicitação do exame com tutor e pet já vinculados.
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
              Este exame ficará vinculado à consulta <strong>#{consultaId}</strong>.
            </div>
          )}

          <div className="sm:col-span-2">
            <TutorAutocomplete
              label="Tutor"
              inputId="exame-tutor"
              selectedTutor={tutorFormSelecionado}
              onSelect={(tutor) => {
                setTutorFormSelecionado(tutor);
                setForm((prev) => ({ ...prev, pet_id: "" }));
              }}
              placeholder="Digite o nome, CPF ou telefone do tutor..."
            />
          </div>

          <div className="sm:col-span-2">
            <div className="mb-1 flex items-center justify-between gap-2">
              <label className="block text-xs font-medium text-gray-600">Pet*</label>
              <NovoPetButton
                tutorId={tutorFormSelecionado?.id}
                tutorNome={tutorFormSelecionado?.nome}
                returnTo={retornoNovoPet}
                onBeforeNavigate={onClose}
              />
            </div>
            <select
              value={form.pet_id}
              onChange={(event) => setForm((prev) => ({ ...prev, pet_id: event.target.value }))}
              disabled={!tutorFormSelecionado?.id}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
            >
              <option value="">
                {!tutorFormSelecionado?.id
                  ? "Selecione o tutor primeiro..."
                  : petsDoTutor.length > 0
                  ? "Selecione o pet..."
                  : "Nenhum pet vinculado a este tutor"}
              </option>
              {petsDoTutor.map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.nome}
                  {pet.especie ? ` (${pet.especie})` : ""}
                </option>
              ))}
            </select>
            {tutorFormSelecionado?.id && petsDoTutor.length === 0 && (
              <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para este tutor.</p>
            )}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Tipo*</label>
            <select
              value={form.tipo}
              onChange={(event) => setForm((prev) => ({ ...prev, tipo: event.target.value }))}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
            >
              <option value="laboratorial">Laboratorial</option>
              <option value="imagem">Imagem</option>
              <option value="clinico">Clínico</option>
              <option value="outro">Outro</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Data da solicitação</label>
            <input
              type="date"
              value={form.data_solicitacao}
              onChange={(event) => setForm((prev) => ({ ...prev, data_solicitacao: event.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
          </div>

          <CampoTexto
            label="Nome do exame*"
            value={form.nome}
            onChange={(value) => setForm((prev) => ({ ...prev, nome: value }))}
            placeholder="Ex: Hemograma completo"
            className="sm:col-span-2"
          />

          <CampoTexto
            label="Laboratório"
            value={form.laboratorio}
            onChange={(value) => setForm((prev) => ({ ...prev, laboratorio: value }))}
            placeholder="Opcional"
            className="sm:col-span-2"
          />

          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">Observações</label>
            <textarea
              value={form.observacoes}
              onChange={(event) => setForm((prev) => ({ ...prev, observacoes: event.target.value }))}
              rows={4}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              placeholder="Informações adicionais do exame agendado..."
            />
          </div>

          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">Arquivo do exame</label>
            <input
              type="file"
              onChange={(event) => setArquivoNovo(event.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-orange-100 file:px-3 file:py-1.5 file:text-orange-700"
            />
            <p className="mt-1 text-xs text-gray-500">
              Se anexar agora, o exame já aparece nesta tela e fica pronto para consulta pela IA.
            </p>
          </div>
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

function CampoTexto({ label, value, onChange, placeholder, className = "" }) {
  return (
    <div className={className}>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
      />
    </div>
  );
}
