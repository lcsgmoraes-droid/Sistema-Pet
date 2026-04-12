import {
  AlertTriangle,
  Check,
  Copy,
  History,
  Plus,
  Search,
  User,
  Wallet,
} from "lucide-react";
import { formatBRL, formatMoneyBRL } from "../../utils/formatters";

export default function PDVClienteCard({
  buscarCliente,
  buscarClientePorCodigoExato,
  clientesSugeridos,
  copiadoClienteCampo,
  destaqueVenda,
  modoVisualizacao,
  onAbrirCadastroCliente,
  onAbrirHistoricoCliente,
  onAbrirModalAdicionarCredito,
  onAbrirVendasEmAberto,
  onBuscarClienteChange,
  onCopiarCampoCliente,
  onRemoverCliente,
  onSelecionarCliente,
  onSelecionarPet,
  onTrocarCliente,
  saldoCampanhas,
  vendaAtual,
  vendaGuiaClasses,
  vendasEmAbertoInfo,
}) {
  const saldoCarimbos = Number(saldoCampanhas?.total_carimbos || 0);
  const debitoFidelidade = Math.max(
    Number(saldoCampanhas?.carimbos_em_debito || 0),
    saldoCarimbos < 0 ? Math.abs(saldoCarimbos) : 0,
  );

  return (
    <div
      id="tour-pdv-cliente"
      className={`bg-white rounded-lg shadow-sm border p-6 ${
        destaqueVenda ? vendaGuiaClasses.box : ""
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center">
          <User className="w-5 h-5 mr-2 text-blue-600" />
          Cliente
        </h2>
        {vendaAtual.cliente && !modoVisualizacao && (
          <button
            onClick={onRemoverCliente}
            className="text-sm text-red-600 hover:text-red-700"
          >
            Remover
          </button>
        )}
      </div>

      {!vendaAtual.cliente ? (
        <div className="space-y-3">
          <div className="relative">
            <div className="flex items-center gap-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={buscarCliente}
                  onChange={(e) => onBuscarClienteChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key !== "Enter") return;

                    const clientePorCodigo =
                      buscarClientePorCodigoExato(buscarCliente);
                    if (clientePorCodigo) {
                      e.preventDefault();
                      onSelecionarCliente(clientePorCodigo);
                    }
                  }}
                  placeholder="Digite nome, CPF ou telefone do cliente..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={modoVisualizacao}
                />
                <Search className="w-5 h-5 text-gray-400 absolute right-3 top-1/2 -translate-y-1/2" />
              </div>
              <button
                onClick={onAbrirCadastroCliente}
                disabled={modoVisualizacao}
                className="flex items-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus className="w-5 h-5" />
                <span>Novo</span>
              </button>
            </div>

            {clientesSugeridos.length > 0 && (
              <div className="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {clientesSugeridos.map((cliente) => (
                  <button
                    key={cliente.id}
                    onClick={() => onSelecionarCliente(cliente)}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b last:border-b-0"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-medium text-gray-900 flex-1">
                        {cliente.nome}
                      </div>
                      {cliente.codigo && (
                        <div className="text-xs font-mono bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded flex-shrink-0">
                          #{cliente.codigo}
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-gray-500">
                      {cliente.cpf && `CPF: ${cliente.cpf}`}
                      {cliente.telefone && ` • ${cliente.telefone}`}
                    </div>
                    {cliente.pets && cliente.pets.length > 0 && (
                      <div className="text-xs text-blue-600 mt-1">
                        {cliente.pets.length} pet(s)
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
          {buscarCliente.length >= 2 && clientesSugeridos.length === 0 && (
            <div className="text-sm text-gray-500 text-center py-2">
              Nenhum cliente encontrado
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="font-semibold text-blue-900">
                  {vendaAtual.cliente.nome}
                </div>
                <div className="text-sm text-blue-700 mt-1 space-y-1">
                  <div>
                    {vendaAtual.cliente.cpf &&
                      `CPF: ${vendaAtual.cliente.cpf}`}
                  </div>
                  {(vendaAtual.cliente.codigo || vendaAtual.cliente.id) && (
                    <div className="flex items-center gap-2">
                      <span>
                        Código: {vendaAtual.cliente.codigo || vendaAtual.cliente.id}
                      </span>
                      <button
                        onClick={() =>
                          onCopiarCampoCliente(
                            vendaAtual.cliente.codigo || vendaAtual.cliente.id,
                            "codigo",
                          )
                        }
                        className="text-blue-700 hover:text-blue-900"
                        title="Copiar código do cliente"
                      >
                        {copiadoClienteCampo === "codigo" ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  )}
                  {(vendaAtual.cliente.telefone ||
                    vendaAtual.cliente.celular ||
                    vendaAtual.cliente.whatsapp) && (
                    <div className="flex items-center gap-2">
                      <span>
                        Tel:{" "}
                        {vendaAtual.cliente.telefone ||
                          vendaAtual.cliente.celular ||
                          vendaAtual.cliente.whatsapp}
                      </span>
                      <button
                        onClick={() =>
                          onCopiarCampoCliente(
                            vendaAtual.cliente.telefone ||
                              vendaAtual.cliente.celular ||
                              vendaAtual.cliente.whatsapp,
                            "telefone",
                          )
                        }
                        className="text-blue-700 hover:text-blue-900"
                        title="Copiar telefone do cliente"
                      >
                        {copiadoClienteCampo === "telefone" ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {vendaAtual.cliente.credito > 0 && (
              <div className="mt-3 pt-3 border-t border-blue-300">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wallet className="w-4 h-4 text-green-600" />
                    <span className="text-sm font-medium text-gray-700">
                      Crédito Disponível:
                    </span>
                  </div>
                  <span className="text-lg font-bold text-green-600">
                    {formatMoneyBRL(vendaAtual.cliente.credito || 0)}
                  </span>
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  💡 Este crédito pode ser usado como forma de pagamento
                </p>
              </div>
            )}

            {vendasEmAbertoInfo && vendasEmAbertoInfo.total_vendas > 0 && (
              <div className="mt-3 pt-3 border-t border-blue-300">
                <div className="flex items-center justify-between p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-yellow-600" />
                    <div>
                      <div className="text-sm font-medium text-yellow-900">
                        {vendasEmAbertoInfo.total_vendas} venda(s) em aberto
                      </div>
                      <div className="text-xs text-yellow-700">
                        Total:{" "}
                        {formatMoneyBRL(vendasEmAbertoInfo.total_em_aberto)}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={onAbrirVendasEmAberto}
                    className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-xs font-medium rounded transition-colors"
                  >
                    Ver Vendas
                  </button>
                </div>
              </div>
            )}

            {saldoCampanhas &&
              (saldoCampanhas.saldo_cashback > 0 ||
                saldoCarimbos > 0 ||
                debitoFidelidade > 0 ||
                saldoCampanhas.cupons_ativos?.length > 0 ||
                (saldoCampanhas.rank_level &&
                  saldoCampanhas.rank_level !== "bronze")) && (
                <div className="mt-3 pt-3 border-t border-blue-300 space-y-1.5">
                  {saldoCampanhas.rank_level &&
                    saldoCampanhas.rank_level !== "bronze" && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-blue-800">
                          🏆 Nível fidelidade:
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                            saldoCampanhas.rank_level === "platinum"
                              ? "bg-purple-100 text-purple-800"
                              : saldoCampanhas.rank_level === "diamond"
                                ? "bg-cyan-100 text-cyan-800"
                                : saldoCampanhas.rank_level === "gold"
                                  ? "bg-yellow-100 text-yellow-800"
                                  : "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {saldoCampanhas.rank_level === "platinum"
                            ? "👑 Platina"
                            : saldoCampanhas.rank_level === "diamond"
                              ? "💎 Diamante"
                              : saldoCampanhas.rank_level === "gold"
                                ? "🥇 Ouro"
                                : "🥈 Prata"}
                        </span>
                      </div>
                    )}
                  {saldoCarimbos > 0 && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-blue-800">
                        🏷️ Carimbos fidelidade:
                      </span>
                      <span className="font-semibold text-blue-900">
                        {saldoCarimbos} carimbo(s)
                      </span>
                    </div>
                  )}
                  {debitoFidelidade > 0 && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-blue-800">
                        Debito fidelidade:
                      </span>
                      <span className="font-semibold text-red-600">
                        {debitoFidelidade} carimbo(s)
                      </span>
                    </div>
                  )}
                  {saldoCampanhas.saldo_cashback > 0 && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-blue-800">
                        💰 Cashback acumulado:
                      </span>
                      <span className="font-semibold text-green-700">
                        R$ {formatBRL(saldoCampanhas.saldo_cashback)}
                      </span>
                    </div>
                  )}
                  {saldoCampanhas.cupons_ativos?.length > 0 && (
                    <div className="flex items-center flex-wrap gap-1 text-sm">
                      <span className="text-blue-800">🎟️ Cupons:</span>
                      {saldoCampanhas.cupons_ativos.map((c) => (
                        <span
                          key={c.code}
                          className="px-1.5 py-0.5 bg-yellow-100 border border-yellow-300 rounded text-xs font-mono text-yellow-800"
                        >
                          {c.code}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

            <div className="mt-3 pt-3 border-t border-blue-300 flex gap-2 flex-wrap">
              <button
                onClick={onAbrirHistoricoCliente}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <History className="w-4 h-4" />
                Histórico
              </button>
              {!modoVisualizacao && (
                <button
                  onClick={onAbrirModalAdicionarCredito}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  <Wallet className="w-4 h-4" />
                  Inserir Crédito
                </button>
              )}
              {!modoVisualizacao && (
                <button
                  onClick={onTrocarCliente}
                  className="px-4 py-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
                >
                  Trocar
                </button>
              )}
            </div>
          </div>

          {vendaAtual.cliente.pets && vendaAtual.cliente.pets.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Pet (opcional)
              </label>
              <select
                value={vendaAtual.pet?.id || ""}
                onChange={(e) => {
                  const pet = vendaAtual.cliente.pets.find(
                    (item) => item.id === parseInt(e.target.value),
                  );
                  onSelecionarPet(pet || null);
                }}
                disabled={modoVisualizacao}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
              >
                <option value="">Sem pet específico</option>
                {vendaAtual.cliente.pets.map((pet) => (
                  <option key={pet.id} value={pet.id}>
                    {pet.codigo} - {pet.nome} ({pet.especie}
                    {pet.raca && ` - ${pet.raca}`})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
