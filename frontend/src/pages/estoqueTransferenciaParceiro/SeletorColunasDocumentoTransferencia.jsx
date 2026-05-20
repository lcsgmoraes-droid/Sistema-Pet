import {
  COLUNAS_DOCUMENTO_TRANSFERENCIA,
  COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  COLUNAS_DOCUMENTO_TRANSFERENCIA_RETIRADA,
  documentoTransferenciaTemValores,
  normalizarColunasDocumentoTransferencia,
} from "./transferenciaParceiroUtils";

export default function SeletorColunasDocumentoTransferencia({
  colunasSelecionadas,
  onChange,
}) {
  const colunasNormalizadas = normalizarColunasDocumentoTransferencia(colunasSelecionadas);
  const semValores = !documentoTransferenciaTemValores(colunasNormalizadas);

  const alternarColuna = (chave) => {
    if (colunasNormalizadas.includes(chave)) {
      onChange(colunasNormalizadas.filter((coluna) => coluna !== chave));
      return;
    }

    onChange([...colunasNormalizadas, chave]);
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Conteudo do documento</h3>
          <p className="mt-1 text-xs text-slate-500">
            Escolha o que deve sair antes de baixar ou imprimir.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onChange(COLUNAS_DOCUMENTO_TRANSFERENCIA_RETIRADA)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Somente retirada
          </button>
          <button
            type="button"
            onClick={() => onChange(COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Documento completo
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {COLUNAS_DOCUMENTO_TRANSFERENCIA.map((coluna) => (
          <label
            key={coluna.chave}
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
          >
            <input
              type="checkbox"
              checked={colunasNormalizadas.includes(coluna.chave)}
              onChange={() => alternarColuna(coluna.chave)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span>{coluna.label}</span>
          </label>
        ))}
      </div>

      <div
        className={`mt-3 rounded-lg border px-3 py-2 text-xs ${
          semValores
            ? "border-amber-200 bg-amber-50 text-amber-800"
            : "border-emerald-200 bg-emerald-50 text-emerald-800"
        }`}
      >
        {semValores
          ? "Sem custos: o parceiro ve apenas identificacao, descricao e quantidade."
          : "Com valores: o documento mostra custo unitario, total do item e totalizadores marcados."}
      </div>
    </div>
  );
}
