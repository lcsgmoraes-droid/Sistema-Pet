import { Download, Send } from "lucide-react";
import Panel from "../../components/ui/Panel";
import InputPeriodo from "../../components/v2/InputPeriodo/InputPeriodo";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";

export default function XmlContabilidadeLote({
  periodo,
  onPeriodoChange,
  erroPeriodo,
  operacao,
  bloqueioEnvio,
  onBaixar,
  onEnviar,
}) {
  return (
    <Panel
      title="2. Download e envio manual por período"
      subtitle="Escolha qualquer intervalo para baixar os XMLs ou enviá-los agora ao contador."
    >
      <div className="max-w-xl space-y-4">
        <InputPeriodo
          id="xml-periodo"
          label="Período das notas e eventos"
          value={periodo}
          onChange={onPeriodoChange}
          error={erroPeriodo}
          disabled={Boolean(operacao)}
          help="Seleciona as notas pela emissão e os eventos pela data do registro, inclusive de notas antigas. As duas datas estão incluídas."
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
      <p className="mt-4 text-sm text-slate-600 dark:text-slate-300">
        O lote reúne NF-e e NFC-e de saída emitidas no período, inclusive canceladas, e os eventos
        registrados nesse intervalo, mesmo quando a nota foi emitida antes. Inclui cancelamentos,
        cartas de correção e demais eventos. Se faltar algum XML obrigatório, o lote será bloqueado
        para evitar enviar uma contabilidade incompleta.
      </p>
      <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
        No e-mail, cada tipo tem seu ZIP: notas, cancelamentos, cartas de correção e demais eventos.
        O download reúne esses ZIPs em um único arquivo para facilitar o recebimento.
      </p>
      <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
        O envio é processado pelo sistema. Acompanhe o resultado no histórico abaixo.
        {bloqueioEnvio ? ` ${bloqueioEnvio}` : ""}
      </p>
    </Panel>
  );
}
