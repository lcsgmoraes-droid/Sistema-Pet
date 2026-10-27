import { Plus } from "lucide-react";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../../../components/v2/InputCombobox/InputCombobox";
import InputData from "../../../components/v2/InputData/InputData";
import InputMoeda from "../../../components/v2/InputMoeda/InputMoeda";
import InputTexto from "../../../components/v2/InputTexto/InputTexto";
import TutorPetSelector from "../../../components/veterinario/TutorPetSelector";
import BanhoTosaAgendaPacoteAviso from "./BanhoTosaAgendaPacoteAviso";

export default function BanhoTosaAgendaForm({
  dataRef,
  form,
  formId,
  loadingPets,
  petsDoTutor,
  saving,
  recursos = [],
  servicos,
  tutorSelecionado,
  retornoNovoPet,
  showActions = true,
  onChangeData,
  onChangeField,
  onChangeServico,
  onSelectTutor,
  onSubmit,
}) {
  return (
    <form id={formId} onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-4">
        <TutorPetSelector
          tutorSelecionado={tutorSelecionado}
          petId={form.pet_id}
          pets={petsDoTutor}
          loadingPets={loadingPets}
          tutorInputId="bt-agenda-tutor"
          returnTo={retornoNovoPet}
          onSelectTutor={onSelectTutor}
          onSelectPet={(petId) => onChangeField("pet_id", petId)}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <InputData
            id="bt-agenda-data"
            label="Data"
            required
            value={dataRef}
            onChange={onChangeData}
          />
          <InputTexto
            id="bt-agenda-hora"
            label="Hora"
            required
            type="time"
            value={form.hora}
            onChange={(value) => onChangeField("hora", value)}
          />
        </div>
        <InputCombobox
          id="bt-agenda-recurso"
          label="Recurso / box"
          value={form.recurso_id}
          placeholder="Sem recurso definido"
          onChange={(value) => onChangeField("recurso_id", value)}
          opcoes={recursos
            .filter((item) => item.ativo)
            .map((item) => ({
              value: String(item.id),
              label: `${item.nome} — cap. ${item.capacidade_simultanea}`,
            }))}
        />
        <InputCombobox
          id="bt-agenda-servico"
          label="Serviço"
          value={form.servico_id}
          onChange={onChangeServico}
          placeholder="Banho & Tosa avulso"
          opcoes={servicos
            .filter((item) => item.ativo)
            .map((item) => ({
              value: String(item.id),
              label: `${item.nome} — ${item.duracao_padrao_minutos} min`,
            }))}
        />
        <BanhoTosaAgendaPacoteAviso
          clienteId={tutorSelecionado?.id}
          petId={form.pet_id}
          servicoId={form.servico_id}
          data={dataRef}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <InputMoeda
            id="bt-agenda-valor"
            label="Valor de tabela"
            value={form.valor_unitario}
            help="A parte coberta pelo pacote não será cobrada de novo no atendimento."
            onChange={(value) => onChangeField("valor_unitario", value)}
          />
          <InputTexto
            id="bt-agenda-observacoes"
            label="Observações"
            value={form.observacoes}
            onChange={(value) => onChangeField("observacoes", value)}
          />
        </div>
      </div>
      {showActions && (
        <div className="flex justify-end">
          <BotaoInteracao icon={Plus} loading={saving} type="submit">
            Criar agendamento
          </BotaoInteracao>
        </div>
      )}
    </form>
  );
}
