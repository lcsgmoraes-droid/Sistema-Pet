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
      subtitle="Escolha as formas de envio. O download por período continua disponível."
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
          id="xml-automatico"
          checked={config.envio_automatico}
          disabled={salvando || (!config.smtp_configurado && !config.envio_automatico)}
          onChange={(valor) => mudar("envio_automatico", valor)}
        >
          <strong>Enviar um XML a cada emissão</strong>
          <span className="mt-1 block text-slate-500 dark:text-slate-400">
            Depois que a nota de saída for autorizada, o sistema envia o XML ao contador.
          </span>
        </InputCheckTexto>
        <InputCheckTexto
          id="xml-mensal"
          checked={config.envio_mensal}
          disabled={salvando || (!config.smtp_configurado && !config.envio_mensal)}
          onChange={(valor) => mudar("envio_mensal", valor)}
        >
          <strong>Enviar um ZIP todo mês</strong>
          <span className="mt-1 block text-slate-500 dark:text-slate-400">
            Reúne os XMLs do mês anterior e envia na data escolhida, mesmo com esta tela fechada.
          </span>
        </InputCheckTexto>
        {config.envio_mensal ? (
          <div className="grid max-w-xl gap-4 sm:grid-cols-2">
            <InputCombobox
              id="xml-dia-mensal"
              label="Dia do envio mensal"
              value={config.dia_envio_mensal}
              onChange={(valor) => mudar("dia_envio_mensal", Number(valor))}
              opcoes={DIAS}
              permitirLimpar={false}
              disabled={salvando}
              help="Se o mês não tiver esse dia, usa o último dia do mês."
            />
            <InputTexto
              id="xml-hora-mensal"
              label="Hora do envio mensal"
              type="time"
              value={config.hora_envio_mensal}
              onChange={(valor) => mudar("hora_envio_mensal", valor)}
              required
              disabled={salvando}
              help="Horário de Brasília (UTC−3)."
            />
          </div>
        ) : null}
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
