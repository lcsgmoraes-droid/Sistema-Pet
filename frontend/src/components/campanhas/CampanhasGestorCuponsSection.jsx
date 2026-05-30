import CampanhasGestorSection from "./CampanhasGestorSection";

export default function CampanhasGestorCuponsSection({
  gestorSecao,
  setGestorSecao,
  gestorCupons,
  cupomStatus,
  formatBRL,
  anularCupomGestor,
  gestorAnulando,
  abrirCupomManual,
  gestorCliente,
}) {
  const isOpen = gestorSecao === "cupons";
  const ativos =
    gestorCupons?.filter((cupom) => cupom.status === "active").length || 0;
  const criarCupomParaCliente = () => {
    if (!abrirCupomManual || !gestorCliente) return;
    abrirCupomManual({
      customer_id: gestorCliente.id,
      cliente_nome: gestorCliente.nome,
      channel: "pdv",
      motivo: "",
      descricao: "",
      retornar_para_aba: "gestor",
    });
  };

  return (
    <CampanhasGestorSection
      icon={"\uD83C\uDF9F\uFE0F"}
      title="Cupons"
      subtitle={`${ativos} ativo(s) de ${gestorCupons?.length || 0} no total`}
      isOpen={isOpen}
      onToggle={() => setGestorSecao(isOpen ? null : "cupons")}
    >
      <div className="flex items-center justify-between gap-3 mb-3">
        <p className="text-xs text-gray-500">
          Gere cupons pontuais para aniversarios, eventos e acoes da loja.
        </p>
        <button
          type="button"
          onClick={criarCupomParaCliente}
          className="px-3 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700"
        >
          + Gerar cupom
        </button>
      </div>
      {gestorCupons && gestorCupons.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                  Codigo
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                  Desconto
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                  Validade
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-600">
                  Status
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-600">
                  Acao
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {gestorCupons.map((cupom) => (
                <tr
                  key={cupom.id}
                  className={
                    cupom.status !== "active"
                      ? "bg-gray-50 opacity-70"
                      : "hover:bg-gray-50"
                  }
                >
                  <td className="px-4 py-3 font-mono text-xs font-bold text-gray-800">
                    {cupom.code}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-700">
                    {cupom.coupon_type === "gift"
                      ? "Brinde"
                      : cupom.coupon_type === "percent"
                        ? `${cupom.discount_percent}%`
                        : `R$ ${formatBRL(cupom.discount_value)}`}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                    {cupom.valid_until
                      ? new Date(cupom.valid_until).toLocaleDateString("pt-BR")
                      : "Indeterminado"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-0.5 text-xs rounded-full ${
                        cupomStatus[cupom.status]?.color ||
                        "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {cupomStatus[cupom.status]?.label || cupom.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {cupom.status === "active" && (
                      <button
                        onClick={() => anularCupomGestor(cupom.code)}
                        disabled={gestorAnulando === cupom.code}
                        className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 disabled:opacity-50"
                      >
                        {gestorAnulando === cupom.code ? "..." : "Anular"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-8 text-center text-gray-400 text-sm">
          Nenhum cupom encontrado.
        </div>
      )}
    </CampanhasGestorSection>
  );
}
