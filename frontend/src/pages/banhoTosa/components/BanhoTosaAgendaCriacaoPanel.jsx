import { Plus, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import BanhoTosaAgendaForm from "./BanhoTosaAgendaForm";
import BanhoTosaSugestoesSlots from "./BanhoTosaSugestoesSlots";

const FORM_ID = "bt-agenda-modal-form";

export default function BanhoTosaAgendaCriacaoPanel({
  agendamentos,
  capacidade,
  dataRef,
  form,
  isOpen,
  loadingAgenda,
  loadingPets,
  loadingSugestoes,
  petsDoTutor,
  recursos,
  saving,
  servicos,
  sugestoes,
  tutorSelecionado,
  retornoNovoPet,
  onChangeData,
  onChangeField,
  onChangeServico,
  onClose,
  onSelectTutor,
  onSubmit,
  onUseSlot,
}) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Novo agendamento</h2>
            <p className="mt-1 text-sm text-slate-500">
              Escolha tutor, pet e servico, veja a agenda do dia e selecione um horario livre.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-5 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <BanhoTosaAgendaForm
            dataRef={dataRef}
            form={form}
            formId={FORM_ID}
            loadingPets={loadingPets}
            petsDoTutor={petsDoTutor}
            recursos={recursos}
            saving={saving}
            servicos={servicos}
            showActions={false}
            tutorSelecionado={tutorSelecionado}
            retornoNovoPet={retornoNovoPet}
            onChangeData={onChangeData}
            onChangeField={onChangeField}
            onChangeServico={onChangeServico}
            onSelectTutor={onSelectTutor}
            onSubmit={onSubmit}
          />

          <BanhoTosaSugestoesSlots
            agendamentos={agendamentos}
            capacidade={capacidade}
            dataRef={dataRef}
            form={form}
            loadingAgenda={loadingAgenda}
            loadingSugestoes={loadingSugestoes}
            recursos={recursos}
            sugestoes={sugestoes}
            onChangeField={onChangeField}
            onUseSlot={onUseSlot}
          />
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <ActionButton intent="neutral" onClick={onClose} size="md" tone="soft">
            Cancelar
          </ActionButton>
          <ActionButton
            form={FORM_ID}
            icon={Plus}
            intent="create"
            loading={saving}
            size="md"
            type="submit"
          >
            Confirmar
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
