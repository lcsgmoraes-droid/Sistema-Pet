import { formatarMoeda } from "../../api/produtos";
import { normalizarNumero } from "./transferenciaParceiroUtils";

export default function BaixaLoteAcertoDireto({ form, setForm, totalAplicado, totalCompensado }) {
  const novaConta = form.nova_conta_pagar_acerto || {};
  const valorNovaConta = normalizarNumero(novaConta.valor);
  const valorAtual = Number.isFinite(valorNovaConta) ? valorNovaConta : 0;
  const totalSemNovaConta = Math.max(Number(totalCompensado || 0) - valorAtual, 0);
  const valorSugerido = Math.max(Number(totalAplicado || 0) - totalSemNovaConta, 0);

  const atualizarCampo = (campo, valor) => {
    setForm((prev) => ({
      ...prev,
      nova_conta_pagar_acerto: {
        ...(prev.nova_conta_pagar_acerto || {}),
        [campo]: valor,
      },
    }));
  };

  const preencherValorSugerido = () => {
    atualizarCampo("valor", valorSugerido > 0 ? valorSugerido.toFixed(2) : "");
  };

  return (
    <div className="mt-4 rounded-xl border border-amber-200 bg-white p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold text-amber-950">Lancar divida para acerto</p>
          <p className="mt-1 text-xs text-amber-800">
            Use quando voce deve algo para essa pessoa e quer criar a conta a pagar no ato.
          </p>
        </div>
        <button
          type="button"
          onClick={preencherValorSugerido}
          className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800 transition hover:bg-amber-100"
        >
          Usar saldo do acerto
        </button>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-[1.3fr_0.7fr_0.8fr_0.8fr]">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-amber-900">
            Descricao
          </label>
          <input
            type="text"
            value={novaConta.descricao || ""}
            onChange={(event) => atualizarCampo("descricao", event.target.value)}
            placeholder="Compra de mercadoria / acerto parceiro"
            className="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-amber-900">
            Valor
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={novaConta.valor || ""}
            onChange={(event) => atualizarCampo("valor", event.target.value)}
            className="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-right text-sm text-slate-900 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-amber-900">
            Vencimento
          </label>
          <input
            type="date"
            value={novaConta.data_vencimento || form.data_recebimento}
            onChange={(event) => atualizarCampo("data_vencimento", event.target.value)}
            className="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-amber-900">
            Documento
          </label>
          <input
            type="text"
            value={novaConta.documento || ""}
            onChange={(event) => atualizarCampo("documento", event.target.value)}
            className="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
          />
        </div>
      </div>

      <label className="mt-3 block text-xs font-medium uppercase tracking-wide text-amber-900">
        Observacao da divida
      </label>
      <textarea
        rows={2}
        value={novaConta.observacao || ""}
        onChange={(event) => atualizarCampo("observacao", event.target.value)}
        className="mt-1 w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
      />

      <p className="mt-2 text-xs text-amber-800">
        Valor sugerido para fechar o acerto: {formatarMoeda(valorSugerido)}
      </p>
    </div>
  );
}
