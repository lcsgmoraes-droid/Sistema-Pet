import { Link } from "react-router-dom";

const copy = {
  agenda: {
    title: "Agenda exclusiva de Banho & Tosa",
    text: "O backend ja tem a base para agendamento. O proximo bloco vai trazer calendario, recursos, encaixes e taxi dog.",
  },
  fila: {
    title: "Fila do dia e kanban operacional",
    text: "A proxima etapa transforma cada atendimento em etapas: chegada, banho, secagem, tosa, pronto e entregue.",
  },
};

export default function BanhoTosaComingSoon({ view }) {
  const data = copy[view] || copy.agenda;

  return (
    <div className="rounded-3xl border border-white/80 bg-white p-8 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
        Proximo bloco
      </p>
      <h2 className="mt-2 text-3xl font-black text-slate-900">{data.title}</h2>
      <p className="mt-3 max-w-2xl text-slate-600">{data.text}</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          to="/banho-tosa/servicos"
          className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700"
        >
          Parametrizar servicos
        </Link>
        <Link
          to="/banho-tosa/parametros"
          className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:border-orange-300 hover:text-orange-700"
        >
          Ajustar custos base
        </Link>
      </div>
    </div>
  );
}
