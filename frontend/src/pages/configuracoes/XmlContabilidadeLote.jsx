import { CalendarClock, Download, Send } from "lucide-react";
import Panel from "../../components/ui/Panel";
import InputPeriodo from "../../components/v2/InputPeriodo/InputPeriodo";
import InputDataHora from "../../components/v2/InputDataHora/InputDataHora";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";

export default function XmlContabilidadeLote({
  periodo,
  onPeriodoChange,
  erroPeriodo,
  agendadoPara,
  onAgendamentoChange,
  operacao,
  bloqueioEnvio,
  onBaixar,
  onEnviar,
  onAgendar,
}) {
  return (
    <Panel
      title="2. XMLs por período"
      subtitle="Reúna as notas de saída do intervalo escolhido em um arquivo ZIP."
    >
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-4">
          <InputPeriodo
            id="xml-periodo"
            label="Período de emissão"
            value={periodo}
            onChange={onPeriodoChange}
            error={erroPeriodo}
            disabled={Boolean(operacao)}
            help="As datas inicial e final estão incluídas no lote."
          />
          <div className="flex flex-wrap gap-2">
            <BotaoInteracao
              icon={Download}
              onClick={onBaixar}
              loading={operacao === "baixar"}
              disabled={Boolean(operacao)}
            >
              Baixar ZIP
            </BotaoInteracao>
            <BotaoInteracao
              icon={Send}
              onClick={onEnviar}
              loading={operacao === "enviar"}
              disabled={Boolean(operacao) || Boolean(bloqueioEnvio)}
              title={bloqueioEnvio || undefined}
            >
              Enviar agora
            </BotaoInteracao>
          </div>
        </div>
        <div className="space-y-4">
          <InputDataHora
            id="xml-agendamento"
            label="Data e hora do envio agendado"
            value={agendadoPara}
            onChange={onAgendamentoChange}
            disabled={Boolean(operacao)}
            help="Horário de Brasília (UTC−3). Usa o período selecionado ao lado."
          />
          <BotaoInteracao
            icon={CalendarClock}
            onClick={onAgendar}
            loading={operacao === "agendar"}
            disabled={Boolean(operacao) || Boolean(bloqueioEnvio)}
            title={bloqueioEnvio || undefined}
          >
            Agendar envio do ZIP
          </BotaoInteracao>
        </div>
      </div>
      <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
        O envio é processado pelo sistema. Acompanhe o resultado no histórico abaixo.
        {bloqueioEnvio ? ` ${bloqueioEnvio}` : ""}
      </p>
    </Panel>
  );
}
