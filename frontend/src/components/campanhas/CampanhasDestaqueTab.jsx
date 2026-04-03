import { formatBRL } from "../../utils/formatters";

export default function CampanhasDestaqueTab({
  loadingDestaque,
  destaque,
  carregarDestaque,
  premiosPorVencedor,
  setPremiosPorVencedor,
  vencedoresSelecionados,
  setVencedoresSelecionados,
  createDefaultPremio,
  destaqueResultado,
  setDestaqueResultado,
  enviarDestaque,
  enviandoDestaque,
}) {
  if (loadingDestaque) {
    return (
      <div className="space-y-4">
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
          <span className="text-2xl">🌟</span>
          <div>
            <p className="font-semibold text-amber-800">Destaque Mensal</p>
            <p className="text-sm text-amber-700 mt-0.5">
              O sistema identifica os clientes que mais gastaram e mais
              compraram no mês anterior. Você pode premiar cada vencedor com um
              cupom de recompensa.
            </p>
          </div>
        </div>
        <div className="p-8 text-center text-gray-400">Carregando destaque...</div>
      </div>
    );
  }

  if (!destaque) {
    return (
      <div className="space-y-4">
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
          <span className="text-2xl">🌟</span>
          <div>
            <p className="font-semibold text-amber-800">Destaque Mensal</p>
            <p className="text-sm text-amber-700 mt-0.5">
              O sistema identifica os clientes que mais gastaram e mais
              compraram no mês anterior. Você pode premiar cada vencedor com um
              cupom de recompensa.
            </p>
          </div>
        </div>
        <div className="p-8 text-center">
          <button
            onClick={carregarDestaque}
            className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600"
          >
            Calcular Vencedores
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
        <span className="text-2xl">🌟</span>
        <div>
          <p className="font-semibold text-amber-800">Destaque Mensal</p>
          <p className="text-sm text-amber-700 mt-0.5">
            O sistema identifica os clientes que mais gastaram e mais compraram
            no mês anterior. Você pode premiar cada vencedor com um cupom de
            recompensa.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-gray-900">
              Vencedores - {destaque.periodo}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {destaque.total_clientes_ativos} clientes ativos no período
            </p>
          </div>
          <button
            onClick={carregarDestaque}
            className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200"
          >
            Recalcular
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          {Object.entries(destaque.vencedores).map(([categoria, info]) => {
            const premio =
              premiosPorVencedor[categoria] || createDefaultPremio();
            const setPremio = (update) =>
              setPremiosPorVencedor((prev) => ({
                ...prev,
                [categoria]: {
                  ...(prev[categoria] || createDefaultPremio()),
                  ...update,
                },
              }));
            const selecionado = vencedoresSelecionados[categoria] !== false;

            return (
              <div
                key={categoria}
                className={`bg-gradient-to-br from-amber-50 to-yellow-50 border rounded-xl p-4 space-y-3 transition-opacity ${
                  selecionado
                    ? "border-amber-200 opacity-100"
                    : "border-gray-200 opacity-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selecionado}
                      onChange={(e) =>
                        setVencedoresSelecionados((prev) => ({
                          ...prev,
                          [categoria]: e.target.checked,
                        }))
                      }
                      className="w-4 h-4 accent-amber-500"
                    />
                    <p className="text-xs font-semibold text-amber-600 uppercase">
                      {categoria === "maior_gasto"
                        ? "Maior Gasto"
                        : "Mais Compras"}
                    </p>
                  </label>

                  <div className="flex gap-1">
                    <button
                      onClick={() => setPremio({ tipo_premio: "cupom" })}
                      className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
                        premio.tipo_premio !== "mensagem"
                          ? "bg-amber-500 text-white border-amber-500"
                          : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"
                      }`}
                    >
                      Cupom
                    </button>
                    <button
                      onClick={() => setPremio({ tipo_premio: "mensagem" })}
                      className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
                        premio.tipo_premio === "mensagem"
                          ? "bg-amber-500 text-white border-amber-500"
                          : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"
                      }`}
                    >
                      Brinde
                    </button>
                  </div>
                </div>

                <div>
                  <p className="font-bold text-gray-900">{info.nome}</p>
                  <p className="text-sm text-gray-600">
                    {categoria === "maior_gasto"
                      ? `R$ ${formatBRL(info.total_spent)} gastos`
                      : `${info.total_purchases} compra(s)`}
                  </p>
                </div>

                {premio.tipo_premio !== "mensagem" ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">
                          Valor do cupom (R$)
                        </label>
                        <input
                          type="number"
                          min="1"
                          step="0.01"
                          value={premio.coupon_value ?? 50}
                          onChange={(e) =>
                            setPremio({
                              coupon_value:
                                Number.parseFloat(e.target.value) || 0,
                            })
                          }
                          className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">
                          Validade (dias)
                        </label>
                        <input
                          type="number"
                          min="1"
                          value={premio.coupon_valid_days ?? 10}
                          onChange={(e) =>
                            setPremio({
                              coupon_valid_days:
                                Number.parseInt(e.target.value, 10) || 1,
                            })
                          }
                          className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 block mb-1">
                        Mensagem ao cliente
                      </label>
                      <input
                        type="text"
                        value={premio.mensagem ?? ""}
                        onChange={(e) =>
                          setPremio({ mensagem: e.target.value })
                        }
                        placeholder="Ex: Parabéns! Use este cupom em sua próxima visita"
                        className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div>
                      <label className="text-xs text-gray-500 block mb-1">
                        Mensagem ao cliente
                      </label>
                      <textarea
                        rows={3}
                        value={premio.mensagem_brinde ?? ""}
                        onChange={(e) =>
                          setPremio({ mensagem_brinde: e.target.value })
                        }
                        className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300 resize-none"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">
                          Retirada a partir de
                        </label>
                        <input
                          type="date"
                          value={premio.retirar_de ?? ""}
                          onChange={(e) =>
                            setPremio({ retirar_de: e.target.value })
                          }
                          className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">
                          Retirada até
                        </label>
                        <input
                          type="date"
                          value={premio.retirar_ate ?? ""}
                          onChange={(e) =>
                            setPremio({ retirar_ate: e.target.value })
                          }
                          className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {Object.keys(destaque.vencedores).length === 0 && (
            <div className="col-span-2 p-6 text-center text-gray-400">
              Nenhum vencedor identificado para o período.
            </div>
          )}
        </div>

        {(destaque.desempate_info || []).length > 0 && (
          <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-4 space-y-2">
            <p className="font-semibold text-yellow-800 text-sm">
              Desempate aplicado
            </p>
            {destaque.desempate_info.map((desempate, index) => (
              <div
                key={index}
                className="text-sm text-yellow-700 leading-relaxed"
              >
                <span className="font-medium">
                  {desempate.categoria === "maior_gasto"
                    ? "Maior Gasto"
                    : "Mais Compras"}
                  :
                </span>{" "}
                <span className="line-through text-yellow-500">
                  {desempate.pulado?.nome}
                </span>{" "}
                (1º lugar) já ganhou em outra categoria - o{" "}
                <span className="font-medium">{desempate.posicao_eleito}º colocado</span>{" "}
                <span className="font-semibold text-yellow-800">
                  {desempate.eleito?.nome}
                </span>{" "}
                foi selecionado no lugar.
              </div>
            ))}
          </div>
        )}

        {destaqueResultado ? (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="font-semibold text-green-800">
                Prêmios enviados! ({destaqueResultado.enviados} vencedor(es))
              </p>
              <button
                onClick={() => setDestaqueResultado(null)}
                className="text-xs text-gray-400 hover:text-gray-600 underline"
              >
                Enviar novamente
              </button>
            </div>
            <ul className="space-y-1.5">
              {(destaqueResultado.resultados || []).map((resultado, index) => (
                <li
                  key={index}
                  className="flex items-center gap-2 text-sm text-gray-700"
                >
                  <span>
                    {resultado.categoria === "maior_gasto"
                      ? "Maior Gasto"
                      : "Mais Compras"}
                    :
                  </span>
                  {resultado.tipo_premio === "cupom" ? (
                    <>
                      <span className="font-mono font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded">
                        {resultado.coupon_code}
                      </span>
                      {resultado.ja_existia && (
                        <span className="text-xs text-gray-400">
                          (já existia)
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="text-amber-700">Brinde registrado</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          Object.keys(destaque.vencedores).length > 0 && (
            <button
              onClick={enviarDestaque}
              disabled={
                enviandoDestaque ||
                Object.values(vencedoresSelecionados).every((valor) => !valor)
              }
              className="w-full py-3 bg-amber-500 text-white rounded-xl font-semibold hover:bg-amber-600 disabled:opacity-50 transition-colors"
            >
              {enviandoDestaque
                ? "Enviando prêmios..."
                : "Enviar Prêmios aos Vencedores"}
            </button>
          )
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          ["maior_gasto", "top5_maior_gasto", "Top 5 - Maior Gasto"],
          ["mais_compras", "top5_mais_compras", "Top 5 - Mais Compras"],
        ].map(([categoria, chave, titulo]) => (
          <div
            key={categoria}
            className="bg-white rounded-xl border shadow-sm overflow-hidden"
          >
            <div className="px-4 py-3 border-b bg-gray-50">
              <p className="font-semibold text-gray-800 text-sm">{titulo}</p>
            </div>
            <ul className="divide-y">
              {(destaque[chave] || []).map((cliente, index) => (
                <li
                  key={index}
                  className="px-4 py-3 flex items-center gap-3"
                >
                  <span className="text-lg font-bold text-gray-300 w-6 text-center">
                    {index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {cliente.nome}
                    </p>
                    <p className="text-xs text-gray-500">
                      {categoria === "maior_gasto"
                        ? `R$ ${formatBRL(cliente.total_spent)}`
                        : `${cliente.total_purchases} compra(s)`}
                    </p>
                  </div>
                  {destaque.vencedores[categoria]?.customer_id ===
                    cliente.customer_id && (
                    <span className="text-yellow-500 text-lg">🏆</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
