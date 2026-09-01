import { FiBarChart2, FiCheckCircle, FiMessageCircle, FiRepeat } from "react-icons/fi";
import { formatarDataHora } from "./lembretesFormatters";

export default function LembretesRelatorios({ relatorio }) {
  if (!relatorio) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-5 py-12 text-center text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
        Ainda não foi possível carregar o resumo de relacionamento.
      </div>
    );
  }
  const cards = [
    {
      icon: FiMessageCircle,
      label: "Contatos nos últimos 30 dias",
      value: relatorio.contatos_total,
    },
    {
      icon: FiBarChart2,
      label: "Oportunidades contatadas",
      value: relatorio.oportunidades_contatadas,
    },
    { icon: FiRepeat, label: "Recompras após contato", value: relatorio.recompras_apos_contato },
    { icon: FiCheckCircle, label: "Conversão observada", value: `${relatorio.taxa_conversao}%` },
  ];

  return (
    <div className="grid gap-5">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ icon: Icon, label, value }) => (
          <article
            className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900"
            key={label}
          >
            <Icon className="text-teal-700 dark:text-teal-300" aria-hidden="true" />
            <p className="mt-3 text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{label}</p>
          </article>
        ))}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <header className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
            Contatos recentes
          </h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
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
                  <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">
                    {contact.resultado || contact.acao}
                  </p>
                </div>
                <span className="text-xs font-medium capitalize text-slate-600 dark:text-slate-300">
                  {contact.canal} · {contact.status}
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400 sm:text-right">
                  {formatarDataHora(contact.criado_em)}
                </span>
              </article>
            ))}
          </div>
        ) : (
          <p className="m-0 px-5 py-12 text-center text-sm text-slate-500 dark:text-slate-400">
            Nenhum contato registrado nos últimos 30 dias.
          </p>
        )}
      </section>
    </div>
  );
}
