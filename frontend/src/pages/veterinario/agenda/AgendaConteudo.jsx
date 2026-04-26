import AgendaDiasView from "./AgendaDiasView";
import AgendaMesView from "./AgendaMesView";

export default function AgendaConteudo({
  carregando,
  modo,
  diasMes,
  diasVisiveis,
  dataRef,
  agsDia,
  abrindoAgendamentoId,
  onAbrirNovo,
  onGerenciarAgendamento,
}) {
  if (carregando) {
    return (
      <div className="flex h-40 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-500" />
      </div>
    );
  }

  if (modo === "mes") {
    return (
      <AgendaMesView
        diasMes={diasMes}
        dataRef={dataRef}
        agsDia={agsDia}
        abrindoAgendamentoId={abrindoAgendamentoId}
        onAbrirNovo={onAbrirNovo}
        onGerenciarAgendamento={onGerenciarAgendamento}
      />
    );
  }

  return (
    <AgendaDiasView
      modo={modo}
      diasVisiveis={diasVisiveis}
      agsDia={agsDia}
      abrindoAgendamentoId={abrindoAgendamentoId}
      onAbrirNovo={onAbrirNovo}
      onGerenciarAgendamento={onGerenciarAgendamento}
    />
  );
}
