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
  onChangeData,
  onChangeField,
  onChangeServico,
  onSelectTutor,
  onSubmit,
  onUseSlot,
}) {
  return (
    <div>
      <BanhoTosaAgendaForm
        dataRef={dataRef}
        form={form}
        loadingPets={loadingPets}
        petsDoTutor={petsDoTutor}
        recursos={recursos}
        saving={saving}
        servicos={servicos}
        tutorSelecionado={tutorSelecionado}
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
    </div>
  );
}
