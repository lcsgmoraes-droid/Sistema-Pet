import { formatQtd } from "./produtosBalancoUtils";

function ProdutosBalancoTabela({
  destacados,
  inputRefs,
  inputs,
  onAtualizarInput,
  onInputKeyDown,
  produtos,
  submetendo,
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-auto">
      <table className="w-full min-w-[1300px]">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Imagem
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Descricao
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Codigo
            </th>
            <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">
              Unidade
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Estoque Atual
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Entrada
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Saida
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Balanco
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Lote
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Validade
            </th>
          </tr>
        </thead>
        <tbody>
          {produtos.map((produto) => {
            const destaque = destacados[produto.id];
            const corDestaque = destaque ? "bg-emerald-50 border-l-4 border-emerald-500" : "";

            return (
              <tr key={produto.id} className={`border-b border-gray-100 ${corDestaque}`}>
                <td className="px-3 py-3">
                  <div className="w-10 h-10 rounded bg-gray-100 overflow-hidden border border-gray-200 flex items-center justify-center">
                    {produto.imagem_principal ? (
                      <img
                        src={
                          produto.imagem_principal.startsWith("http")
                            ? produto.imagem_principal
                            : `${globalThis.location.origin}${produto.imagem_principal}`
                        }
                        alt={produto.nome}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <span className="text-xs text-gray-400">IMG</span>
                    )}
                  </div>
                </td>
                <td className="px-3 py-3">
                  <div className="text-sm font-medium text-gray-900">{produto.nome}</div>
                  <div className="text-xs text-gray-500">{produto.marca?.nome || "Sem marca"}</div>
                </td>
                <td className="px-3 py-3">
                  <div className="text-sm text-gray-900 font-mono">{produto.codigo || "-"}</div>
                  <div className="text-xs text-gray-500 font-mono">
                    {produto.codigo_barras || "-"}
                  </div>
                </td>
                <td className="px-3 py-3 text-center text-sm text-gray-700">
                  {produto.unidade || "UN"}
                </td>
                <td className="px-3 py-3 text-right text-sm font-semibold text-gray-900">
                  {formatQtd(produto.estoque_atual)}
                </td>

                {[
                  { campo: "entrada", placeholder: "0" },
                  { campo: "saida", placeholder: "0" },
                  { campo: "balanco", placeholder: "Novo estoque" },
                ].map((coluna) => (
                  <td key={coluna.campo} className="px-3 py-3 text-right">
                    <input
                      ref={(el) => {
                        inputRefs.current[`${produto.id}-${coluna.campo}`] = el;
                      }}
                      type="text"
                      inputMode="decimal"
                      value={inputs?.[produto.id]?.[coluna.campo] ?? ""}
                      onChange={(e) => onAtualizarInput(produto.id, coluna.campo, e.target.value)}
                      onKeyDown={(e) => onInputKeyDown(e, produto, coluna.campo)}
                      placeholder={coluna.placeholder}
                      disabled={Boolean(submetendo[produto.id])}
                      className="w-28 border border-gray-300 rounded-lg px-2 py-1.5 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-300"
                    />
                  </td>
                ))}

                <td className="px-3 py-3">
                  <input
                    ref={(el) => {
                      inputRefs.current[`${produto.id}-lote`] = el;
                    }}
                    type="text"
                    value={inputs?.[produto.id]?.lote ?? ""}
                    onChange={(e) => onAtualizarInput(produto.id, "lote", e.target.value)}
                    placeholder="Ex: LOTE-001"
                    disabled={Boolean(submetendo[produto.id])}
                    className="w-40 border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  />
                </td>

                <td className="px-3 py-3">
                  <input
                    ref={(el) => {
                      inputRefs.current[`${produto.id}-validade`] = el;
                    }}
                    type="date"
                    value={inputs?.[produto.id]?.validade ?? ""}
                    onChange={(e) => onAtualizarInput(produto.id, "validade", e.target.value)}
                    disabled={Boolean(submetendo[produto.id])}
                    className="w-40 border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  />
                </td>
              </tr>
            );
          })}

          {produtos.length === 0 && (
            <tr>
              <td colSpan={10} className="px-3 py-8 text-center text-sm text-gray-500">
                Nenhum produto encontrado com os filtros atuais.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ProdutosBalancoTabela;
