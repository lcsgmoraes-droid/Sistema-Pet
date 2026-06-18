import { CalendarDays } from "lucide-react";
import EmptyState from "../../../components/ui/EmptyState";
import LoadingState from "../../../components/ui/LoadingState";
import Panel from "../../../components/ui/Panel";
import BanhoTosaAgendaCard from "./BanhoTosaAgendaCard";
import BanhoTosaAgendaHeader from "./BanhoTosaAgendaHeader";

export default function BanhoTosaAgendaList({
  agendamentos,
  dataRef,
  loading,
  onAtualizar,
  onCancelar,
  onCheckIn,
}) {
  return (
    <Panel>
      <BanhoTosaAgendaHeader dataRef={dataRef} onAtualizar={onAtualizar} />
      <div className="mt-3 space-y-3">
        {loading && <LoadingState compact label="Carregando agenda..." />}

        {!loading &&
          agendamentos.map((agendamento) => (
            <BanhoTosaAgendaCard
              key={agendamento.id}
              agendamento={agendamento}
              onCheckIn={onCheckIn}
              onCancelar={onCancelar}
            />
          ))}

        {!loading && agendamentos.length === 0 && (
          <EmptyState
            compact
            description="Use Agendar para incluir o primeiro atendimento deste dia."
            icon={CalendarDays}
            title="Nenhum agendamento para esta data"
          />
        )}
      </div>
    </Panel>
  );
}
