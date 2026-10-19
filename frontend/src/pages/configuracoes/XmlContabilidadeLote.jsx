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
      subtitle="Escolha qualquer intervalo para baixar um ZIP ou enviá-lo agora ao contador."
    >
      <div className="max-w-xl space-y-4">
        <InputPeriodo
          id="xml-periodo"
          label="Período de emissão"
          value={periodo}
          onChange={onPeriodoChange}
          error={erroPeriodo}
          disabled={Boolean(operacao)}
          help="As datas inicial e final estão incluídas. Esta seleção vale somente para as ações manuais."
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
        O lote reúne NF-e e NFC-e de saída emitidas no período, inclusive canceladas, com todos os
        eventos dessas notas, como cancelamentos e cartas de correção. Se faltar algum XML
        obrigatório, o lote será bloqueado para evitar enviar uma contabilidade incompleta.
      </p>
      <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
        O envio é processado pelo sistema. Acompanhe o resultado no histórico abaixo.
        {bloqueioEnvio ? ` ${bloqueioEnvio}` : ""}
      </p>
    </Panel>
  );
}
