import {
  FiCreditCard,
  FiDollarSign,
  FiMessageCircle,
  FiTrendingDown,
  FiTrendingUp,
} from "react-icons/fi";
import ActionButton from "../ui/ActionButton";
import ClienteInsights from "../ClienteInsights";
import { ClienteSegmentos } from "../ClienteSegmentos";
import ClienteTimeline from "../ClienteTimeline";
import ExtratoCredito from "../ExtratoCredito";
import WhatsAppHistorico from "../WhatsAppHistorico";
import { formatBRL } from "../../utils/formatters";

const RANK_INFO = {
  platinum: { emoji: "👑", label: "Platina", classe: "bg-purple-50 border-purple-300 text-purple-700" },
  diamond: { emoji: "💎", label: "Diamante", classe: "bg-cyan-50 border-cyan-300 text-cyan-700" },
  gold: { emoji: "🥇", label: "Ouro", classe: "bg-yellow-50 border-yellow-300 text-yellow-700" },
  silver: { emoji: "🥈", label: "Prata", classe: "bg-gray-50 border-gray-300 text-gray-600" },
  bronze: { emoji: "🥉", label: "Bronze", classe: "bg-amber-50 border-amber-200 text-amber-700" },
};

export default function ClientePessoaFinanceiroTab({
  cliente,
  loadingResumo,
  navigate,
  refreshKeyCredito,
  resumoFinanceiro,
  saldoCampanhas,
  setMostrarModalAdicionarCredito,
  setMostrarModalRemoverCredito,
}) {
  const rank = saldoCampanhas ? RANK_INFO[saldoCampanhas.rank_level] || RANK_INFO.bronze : null;

  return (
    <div className="space-y-6">
      <div className="rounded-xl border-2 border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="mb-1 text-sm font-medium text-green-800">Saldo de crédito</p>
            <p className="text-3xl font-bold text-green-600">
              R$ {cliente?.credito ? parseFloat(cliente.credito).toFixed(2).replace(".", ",") : "0,00"}
            </p>
            <p className="mt-1 text-xs text-green-700">Disponível para uso em compras</p>
          </div>
          <div className="flex gap-2">
            <ActionButton
              icon={FiTrendingUp}
              intent="create"
              onClick={() => setMostrarModalAdicionarCredito(true)}
            >
              Inserir crédito
            </ActionButton>
            <ActionButton
              icon={FiTrendingDown}
              intent="delete"
              onClick={() => setMostrarModalRemoverCredito(true)}
            >
              Remover crédito
            </ActionButton>
          </div>
        </div>
      </div>

      <ExtratoCredito clienteId={cliente.id} refreshKey={refreshKeyCredito} />

      {rank ? (
        <div className={`flex items-center gap-3 rounded-xl border p-4 ${rank.classe}`}>
          <span className="text-3xl">{rank.emoji}</span>
          <div className="flex-1">
            <p className="text-xs font-medium text-gray-500">Nível de fidelidade</p>
            <p className="text-lg font-bold">{rank.label}</p>
          </div>
          <div className="space-y-0.5 text-right">
            {saldoCampanhas.saldo_cashback > 0 ? (
              <p className="text-sm font-semibold text-green-700">
                R$ {formatBRL(saldoCampanhas.saldo_cashback)} cashback
              </p>
            ) : null}
            {saldoCampanhas.total_carimbos > 0 ? (
              <p className="text-sm text-blue-700">{saldoCampanhas.total_carimbos} carimbo(s)</p>
            ) : null}
            {saldoCampanhas.cupons_ativos?.length > 0 ? (
              <p className="text-sm text-orange-700">
                {saldoCampanhas.cupons_ativos.length} cupom(ns) ativo(s)
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h4 className="text-md mb-4 flex items-center gap-2 font-semibold text-gray-800">
          <FiCreditCard />
          Resumo financeiro (últimos 90 dias)
        </h4>

        {loadingResumo ? (
          <div className="py-8 text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-purple-600" />
            <p className="mt-2 text-sm text-gray-600">Carregando resumo...</p>
          </div>
        ) : (
          <>
            {resumoFinanceiro ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                  <p className="mb-1 text-xs text-gray-600">Total comprado</p>
                  <p className="text-2xl font-bold text-blue-600">
                    R$ {resumoFinanceiro.total_vendas?.toFixed(2).replace(".", ",") || "0,00"}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {resumoFinanceiro.quantidade_vendas || 0} vendas
                  </p>
                </div>

                <div
                  className={`rounded-lg border p-4 ${
                    resumoFinanceiro.tem_debitos_vencidos
                      ? "border-red-300 bg-red-50"
                      : resumoFinanceiro.tem_debitos
                        ? "border-orange-200 bg-orange-50"
                        : "border-green-200 bg-green-50"
                  }`}
                >
                  <p className="mb-1 text-xs text-gray-600">Em aberto</p>
                  <p
                    className={`text-2xl font-bold ${
                      resumoFinanceiro.tem_debitos_vencidos
                        ? "text-red-600"
                        : resumoFinanceiro.tem_debitos
                          ? "text-orange-600"
                          : "text-green-600"
                    }`}
                  >
                    R$ {resumoFinanceiro.total_em_aberto?.toFixed(2).replace(".", ",") || "0,00"}
                  </p>
                  {resumoFinanceiro.tem_debitos_vencidos ? (
                    <p className="mt-1 text-xs font-semibold text-red-600">
                      R$ {resumoFinanceiro.total_vencido?.toFixed(2).replace(".", ",") || "0,00"}{" "}
                      vencido
                    </p>
                  ) : null}
                </div>

                <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
                  <p className="mb-1 text-xs text-gray-600">Ticket médio</p>
                  <p className="text-2xl font-bold text-purple-600">
                    R$ {resumoFinanceiro.ticket_medio?.toFixed(2).replace(".", ",") || "0,00"}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">por compra</p>
                </div>

                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <p className="mb-1 text-xs text-gray-600">Última compra</p>
                  {resumoFinanceiro.ultima_compra ? (
                    <>
                      <p className="text-2xl font-bold text-gray-700">
                        R${" "}
                        {resumoFinanceiro.ultima_compra.valor?.toFixed(2).replace(".", ",") ||
                          "0,00"}
                      </p>
                      <p className="mt-1 text-xs text-gray-500">
                        {new Date(resumoFinanceiro.ultima_compra.data).toLocaleDateString("pt-BR")}{" "}
                        (há {resumoFinanceiro.ultima_compra.dias_atras} dias)
                      </p>
                    </>
                  ) : (
                    <p className="mt-2 text-sm text-gray-500">Nenhuma compra</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-gray-500">
                <p className="mb-2">Nenhuma informação financeira</p>
                <p className="text-sm">Dados aparecerão após a primeira venda</p>
              </div>
            )}

            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              <ActionButton
                icon={FiCreditCard}
                intent="info"
                onClick={() => navigate(`/clientes/${cliente.id}/financeiro`)}
              >
                Ver histórico financeiro completo
              </ActionButton>
              <ActionButton
                icon={FiDollarSign}
                intent="info"
                tone="outline"
                onClick={() =>
                  navigate(
                    `/financeiro/contas-receber?cliente_id=${cliente.id}&filtro=em_aberto&periodo=todos`,
                  )
                }
              >
                Ver parcelas em aberto
              </ActionButton>
            </div>
          </>
        )}
      </div>

      <ClienteSegmentos clienteId={cliente.id} />

      <ClienteInsights clienteId={cliente.id} cliente={cliente} metricas={resumoFinanceiro} />

      {cliente.celular ? (
        <div className="rounded-xl border-2 border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FiMessageCircle className="text-green-600" size={24} />
              <h3 className="text-lg font-semibold text-gray-900">WhatsApp</h3>
            </div>
            <ActionButton
              icon={FiMessageCircle}
              intent="create"
              onClick={() => {
                const celular = cliente.celular.replace(/\D/g, "");
                window.open(`https://wa.me/55${celular}`, "_blank");
              }}
            >
              Abrir conversa
            </ActionButton>
          </div>

          <WhatsAppHistorico clienteId={cliente.id} />
        </div>
      ) : null}

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <ClienteTimeline
          clienteId={cliente.tipo_cadastro === "cliente" ? cliente.id : null}
          fornecedorId={cliente.tipo_cadastro === "fornecedor" ? cliente.id : null}
          tipo={cliente.tipo_cadastro === "fornecedor" ? "fornecedor" : "cliente"}
          limit={5}
          showHeader
          onVerMais={() => navigate(`/clientes/${cliente.id}/timeline`)}
        />
      </div>
    </div>
  );
}
