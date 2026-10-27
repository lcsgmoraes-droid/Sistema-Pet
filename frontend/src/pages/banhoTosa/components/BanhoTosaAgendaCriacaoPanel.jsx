import { Plus } from "lucide-react";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import ModalPadrao from "../../../components/v2/ModalPadrao/ModalPadrao";
import BanhoTosaAgendaForm from "./BanhoTosaAgendaForm";
import BanhoTosaSugestoesSlots from "./BanhoTosaSugestoesSlots";

const FORM_ID = "bt-agenda-modal-form";
export default function BanhoTosaAgendaCriacaoPanel({
  agendamentos,
  capacidade,
  dataRef,
  duracaoMinutos,
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
    <ModalPadrao
      titulo="Novo agendamento"
      tamanho="ampla"
      onFechar={() => !saving && onClose()}
      rodape={
        <>
          <BotaoCancelar disabled={saving} onClick={onClose} />
          <BotaoInteracao form={FORM_ID} icon={Plus} loading={saving} type="submit">
            Confirmar
          </BotaoInteracao>
        </>
      }
    >
      <p className="mb-5 text-sm text-slate-500 dark:text-slate-400">
        Escolha tutor, pet e serviço, confira o pacote e selecione um horário livre.
      </p>
      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr] lg:gap-6">
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
          duracaoMinutos={duracaoMinutos}
          form={form}
          loadingAgenda={loadingAgenda}
          loadingSugestoes={loadingSugestoes}
          recursos={recursos}
          sugestoes={sugestoes}
          onChangeField={onChangeField}
          onUseSlot={onUseSlot}
        />
      </div>
    </ModalPadrao>
  );
}
