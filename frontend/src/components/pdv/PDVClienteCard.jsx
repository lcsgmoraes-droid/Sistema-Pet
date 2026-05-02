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
import ActionButton from "../ui/ActionButton";
import Panel from "../ui/Panel";

function CopyButton({ active, onClick, title }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex h-4 w-4 items-center justify-center rounded text-blue-700 hover:bg-blue-100 hover:text-blue-900"
      title={title}
    >
      {active ? (
        <Check className="h-3.5 w-3.5 text-green-600" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

function ClienteInfoLine({ label, value, copyKey, copiedKey, onCopy }) {
  if (!value) return null;

  return (
    <div className="inline-flex min-w-0 items-center gap-1">
      <span className="text-blue-700">{label}:</span>
      <span className="truncate text-blue-800">{value}</span>
      {copyKey && (
        <CopyButton
          active={copiedKey === copyKey}
          onClick={() => onCopy(value, copyKey)}
          title={`Copiar ${label.toLowerCase()}`}
        />
      )}
    </div>
  );
}

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
  saldoCampanhas,
  vendaAtual,
  vendaGuiaClasses,
  vendasEmAbertoInfo,
}) {
  const cliente = vendaAtual.cliente;
  const saldoCarimbos = Number(saldoCampanhas?.total_carimbos || 0);
  const debitoFidelidade = Math.max(
    Number(saldoCampanhas?.carimbos_em_debito || 0),
    saldoCarimbos < 0 ? Math.abs(saldoCarimbos) : 0,
  );
  const creditoCliente = Number(cliente?.credito || 0);
  const cuponsAtivos = saldoCampanhas?.cupons_ativos || [];
  const totalVendasAbertas = Number(vendasEmAbertoInfo?.total_vendas || 0);
  const telefoneCliente =
    cliente?.telefone || cliente?.celular || cliente?.whatsapp || "";
  const codigoCliente = cliente?.codigo || cliente?.id || "";
  const nivelFidelidade = saldoCampanhas?.rank_level || "bronze";
  const cashback = Number(saldoCampanhas?.saldo_cashback || 0);

  return (
    <Panel
      id="tour-pdv-cliente"
      padding={cliente ? "sm" : "lg"}
      className={destaqueVenda ? vendaGuiaClasses.box : ""}
    >
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <h2 className="flex items-center text-base font-semibold text-gray-900">
          <User className="mr-2 h-4 w-4 text-blue-600" />
          Cliente
        </h2>
        {cliente && !modoVisualizacao && (
          <ActionButton
            onClick={onRemoverCliente}
            intent="delete"
            tone="ghost"
            size="xs"
          >
            Remover
          </ActionButton>
        )}
      </div>

      {!cliente ? (
        <div className="space-y-3">
          <div className="relative">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
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
                  className="h-9 w-full rounded-lg border border-gray-300 px-3 pr-9 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500"
                  disabled={modoVisualizacao}
                />
                <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              </div>
              <ActionButton
                onClick={onAbrirCadastroCliente}
                disabled={modoVisualizacao}
                icon={Plus}
                intent="create"
                size="md"
                className="whitespace-nowrap"
              >
                <span>Novo</span>
              </ActionButton>
            </div>

            {clientesSugeridos.length > 0 && (
              <div className="absolute z-10 mt-2 max-h-60 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg">
                {clientesSugeridos.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onSelecionarCliente(item)}
                    className="w-full border-b px-4 py-3 text-left last:border-b-0 hover:bg-gray-50"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 font-medium text-gray-900">
                        {item.nome}
                      </div>
                      {item.codigo && (
                        <div className="flex-shrink-0 rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-600">
                          #{item.codigo}
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-gray-500">
                      {item.cpf && `CPF: ${item.cpf}`}
                      {item.telefone && ` - ${item.telefone}`}
                    </div>
                    {item.pets && item.pets.length > 0 && (
                      <div className="mt-1 text-xs text-blue-600">
                        {item.pets.length} pet(s)
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {buscarCliente.length >= 2 && clientesSugeridos.length === 0 && (
            <div className="py-2 text-center text-sm text-gray-500">
              Nenhum cliente encontrado
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <div className="grid grid-cols-1 overflow-hidden rounded-lg border border-blue-200 bg-blue-50 text-sm md:grid-cols-3">
            <div className="min-w-0 border-b border-blue-200 px-3 py-3 md:border-b-0">
              <div className="truncate font-semibold text-blue-950">
                {cliente.nome}
              </div>
              <div className="mt-1.5 flex flex-col gap-1 text-xs">
                <ClienteInfoLine label="CPF" value={cliente.cpf} />
                <ClienteInfoLine
                  label="Codigo"
                  value={codigoCliente}
                  copyKey="codigo"
                  copiedKey={copiadoClienteCampo}
                  onCopy={onCopiarCampoCliente}
                />
                <ClienteInfoLine
                  label="Tel"
                  value={telefoneCliente}
                  copyKey="telefone"
                  copiedKey={copiadoClienteCampo}
                  onCopy={onCopiarCampoCliente}
                />
              </div>
            </div>

            <div className="min-w-0 border-b border-blue-200 px-3 py-3 md:border-b-0 md:border-r">
              <div className="space-y-1.5 text-xs text-blue-800">
                <div className="flex items-center justify-between gap-3">
                  <span>Nivel fidelidade:</span>
                  <span className="font-semibold capitalize text-blue-950">
                    {nivelFidelidade}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>Carimbos fidelidade:</span>
                  <span className="font-semibold text-blue-950">
                    {saldoCarimbos} carimbo(s)
                  </span>
                </div>
                {debitoFidelidade > 0 && (
                  <div className="flex items-center justify-between gap-3">
                    <span>Debito fidelidade:</span>
                    <span className="font-semibold text-red-600">
                      {debitoFidelidade} carimbo(s)
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between gap-3">
                  <span>Cashback acumulado:</span>
                  <span className="font-semibold text-green-700">
                    R$ {formatBRL(cashback)}
                  </span>
                </div>
                <div className="flex items-start justify-between gap-3">
                  <span className="pt-0.5">Cupons:</span>
                  <span className="flex min-w-0 flex-wrap justify-end gap-1">
                    {cuponsAtivos.length > 0 ? (
                      cuponsAtivos.map((c) => {
                        const codigoCupom = String(
                          c.code || c.codigo || c.id || "",
                        );
                        if (!codigoCupom) return null;
                        const chaveCopia = `cupom-${codigoCupom}`;

                        return (
                          <span
                            key={codigoCupom}
                            className="inline-flex max-w-full items-center gap-1 rounded border border-yellow-300 bg-yellow-100 px-1.5 py-0.5 font-mono text-[11px] text-yellow-800"
                          >
                            <span className="truncate">{codigoCupom}</span>
                            <button
                              type="button"
                              onClick={() =>
                                onCopiarCampoCliente(codigoCupom, chaveCopia)
                              }
                              className="inline-flex h-4 w-4 items-center justify-center rounded text-yellow-700 hover:bg-yellow-200 hover:text-yellow-900"
                              title="Copiar cupom"
                            >
                              {copiadoClienteCampo === chaveCopia ? (
                                <Check className="h-3 w-3 text-green-600" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </button>
                          </span>
                        );
                      })
                    ) : (
                      <span className="text-blue-500">-</span>
                    )}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex min-w-0 flex-col gap-2 bg-blue-50 px-3 py-3">
              <div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-semibold text-blue-950">
                  <span className="inline-flex items-center gap-1.5">
                    <Wallet className="h-4 w-4 text-green-600" />
                    Credito Disponivel:
                  </span>
                  <span className="text-lg font-bold leading-none text-green-700">
                    {formatMoneyBRL(creditoCliente)}
                  </span>
                </div>
                <div className="mt-1 text-xs text-blue-700">
                  Este credito pode ser usado como forma de pagamento
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {totalVendasAbertas > 0 ? (
              <div
                className="flex min-h-[46px] min-w-0 flex-none items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-800"
                style={{ width: "560px", maxWidth: "calc(100% - 300px)" }}
              >
                <div className="flex min-w-0 items-center gap-2">
                  <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-600" />
                  <div className="min-w-0">
                    <div className="text-sm font-semibold leading-tight">
                      {totalVendasAbertas} venda(s) em aberto
                    </div>
                    <div className="truncate leading-tight">
                      Total:{" "}
                      {formatMoneyBRL(vendasEmAbertoInfo?.total_em_aberto || 0)}
                    </div>
                  </div>
                </div>
                <ActionButton
                  onClick={onAbrirVendasEmAberto}
                  intent="warning"
                  size="sm"
                  className="min-w-[128px]"
                >
                  Ver Vendas
                </ActionButton>
              </div>
            ) : (
              <div />
            )}

            <div className="min-w-0 flex-1" />

            <div className="flex min-h-[46px] flex-none items-center justify-end gap-2">
              <ActionButton
                onClick={onAbrirHistoricoCliente}
                icon={History}
                intent="neutral"
                tone="soft"
                size="sm"
                className="min-w-[132px]"
              >
                Historico
              </ActionButton>
              {!modoVisualizacao && (
                <ActionButton
                  onClick={onAbrirModalAdicionarCredito}
                  icon={Wallet}
                  intent="create"
                  size="sm"
                  className="min-w-[150px]"
                >
                  Inserir Credito
                </ActionButton>
              )}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Pet (opcional)
            </label>
            <select
              value={vendaAtual.pet?.id || ""}
              onChange={(e) => {
                const pet = cliente.pets?.find(
                  (item) => item.id === parseInt(e.target.value, 10),
                );
                onSelecionarPet(pet || null);
              }}
              disabled={modoVisualizacao}
              className="h-9 w-full rounded-lg border border-gray-300 bg-white px-3 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-50"
            >
              <option value="">Sem pet especifico</option>
              {cliente.pets?.map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.codigo} - {pet.nome} ({pet.especie}
                  {pet.raca && ` - ${pet.raca}`})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </Panel>
  );
}
