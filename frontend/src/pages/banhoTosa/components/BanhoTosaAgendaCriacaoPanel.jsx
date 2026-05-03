import { X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import Panel from "../../../components/ui/Panel";
import BanhoTosaAgendaForm from "./BanhoTosaAgendaForm";
import BanhoTosaSugestoesSlots from "./BanhoTosaSugestoesSlots";

export default function BanhoTosaAgendaCriacaoPanel({
  dataRef,
  form,
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
  return (
    <Panel
      actions={
        <ActionButton icon={X} intent="neutral" onClick={onClose} tone="ghost">
          Fechar
        </ActionButton>
      }
      subtitle="Selecione tutor e pet, depois use uma sugestao de horario se quiser acelerar."
      title="Novo agendamento"
    >
      <BanhoTosaAgendaForm
        dataRef={dataRef}
        form={form}
        loadingPets={loadingPets}
        petsDoTutor={petsDoTutor}
        recursos={recursos}
        saving={saving}
        servicos={servicos}
        tutorSelecionado={tutorSelecionado}
        retornoNovoPet={retornoNovoPet}
        onChangeData={onChangeData}
        onChangeField={onChangeField}
        onChangeServico={onChangeServico}
        onSelectTutor={onSelectTutor}
        onSubmit={onSubmit}
      />
      <BanhoTosaSugestoesSlots
        loading={loadingSugestoes}
        sugestoes={sugestoes}
        onUseSlot={onUseSlot}
      />
    </Panel>
  );
}
