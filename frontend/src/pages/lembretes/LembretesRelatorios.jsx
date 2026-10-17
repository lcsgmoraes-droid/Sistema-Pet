import { BarChart3, CheckCircle2, MessageCircle, Repeat } from "lucide-react";
import CartaoIndicador from "../../components/v2/CartaoIndicador/CartaoIndicador";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import { formatarDataHora } from "./lembretesFormatters";

export default function LembretesRelatorios({ relatorio }) {
  if (!relatorio) {
    return (
      <EstadoVazio
        icone={BarChart3}
        titulo="Ainda não foi possível carregar o resumo de relacionamento."
      />
    );
  }
  const cards = [
    { icon: MessageCircle, label: "Contatos nos últimos 30 dias", value: relatorio.contatos_total },
    {
      icon: BarChart3,
      label: "Oportunidades contatadas",
      value: relatorio.oportunidades_contatadas,
    },
    { icon: Repeat, label: "Recompras após contato", value: relatorio.recompras_apos_contato },
    { icon: CheckCircle2, label: "Conversão observada", value: `${relatorio.taxa_conversao}%` },
  ];

  return (
    <div className="grid gap-5">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ icon, label, value }) => (
          <CartaoIndicador icone={icon} key={label} titulo={label} tom="informativo">
            <p className="text-2xl font-bold text-slate-950 dark:text-white">{value}</p>
          </CartaoIndicador>
        ))}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <header className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
            Contatos recentes
          </h2>
          <p className="v2-texto-ajuda mt-1">
            WhatsApp registra a abertura da conversa; o push acompanha o estado real da fila.
          </p>
        </header>
        {relatorio.historico?.length ? (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {relatorio.historico.map((contact) => (
              <article
                className="grid gap-2 px-5 py-3.5 text-sm sm:grid-cols-[minmax(0,1fr)_160px_140px] sm:items-center"
                key={contact.id}
              >
                <div className="min-w-0">
                  <p className="m-0 truncate font-semibold text-slate-800 dark:text-slate-200">
                    {contact.cliente_nome || "Cliente"} · {contact.produto_nome || "Produto"}
                  </p>
                  <p className="v2-texto-ajuda mt-0.5 truncate">
                    {contact.resultado || contact.acao}
                  </p>
                </div>
                <span className="text-xs font-medium capitalize text-slate-600 dark:text-slate-300">
                  {contact.canal} · {contact.status}
                </span>
                <span className="v2-texto-ajuda sm:text-right">
                  {formatarDataHora(contact.criado_em)}
                </span>
              </article>
            ))}
          </div>
        ) : (
          <div className="p-5">
            <EstadoVazio
              icone={MessageCircle}
              titulo="Nenhum contato registrado nos últimos 30 dias."
            />
          </div>
        )}
      </section>
    </div>
  );
}
