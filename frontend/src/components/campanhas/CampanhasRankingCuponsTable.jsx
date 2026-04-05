import { Fragment } from "react";

function CampanhasRankingCupomDetalhesRow({ cupom }) {
  return (
    <tr className="bg-blue-50 border-b">
      <td colSpan={9} className="px-6 py-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div>
            <p className="text-xs text-gray-500 font-medium mb-0.5">Codigo</p>
            <p className="font-mono font-bold text-gray-800">{cupom.code}</p>
          </div>

          {cupom.nome_campanha && (
            <div>
              <p className="text-xs text-gray-500 font-medium mb-0.5">
                Campanha
              </p>
              <p className="text-gray-700">{cupom.nome_campanha}</p>
            </div>
          )}

          <div>
            <p className="text-xs text-gray-500 font-medium mb-0.5">
              Criado em
            </p>
            <p className="text-gray-700">
              {cupom.created_at
                ? new Date(cupom.created_at).toLocaleString("pt-BR")
                : "-"}
            </p>
          </div>

          <div>
            <p className="text-xs text-gray-500 font-medium mb-0.5">
              Valido ate
            </p>
            <p className="text-gray-700">
              {cupom.valid_until
                ? new Date(cupom.valid_until).toLocaleDateString("pt-BR")
                : "Sem validade"}
            </p>
          </div>

          {cupom.used_at && (
            <div>
              <p className="text-xs text-gray-500 font-medium mb-0.5">
                Usado em
              </p>
              <p className="text-gray-700">
                {new Date(cupom.used_at).toLocaleString("pt-BR")}
              </p>
            </div>
          )}

          {cupom.coupon_type === "gift" && cupom.meta?.mensagem && (
            <div className="col-span-2">
              <p className="text-xs text-gray-500 font-medium mb-0.5">
                Mensagem do brinde
              </p>
              <p className="text-gray-700">{cupom.meta.mensagem}</p>
            </div>
          )}

          {cupom.meta?.retirar_de && (
            <div>
              <p className="text-xs text-gray-500 font-medium mb-0.5">
                Retirada a partir de
              </p>
              <p className="text-gray-700">
                {new Date(cupom.meta.retirar_de).toLocaleDateString("pt-BR")}
              </p>
            </div>
          )}

          {cupom.meta?.retirar_ate && (
            <div>
              <p className="text-xs text-gray-500 font-medium mb-0.5">
                Retirada ate
              </p>
              <p className="text-gray-700">
                {new Date(cupom.meta.retirar_ate).toLocaleDateString("pt-BR")}
              </p>
            </div>
          )}

          {cupom.meta?.categoria && (
            <div>
              <p className="text-xs text-gray-500 font-medium mb-0.5">
                Categoria destaque
              </p>
              <p className="text-gray-700">
                {cupom.meta.categoria === "maior_gasto"
                  ? "Maior gasto"
                  : cupom.meta.categoria === "mais_compras"
                    ? "Mais compras"
                    : cupom.meta.categoria}
              </p>
            </div>
          )}

          {cupom.meta?.periodo && (
            <div>
              <p className="text-xs text-gray-500 font-medium mb-0.5">
                Periodo
              </p>
              <p className="text-gray-700">{cupom.meta.periodo}</p>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

export default function CampanhasRankingCuponsTable({
  loadingCupons,
  cupons,
  cupomStatus,
  cupomDetalhes,
  setCupomDetalhes,
  anularCupom,
  anulando,
  formatarValorCupom,
}) {
  if (loadingCupons) {
    return <div className="p-8 text-center text-gray-400">Carregando cupons...</div>;
  }

  if (cupons.length === 0) {
    return (
      <div className="p-8 text-center text-gray-400">
        <p>Nenhum cupom encontrado.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Codigo
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Tipo
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Canal
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Desconto
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Cliente
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Criado em
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Validade
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Status
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Acao
            </th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {cupons.map((cupom) => {
            const status = cupomStatus[cupom.status] || {
              label: cupom.status,
              color: "bg-gray-100 text-gray-600",
            };
            const isDetalhes = cupomDetalhes?.id === cupom.id;

            return (
              <Fragment key={cupom.id}>
                <tr
                  className={`hover:bg-gray-50 cursor-pointer ${
                    isDetalhes ? "bg-blue-50" : ""
                  }`}
                  onClick={() => setCupomDetalhes(isDetalhes ? null : cupom)}
                >
                  <td className="px-4 py-3 font-mono font-semibold text-gray-800">
                    {cupom.code}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {cupom.coupon_type === "percent"
                      ? "Percentual"
                      : cupom.coupon_type === "fixed"
                        ? "Valor fixo"
                        : cupom.coupon_type === "gift"
                          ? "Brinde"
                          : cupom.coupon_type}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {cupom.channel || "pdv"}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {formatarValorCupom(cupom)}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {cupom.nome_cliente ? (
                      <span title={`ID ${cupom.customer_id}`}>
                        {cupom.nome_cliente}
                      </span>
                    ) : cupom.customer_id ? (
                      <span className="text-gray-400">#{cupom.customer_id}</span>
                    ) : (
                      <span className="text-gray-300">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {cupom.created_at
                      ? new Date(cupom.created_at).toLocaleDateString("pt-BR")
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {cupom.valid_until
                      ? new Date(cupom.valid_until).toLocaleDateString("pt-BR")
                      : "-"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${status.color}`}
                    >
                      {status.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setCupomDetalhes(isDetalhes ? null : cupom);
                      }}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      {isDetalhes ? "Fechar" : "Detalhes"}
                    </button>
                    {cupom.status === "active" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          anularCupom(cupom.code);
                        }}
                        disabled={anulando === cupom.code}
                        className="text-xs text-red-600 hover:text-red-800 disabled:opacity-40 font-medium"
                      >
                        {anulando === cupom.code ? "Anulando..." : "Anular"}
                      </button>
                    )}
                  </td>
                </tr>
                {isDetalhes && <CampanhasRankingCupomDetalhesRow cupom={cupom} />}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
