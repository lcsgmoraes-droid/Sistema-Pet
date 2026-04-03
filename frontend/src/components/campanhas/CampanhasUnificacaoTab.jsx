export default function CampanhasUnificacaoTab({
  carregarSugestoes,
  loadingSugestoes,
  resultadoMerge,
  desfazerMerge,
  sugestoes,
  confirmarMerge,
  confirmandoMerge,
}) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border shadow-sm p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="font-semibold text-gray-800">
              Unificacao cross-canal por CPF/Telefone
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Clientes que parecem ser a mesma pessoa aparecem aqui para
              unificacao manual.
            </p>
          </div>
          <button
            onClick={carregarSugestoes}
            disabled={loadingSugestoes}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loadingSugestoes ? "Buscando..." : "Buscar duplicatas"}
          </button>
        </div>

        {resultadoMerge && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 text-sm flex items-start justify-between gap-2">
            <div>
              <p className="font-semibold text-green-800">
                Clientes unificados! (Merge #{resultadoMerge.merge_id})
              </p>
              <p className="text-green-600">
                Transferidos: {resultadoMerge.transferencias?.cashback ?? 0}{" "}
                cashbacks, {resultadoMerge.transferencias?.carimbos ?? 0}{" "}
                carimbos, {resultadoMerge.transferencias?.cupons ?? 0} cupons,{" "}
                {resultadoMerge.transferencias?.ranking ?? 0} posicoes de
                ranking, {resultadoMerge.transferencias?.vendas ?? 0} vendas,{" "}
                {resultadoMerge.transferencias?.execucoes_campanhas ?? 0}{" "}
                execucoes de campanha.
              </p>
            </div>
            <button
              onClick={() => desfazerMerge(resultadoMerge.merge_id)}
              className="text-xs text-red-600 hover:underline whitespace-nowrap"
            >
              Desfazer
            </button>
          </div>
        )}

        {loadingSugestoes && (
          <div className="p-8 text-center text-gray-400">
            Buscando duplicatas...
          </div>
        )}

        {!loadingSugestoes && sugestoes.length === 0 && (
          <div className="p-8 text-center text-gray-400">
            <p className="text-3xl mb-2">OK</p>
            <p>
              Nenhuma duplicata encontrada. Clique em "Buscar Duplicatas" para
              verificar.
            </p>
          </div>
        )}

        {sugestoes.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Motivo
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Cliente A
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Cliente B
                  </th>
                  <th className="px-4 py-3 text-center font-medium text-gray-600">
                    Acao
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {sugestoes.map((sugestao, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          sugestao.motivo === "mesmo_cpf"
                            ? "bg-purple-100 text-purple-700"
                            : "bg-blue-100 text-blue-700"
                        }`}
                      >
                        {sugestao.motivo === "mesmo_cpf"
                          ? "Mesmo CPF"
                          : "Mesmo Telefone"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">
                        {sugestao.cliente_a.nome}
                      </p>
                      {sugestao.cliente_a.cpf && (
                        <p className="text-xs text-gray-400">
                          CPF: {sugestao.cliente_a.cpf}
                        </p>
                      )}
                      {sugestao.cliente_a.telefone && (
                        <p className="text-xs text-gray-400">
                          Tel: {sugestao.cliente_a.telefone}
                        </p>
                      )}
                      <p className="text-xs text-gray-300">
                        ID #{sugestao.cliente_a.id}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">
                        {sugestao.cliente_b.nome}
                      </p>
                      {sugestao.cliente_b.cpf && (
                        <p className="text-xs text-gray-400">
                          CPF: {sugestao.cliente_b.cpf}
                        </p>
                      )}
                      {sugestao.cliente_b.telefone && (
                        <p className="text-xs text-gray-400">
                          Tel: {sugestao.cliente_b.telefone}
                        </p>
                      )}
                      <p className="text-xs text-gray-300">
                        ID #{sugestao.cliente_b.id}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex flex-col gap-1 items-center">
                        <button
                          onClick={() =>
                            confirmarMerge(
                              sugestao.cliente_a.id,
                              sugestao.cliente_b.id,
                              sugestao.motivo,
                            )
                          }
                          disabled={
                            confirmandoMerge ===
                            `${sugestao.cliente_a.id}-${sugestao.cliente_b.id}`
                          }
                          className="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50 w-full"
                        >
                          Unir A para B
                        </button>
                        <button
                          onClick={() =>
                            confirmarMerge(
                              sugestao.cliente_b.id,
                              sugestao.cliente_a.id,
                              sugestao.motivo,
                            )
                          }
                          disabled={
                            confirmandoMerge ===
                            `${sugestao.cliente_b.id}-${sugestao.cliente_a.id}`
                          }
                          className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300 disabled:opacity-50 w-full"
                        >
                          Unir B para A
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
