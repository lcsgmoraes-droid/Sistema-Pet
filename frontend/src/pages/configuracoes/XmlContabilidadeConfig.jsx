import InputTexto from "../../components/v2/InputTexto/InputTexto";
import InputCheckTexto from "../../components/v2/InputCheckTexto/InputCheckTexto";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import Panel from "../../components/ui/Panel";

const DIAS = Array.from({ length: 31 }, (_, indice) => ({
  value: indice + 1,
  label: `Dia ${indice + 1}`,
}));

export default function XmlContabilidadeConfig({ config, onChange, onSalvar, salvando, alterado }) {
  const mudar = (campo, valor) => onChange({ ...config, [campo]: valor });
  return (
    <Panel
      title="1. Destinatário e envios automáticos"
      subtitle="Ative o envio individual, o envio mensal ou os dois, conforme sua rotina com a contabilidade."
    >
      <form onSubmit={onSalvar} className="space-y-5">
        <div className="max-w-xl">
          <InputTexto
            id="email-contador"
            label="E-mail do contador"
            type="email"
            maxLength={254}
            autoComplete="email"
            placeholder="contador@escritorio.com.br"
            value={config.email_contador}
            onChange={(valor) => mudar("email_contador", valor)}
            required={config.envio_automatico || config.envio_mensal}
            disabled={salvando}
            help="Os envios usam o destinatário salvo nesta configuração."
          />
        </div>
        {!config.smtp_configurado ? (
          <p
            role="status"
            className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
          >
            O serviço de e-mail ainda não está configurado no sistema. Você pode baixar os ZIPs e
            salvar o destinatário; os envios ficam indisponíveis até a configuração do serviço.
          </p>
        ) : null}
        <InputCheckTexto
          id="xml-por-xml"
          checked={config.envio_automatico}
          disabled={salvando || (!config.smtp_configurado && !config.envio_automatico)}
          onChange={(valor) => mudar("envio_automatico", valor)}
        >
          <strong>Enviar XML por XML: cada nota e seus eventos</strong>
          <span className="mt-1 block text-slate-500 dark:text-slate-400">
            Envia cada XML separadamente: a nota após a autorização e os novos eventos quando
            registrados, como cancelamentos e cartas de correção. Funciona mesmo com o envio mensal
            desativado.
          </span>
        </InputCheckTexto>
        <InputCheckTexto
          id="xml-mensal"
          checked={config.envio_mensal}
          disabled={salvando || (!config.smtp_configurado && !config.envio_mensal)}
          onChange={(valor) => mudar("envio_mensal", valor)}
        >
          <strong>Enviar automaticamente o mês anterior completo</strong>
          <span className="mt-1 block text-slate-500 dark:text-slate-400">
            Todo mês, no dia e horário escolhidos, o sistema envia os XMLs ao contador, mesmo com
            esta tela fechada. O período termina no último dia do mês anterior: 28, 29, 30 ou 31. Os
            anexos ficam separados por tipo: um ZIP de notas, outro de cancelamentos, outro de
            cartas de correção e outros para os demais eventos encontrados.
          </span>
        </InputCheckTexto>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          O envio mensal reúne as notas emitidas e os eventos registrados no mês anterior, inclusive
          cancelamentos e correções de notas mais antigas. As duas opções são independentes e podem
          ficar ativadas juntas.
        </p>
        <div className="grid max-w-xl gap-4 sm:grid-cols-2">
          <InputCombobox
            id="xml-dia-mensal"
            label="Dia do envio mensal"
            value={config.dia_envio_mensal}
            onChange={(valor) => mudar("dia_envio_mensal", Number(valor))}
            opcoes={DIAS}
            permitirLimpar={false}
            disabled={salvando || !config.envio_mensal}
            help="Se o mês do envio não tiver esse dia, usa o último dia desse mês."
          />
          <InputTexto
            id="xml-hora-mensal"
            label="Hora do envio mensal"
            type="time"
            value={config.hora_envio_mensal}
            onChange={(valor) => mudar("hora_envio_mensal", valor)}
            required
            disabled={salvando || !config.envio_mensal}
            help="Horário de Brasília (UTC−3)."
          />
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Exemplo: no dia 1º de março, o envio reúne todo fevereiro, do dia 1 ao dia 28 (ou 29 em
          ano bissexto). Outros períodos estão disponíveis somente no envio manual abaixo.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <BotaoSalva loading={salvando} disabled={!alterado}>
            Salvar configuração
          </BotaoSalva>
          {alterado ? (
            <p className="text-xs text-amber-700 dark:text-amber-300">
              Existem alterações ainda não salvas.
            </p>
          ) : null}
        </div>
      </form>
    </Panel>
  );
}
