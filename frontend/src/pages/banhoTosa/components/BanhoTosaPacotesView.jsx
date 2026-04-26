import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaCreditoForm from "./BanhoTosaCreditoForm";
import BanhoTosaCreditosList from "./BanhoTosaCreditosList";
import BanhoTosaPacoteForm from "./BanhoTosaPacoteForm";
import BanhoTosaPacotesList from "./BanhoTosaPacotesList";

export default function BanhoTosaPacotesView({ servicos = [], onChanged }) {
  const [pacotes, setPacotes] = useState([]);
  const [creditos, setCreditos] = useState([]);
  const [loading, setLoading] = useState(false);

  async function carregar() {
    setLoading(true);
    try {
      const [pacotesRes, creditosRes] = await Promise.all([
        banhoTosaApi.listarPacotes(),
        banhoTosaApi.listarCreditosPacote({ limit: 300 }),
      ]);
      setPacotes(Array.isArray(pacotesRes.data) ? pacotesRes.data : []);
      setCreditos(Array.isArray(creditosRes.data) ? creditosRes.data : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar pacotes."));
      setPacotes([]);
      setCreditos([]);
    } finally {
      setLoading(false);
    }
  }

  async function recarregarTudo() {
    await carregar();
    await onChanged?.(true);
  }

  useEffect(() => {
    carregar();
  }, []);

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
              Recorrencia e fidelizacao
            </p>
            <h2 className="mt-2 text-2xl font-black text-slate-900">
              Pacotes de Banho & Tosa
            </h2>
            <p className="mt-1 max-w-3xl text-sm text-slate-500">
              Cadastre pacotes, libere creditos por tutor/pet e consuma o saldo na ficha do atendimento sem gerar cobranca duplicada.
            </p>
          </div>
          <button
            type="button"
            onClick={carregar}
            className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-600 transition hover:border-orange-300 hover:text-orange-700"
          >
            {loading ? "Carregando..." : "Atualizar"}
          </button>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <BanhoTosaPacoteForm servicos={servicos} onChanged={recarregarTudo} />
        <BanhoTosaCreditoForm pacotes={pacotes} onChanged={recarregarTudo} />
      </div>

      <BanhoTosaPacotesList pacotes={pacotes} onChanged={recarregarTudo} />
      <BanhoTosaCreditosList creditos={creditos} />
    </div>
  );
}
