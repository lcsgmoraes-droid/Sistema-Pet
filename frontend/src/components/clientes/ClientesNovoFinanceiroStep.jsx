import ClienteInsights from "../ClienteInsights";
import { ClienteSegmentos } from "../ClienteSegmentos";
import ClienteTimeline from "../ClienteTimeline";
import ExtratoCredito from "../ExtratoCredito";
import WhatsAppHistorico from "../WhatsAppHistorico";
import { FiCreditCard, FiDollarSign, FiMessageCircle, FiTrendingDown, FiTrendingUp } from "react-icons/fi";
import { formatBRL } from "../../utils/formatters";

const ClientesNovoFinanceiroStep = ({
  editingCliente,
  refreshKeyCredito,
  resumoFinanceiro,
  loadingResumo,
  saldoCampanhas,
  setMostrarModalAdicionarCredito,
  setMostrarModalRemoverCredito,
  navigate,
}) => {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <FiDollarSign className="text-green-600" />
        Informacoes financeiras
      </h3>

      <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-green-800 mb-1">
              Saldo de credito
            </p>
            <p className="text-3xl font-bold text-green-600">
              R${" "}
              {editingCliente?.credito
                ? parseFloat(editingCliente.credito).toFixed(2).replace(".", ",")
                : "0,00"}
            </p>
            <p className="text-xs text-green-700 mt-1">
              Disponivel para uso em compras
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-medium disabled:opacity-50"
              disabled={!editingCliente}
              onClick={() => setMostrarModalAdicionarCredito(true)}
            >
              <FiTrendingUp /> Inserir credito
            </button>
            <button
              type="button"
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors text-sm font-medium disabled:opacity-50"
              disabled={!editingCliente}
              onClick={() => setMostrarModalRemoverCredito(true)}
            >
              <FiTrendingDown /> Remover credito
            </button>
          </div>
        </div>
      </div>

      {editingCliente?.id && (
        <ExtratoCredito
          clienteId={editingCliente.id}
          refreshKey={refreshKeyCredito}
        />
      )}

      {editingCliente && saldoCampanhas && (
        <div
          className={`rounded-xl p-4 border flex items-center gap-3 ${
            saldoCampanhas.rank_level === "platinum"
              ? "bg-purple-50 border-purple-300"
              : saldoCampanhas.rank_level === "diamond"
                ? "bg-cyan-50 border-cyan-300"
                : saldoCampanhas.rank_level === "gold"
                  ? "bg-yellow-50 border-yellow-300"
                  : saldoCampanhas.rank_level === "silver"
                    ? "bg-gray-50 border-gray-300"
                    : "bg-amber-50 border-amber-200"
          }`}
        >
          <span className="text-3xl">
            {saldoCampanhas.rank_level === "platinum"
              ? "👑"
              : saldoCampanhas.rank_level === "diamond"
                ? "💎"
                : saldoCampanhas.rank_level === "gold"
                  ? "🥇"
                  : saldoCampanhas.rank_level === "silver"
                    ? "🥈"
                    : "🥉"}
          </span>
          <div className="flex-1">
            <p className="text-xs text-gray-500 font-medium">
              Nivel de fidelidade
            </p>
            <p
              className={`text-lg font-bold ${
                saldoCampanhas.rank_level === "platinum"
                  ? "text-purple-700"
                  : saldoCampanhas.rank_level === "diamond"
                    ? "text-cyan-700"
                    : saldoCampanhas.rank_level === "gold"
                      ? "text-yellow-700"
                      : saldoCampanhas.rank_level === "silver"
                        ? "text-gray-600"
                        : "text-amber-700"
              }`}
            >
              {saldoCampanhas.rank_level === "platinum"
                ? "Platina"
                : saldoCampanhas.rank_level === "diamond"
                  ? "Diamante"
                  : saldoCampanhas.rank_level === "gold"
                    ? "Ouro"
                    : saldoCampanhas.rank_level === "silver"
                      ? "Prata"
                      : "Bronze"}
            </p>
          </div>
          <div className="text-right space-y-0.5">
            {saldoCampanhas.saldo_cashback > 0 && (
              <p className="text-sm font-semibold text-green-700">
                R$ {formatBRL(saldoCampanhas.saldo_cashback)} cashback
              </p>
            )}
            {saldoCampanhas.total_carimbos > 0 && (
              <p className="text-sm text-blue-700">
                {saldoCampanhas.total_carimbos} carimbo(s)
              </p>
            )}
            {saldoCampanhas.cupons_ativos?.length > 0 && (
              <p className="text-sm text-orange-700">
                {saldoCampanhas.cupons_ativos.length} cupom(ns) ativo(s)
              </p>
            )}
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <FiCreditCard />
          Resumo financeiro (ultimos 90 dias)
        </h4>

        {editingCliente ? (
          <div className="space-y-4">
            {loadingResumo ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto"></div>
                <p className="mt-2 text-gray-600 text-sm">
                  Carregando resumo...
                </p>
              </div>
            ) : (
              <>
                {resumoFinanceiro ? (
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                      <p className="text-xs text-gray-600 mb-1">Total comprado</p>
                      <p className="text-2xl font-bold text-blue-600">
                        R${" "}
                        {resumoFinanceiro.total_vendas
                          ?.toFixed(2)
                          .replace(".", ",") || "0,00"}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {resumoFinanceiro.quantidade_vendas || 0} vendas
                      </p>
                    </div>

                    <div
                      className={`rounded-lg p-4 border ${
                        resumoFinanceiro.tem_debitos_vencidos
                          ? "bg-red-50 border-red-300"
                          : resumoFinanceiro.tem_debitos
                            ? "bg-orange-50 border-orange-200"
                            : "bg-green-50 border-green-200"
                      }`}
                    >
                      <p className="text-xs text-gray-600 mb-1">Em aberto</p>
                      <p
                        className={`text-2xl font-bold ${
                          resumoFinanceiro.tem_debitos_vencidos
                            ? "text-red-600"
                            : resumoFinanceiro.tem_debitos
                              ? "text-orange-600"
                              : "text-green-600"
                        }`}
                      >
                        R${" "}
                        {resumoFinanceiro.total_em_aberto
                          ?.toFixed(2)
                          .replace(".", ",") || "0,00"}
                      </p>
                      {resumoFinanceiro.tem_debitos_vencidos && (
                        <p className="text-xs text-red-600 font-semibold mt-1">
                          R${" "}
                          {resumoFinanceiro.total_vencido
                            ?.toFixed(2)
                            .replace(".", ",") || "0,00"}{" "}
                          vencido
                        </p>
                      )}
                    </div>

                    <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                      <p className="text-xs text-gray-600 mb-1">Ticket medio</p>
                      <p className="text-2xl font-bold text-purple-600">
                        R${" "}
                        {resumoFinanceiro.ticket_medio
                          ?.toFixed(2)
                          .replace(".", ",") || "0,00"}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">por compra</p>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <p className="text-xs text-gray-600 mb-1">Ultima compra</p>
                      {resumoFinanceiro.ultima_compra ? (
                        <>
                          <p className="text-2xl font-bold text-gray-700">
                            R${" "}
                            {resumoFinanceiro.ultima_compra.valor
                              ?.toFixed(2)
                              .replace(".", ",") || "0,00"}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {new Date(
                              resumoFinanceiro.ultima_compra.data,
                            ).toLocaleDateString("pt-BR")}{" "}
                            (ha {resumoFinanceiro.ultima_compra.dias_atras} dias)
                          </p>
                        </>
                      ) : (
                        <p className="text-sm text-gray-500 mt-2">
                          Nenhuma compra
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6 text-gray-500">
                    <p className="mb-2">Nenhuma informacao financeira</p>
                    <p className="text-sm">
                      Dados aparecerao apos a primeira venda
                    </p>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() =>
                    navigate(`/clientes/${editingCliente.id}/financeiro`)
                  }
                  className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg transition-all flex items-center justify-center gap-2 font-semibold shadow-md"
                >
                  <FiCreditCard />
                  Ver historico financeiro completo
                  {resumoFinanceiro && (
                    <span className="text-xs bg-white bg-opacity-20 px-2 py-1 rounded">
                      {resumoFinanceiro.total_transacoes_historico || 0} transacoes
                    </span>
                  )}
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <p className="text-blue-800 text-sm">
              Salve o cliente primeiro para visualizar o resumo financeiro
            </p>
          </div>
        )}
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          <strong>Dica:</strong> O credito pode ser gerado automaticamente nas
          devolucoes de produtos e utilizado como forma de pagamento no PDV.
        </p>
      </div>

      {editingCliente && <ClienteSegmentos clienteId={editingCliente.id} />}

      {editingCliente && (
        <ClienteInsights
          clienteId={editingCliente.id}
          cliente={editingCliente}
          metricas={resumoFinanceiro}
        />
      )}

      {editingCliente && editingCliente.celular && (
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FiMessageCircle className="text-green-600" size={24} />
              <h3 className="text-lg font-semibold text-gray-900">WhatsApp</h3>
            </div>
            <button
              type="button"
              onClick={() => {
                const celular = editingCliente.celular.replace(/\D/g, "");
                window.open(`https://wa.me/55${celular}`, "_blank");
              }}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-medium"
            >
              <FiMessageCircle />
              Abrir conversa
            </button>
          </div>

          <WhatsAppHistorico clienteId={editingCliente.id} />
        </div>
      )}

      {editingCliente && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <ClienteTimeline
            clienteId={
              editingCliente.tipo_cadastro === "cliente" ? editingCliente.id : null
            }
            fornecedorId={
              editingCliente.tipo_cadastro === "fornecedor"
                ? editingCliente.id
                : null
            }
            tipo={
              editingCliente.tipo_cadastro === "fornecedor"
                ? "fornecedor"
                : "cliente"
            }
            limit={5}
            showHeader={true}
            onVerMais={() => navigate(`/clientes/${editingCliente.id}/timeline`)}
          />
        </div>
      )}
    </div>
  );
};

export default ClientesNovoFinanceiroStep;
