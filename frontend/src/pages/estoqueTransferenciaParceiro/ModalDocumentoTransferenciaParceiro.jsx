import SeletorColunasDocumentoTransferencia from "./SeletorColunasDocumentoTransferencia";

export default function ModalDocumentoTransferenciaParceiro({
  modal,
  colunasSelecionadas,
  onChangeColunas,
  onClose,
  onConfirmar,
  loading,
}) {
  if (!modal?.aberto) return null;

  const registro = modal.registro;
  const ehCupom = modal.tipo === "cupom";
  const ehEmail = modal.tipo === "email";
  const ehConsolidado = modal.tipo === "pdf_consolidado";
  const titulo = ehCupom
    ? "Imprimir cupom"
    : ehEmail
      ? "Enviar por e-mail"
      : ehConsolidado
        ? "Gerar PDF consolidado"
        : "Gerar PDF";
  const subtitulo = ehConsolidado
    ? "Transferencias do filtro atual ou selecao manual"
    : ehEmail && registro?.parceiro_email
      ? `${registro.documento || `Transferencia #${registro.conta_receber_id}`} | ${registro.parceiro_email}`
      : registro?.documento || `Transferencia #${registro?.conta_receber_id || ""}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">{titulo}</h2>
            <p className="mt-1 text-sm text-slate-500">{subtitulo}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Fechar"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <SeletorColunasDocumentoTransferencia
          colunasSelecionadas={colunasSelecionadas}
          onChange={onChangeColunas}
        />

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={onConfirmar}
            disabled={loading}
            className="flex-1 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
          >
            {loading ? "Processando..." : titulo}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
