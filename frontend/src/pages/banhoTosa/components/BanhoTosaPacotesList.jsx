import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaPacotesList({ pacotes = [], onChanged }) {
  async function toggleAtivo(pacote) {
    try {
      await banhoTosaApi.atualizarPacote(pacote.id, { ativo: !pacote.ativo });
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel atualizar o pacote."));
    }
  }

  return (
    <section className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">Catalogo</p>
          <h2 className="mt-2 text-xl font-black text-slate-900">Pacotes ativos e inativos</h2>
        </div>
        <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-700">
          {pacotes.length} itens
        </span>
      </div>

      <div className="mt-5 divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200">
        {pacotes.map((pacote) => (
          <div key={pacote.id} className="grid gap-3 p-4 md:grid-cols-[1.2fr_0.8fr_0.8fr_auto] md:items-center">
            <div>
              <p className="font-black text-slate-900">{pacote.nome}</p>
              <p className="text-sm text-slate-500">{pacote.servico_nome || "Qualquer servico"} | {pacote.validade_dias} dias</p>
            </div>
            <Info label="Creditos" value={formatNumber(pacote.quantidade_creditos, 0)} />
            <Info label="Preco" value={formatCurrency(pacote.preco)} />
            <button
              type="button"
              onClick={() => toggleAtivo(pacote)}
              className={`rounded-full px-3 py-2 text-xs font-bold ${
                pacote.ativo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
              }`}
            >
              {pacote.ativo ? "Ativo" : "Inativo"}
            </button>
          </div>
        ))}
        {pacotes.length === 0 && (
          <p className="p-6 text-center text-sm text-slate-500">Nenhum pacote cadastrado ainda.</p>
        )}
      </div>
    </section>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">{label}</p>
      <p className="text-sm font-black text-slate-900">{value}</p>
    </div>
  );
}
