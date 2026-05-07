export const COLUNAS_DOCUMENTO_PEDIDO = [
  { chave: 'codigo', label: 'Codigo / SKU' },
  { chave: 'produto', label: 'Descricao' },
  { chave: 'quantidade', label: 'Quantidade' },
  { chave: 'preco_unitario', label: 'Custo unitario' },
  { chave: 'desconto', label: 'Desconto' },
  { chave: 'total', label: 'Total' },
];

export const COLUNAS_DOCUMENTO_COMPLETO = COLUNAS_DOCUMENTO_PEDIDO.map((coluna) => coluna.chave);
export const COLUNAS_DOCUMENTO_FORNECEDOR = ['codigo', 'produto', 'quantidade'];
export const COLUNAS_DOCUMENTO_FINANCEIRAS = ['preco_unitario', 'desconto', 'total'];

export const normalizarColunasDocumentoPedido = (colunas = []) => {
  const candidatas = Array.isArray(colunas)
    ? colunas
    : String(colunas || '').split(',');

  const selecionadas = new Set(
    candidatas
      .map((coluna) => String(coluna || '').trim().toLowerCase())
      .filter(Boolean)
  );

  return COLUNAS_DOCUMENTO_COMPLETO.filter((coluna) => selecionadas.has(coluna));
};

export const documentoTemColunasFinanceiras = (colunas = []) => (
  normalizarColunasDocumentoPedido(colunas).some((coluna) => COLUNAS_DOCUMENTO_FINANCEIRAS.includes(coluna))
);

const SeletorColunasDocumentoPedido = ({ colunasSelecionadas, onChange, titulo, descricao }) => {
  const colunasNormalizadas = normalizarColunasDocumentoPedido(colunasSelecionadas);
  const semValores = !documentoTemColunasFinanceiras(colunasNormalizadas);

  const alternarColuna = (chave) => {
    if (colunasNormalizadas.includes(chave)) {
      onChange(colunasNormalizadas.filter((coluna) => coluna !== chave));
      return;
    }

    onChange([...colunasNormalizadas, chave]);
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">{titulo}</h3>
          <p className="mt-1 text-xs text-slate-500">{descricao}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onChange(COLUNAS_DOCUMENTO_FORNECEDOR)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            Somente fornecedor
          </button>
          <button
            type="button"
            onClick={() => onChange(COLUNAS_DOCUMENTO_COMPLETO)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            Documento completo
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {COLUNAS_DOCUMENTO_PEDIDO.map((coluna) => (
          <label
            key={coluna.chave}
            className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
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

      <div className={`mt-3 rounded-md px-3 py-2 text-xs ${semValores ? 'bg-amber-50 text-amber-800 border border-amber-200' : 'bg-emerald-50 text-emerald-800 border border-emerald-200'}`}>
        {semValores
          ? 'Sem colunas financeiras: frete, desconto e total tambem ficam ocultos no documento e no e-mail.'
          : 'Com colunas financeiras: o documento mostra custos, descontos e total do pedido.'}
      </div>
    </div>
  );
};

export default SeletorColunasDocumentoPedido;
