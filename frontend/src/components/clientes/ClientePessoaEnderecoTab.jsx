import { Edit2, MapPin, Plus, Star } from "lucide-react";
import BotaoExcluir from "../v2/BotaoExcluir/BotaoExcluir";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";

const ROTULO_TIPO_ENDERECO = {
  entrega: "Entrega",
  cobranca: "Cobrança",
  comercial: "Comercial",
  residencial: "Residencial",
  trabalho: "Trabalho",
};

// Uma cor por tipo, todas diferentes da cor do badge "Principal" (índigo) — ajuda a reconhecer o
// endereço certo numa lista maior, sem depender só do texto do badge.
const COR_TIPO_ENDERECO = {
  entrega: "bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-200",
  cobranca: "bg-purple-100 text-purple-800 dark:bg-purple-500/15 dark:text-purple-200",
  comercial: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200",
  residencial: "bg-teal-100 text-teal-800 dark:bg-teal-500/15 dark:text-teal-200",
  trabalho: "bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-200",
};

function CardEndereco({ apelido, badge, endereco, onEditar, onExcluir }) {
  const temDados = Boolean(endereco.cep || endereco.endereco || endereco.cidade);

  return (
    <div
      className={[
        "rounded-lg border p-3",
        badge.principal
          ? "border-indigo-300 bg-indigo-50/60 dark:border-indigo-500/40 dark:bg-indigo-500/10"
          : "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            {badge.principal ? (
              <span className="inline-flex items-center gap-1 rounded bg-indigo-600 px-2 py-0.5 text-xs font-semibold text-white">
                <Star className="h-3 w-3 fill-current" aria-hidden="true" />
                Principal
              </span>
            ) : (
              <>
                <span
                  className={[
                    "rounded px-2 py-0.5 text-xs font-medium",
                    COR_TIPO_ENDERECO[endereco.tipo] || COR_TIPO_ENDERECO.trabalho,
                  ].join(" ")}
                >
                  {ROTULO_TIPO_ENDERECO[endereco.tipo] || "Trabalho"}
                </span>
                <span className="text-xs font-medium text-slate-500">{badge.contador}</span>
              </>
            )}
          </div>

          {apelido ? (
            <p className="mb-1 text-sm font-semibold text-slate-900 dark:text-slate-100">
              {apelido}
            </p>
          ) : null}

          {temDados ? (
            <>
              <p className="text-sm text-slate-700 dark:text-slate-300">
                {endereco.endereco}, {endereco.numero}
                {endereco.complemento ? ` - ${endereco.complemento}` : ""}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {endereco.bairro}, {endereco.cidade}/{endereco.estado}
              </p>
              <p className="mt-1 text-xs text-slate-500">CEP: {endereco.cep}</p>
            </>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Nenhum endereço cadastrado
            </p>
          )}
        </div>
        <div className="flex flex-none gap-1">
          <BotaoInteracao icon={Edit2} tamanho="pequeno" onClick={onEditar}>
            Editar
          </BotaoInteracao>
          {temDados && onExcluir ? (
            <BotaoExcluir
              tamanho="pequeno"
              mensagemConfirmacao="Deseja realmente remover este endereço?"
              onClick={onExcluir}
            >
              Excluir
            </BotaoExcluir>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function ClientePessoaEnderecoTab({
  abrirModalEndereco,
  enderecosAdicionais,
  formData,
  removerEndereco,
}) {
  const enderecoPrincipal = {
    tipo: "principal",
    cep: formData.cep,
    endereco: formData.endereco,
    numero: formData.numero,
    complemento: formData.complemento,
    bairro: formData.bairro,
    cidade: formData.cidade,
    estado: formData.estado,
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-2">
          <MapPin className="mt-0.5 h-4 w-4 flex-none text-blue-600 dark:text-blue-300" aria-hidden="true" />
          <div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Endereço</h4>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              O principal é usado como endereço padrão do cadastro; adicione outros para
              entrega, cobrança etc.
            </p>
          </div>
        </div>
        <BotaoInteracao
          icon={Plus}
          className="self-start sm:self-auto"
          onClick={() => abrirModalEndereco()}
        >
          Adicionar endereço
        </BotaoInteracao>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <CardEndereco
          endereco={enderecoPrincipal}
          badge={{ principal: true }}
          onEditar={() => abrirModalEndereco("principal")}
          onExcluir={() => removerEndereco("principal")}
        />

        {enderecosAdicionais.map((endereco, index) => (
          <CardEndereco
            key={index}
            endereco={endereco}
            apelido={endereco.apelido}
            badge={{ principal: false, contador: `+${index + 1}` }}
            onEditar={() => abrirModalEndereco(index)}
            onExcluir={() => removerEndereco(index)}
          />
        ))}
      </div>
    </div>
  );
}
