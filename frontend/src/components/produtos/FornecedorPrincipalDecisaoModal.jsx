export default function FornecedorPrincipalDecisaoModal({
  decisaoFornecedor,
  isOpen,
  nomeFornecedor,
  onClose,
  onConfirm,
  onSelectDecisao,
  selecionadosCount,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
      <div className="w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-slate-100 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                Fornecedor principal
              </p>
              <h3 className="mt-1 text-xl font-bold text-slate-950">
                Como tratar os fornecedores atuais?
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Voce esta definindo <strong>{nomeFornecedor}</strong> como principal em{" "}
                <strong>{selecionadosCount}</strong> produto(s). Escolha se os outros fornecedores
                continuam como alternativa ou se devem sair do cadastro destes produtos.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              aria-label="Fechar"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        <div className="grid gap-3 px-6 py-5 md:grid-cols-2">
          <button
            type="button"
            onClick={() => onSelectDecisao("manter")}
            className={`group rounded-xl border p-4 text-left transition ${
              decisaoFornecedor === "manter"
                ? "border-blue-500 bg-blue-50 shadow-sm ring-2 ring-blue-100"
                : "border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50"
            }`}
          >
            <span className="flex items-center justify-between gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
                A
              </span>
              {decisaoFornecedor === "manter" && (
                <span className="rounded-full bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white">
                  Selecionado
                </span>
              )}
            </span>
            <span className="mt-4 block text-base font-semibold text-slate-950">
              Manter alternativos
            </span>
            <span className="mt-2 block text-sm leading-5 text-slate-600">
              O novo fornecedor vira principal, e os fornecedores atuais continuam vinculados para
              consulta, historico e futuras compras.
            </span>
          </button>

          <button
            type="button"
            onClick={() => onSelectDecisao("remover")}
            className={`group rounded-xl border p-4 text-left transition ${
              decisaoFornecedor === "remover"
                ? "border-emerald-500 bg-emerald-50 shadow-sm ring-2 ring-emerald-100"
                : "border-emerald-200 bg-emerald-50 hover:border-emerald-400 hover:bg-emerald-100"
            }`}
          >
            <span className="flex items-center justify-between gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-600 text-sm font-bold text-white">
                B
              </span>
              {decisaoFornecedor === "remover" && (
                <span className="rounded-full bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white">
                  Selecionado
                </span>
              )}
            </span>
            <span className="mt-4 block text-base font-semibold text-emerald-950">
              Remover os outros
            </span>
            <span className="mt-2 block text-sm leading-5 text-emerald-900">
              Mantem somente o fornecedor escolhido. Bom para limpar linhas antigas ou fornecedores
              que nao devem mais aparecer nas sugestoes.
            </span>
          </button>
        </div>

        <div className="flex flex-col gap-3 bg-slate-50 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500">
            Nenhuma alteracao sera aplicada ate voce escolher uma opcao e confirmar.
          </p>
          <div className="flex gap-2 sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-white"
            >
              Voltar
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={!decisaoFornecedor}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
            >
              Confirmar escolha
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
