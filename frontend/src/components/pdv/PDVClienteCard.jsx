import { AlertTriangle, Check, Copy, History, Plus, User, Wallet } from "lucide-react";
import { useLocation } from "react-router-dom";
import { formatBRL, formatMoneyBRL } from "../../utils/formatters";
import { getClienteAlertasPdvAtivos } from "../../utils/clienteAlertasPdv";
import { buildPdvCouponTooltip } from "../../utils/pdvCouponTooltip";
import { buildReturnTo } from "../../utils/petReturnFlow";
import PessoaSelector from "../clientes/PessoaSelector";
import ActionButton from "../ui/ActionButton";
import CustomerIdentity from "../ui/CustomerIdentity";
import EntityCard from "../ui/EntityCard";
import Panel from "../ui/Panel";
import PetSelector from "../pets/PetSelector";

function CopyButton({ active, onClick, title }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex h-4 w-4 items-center justify-center rounded text-blue-700 hover:bg-blue-100 hover:text-blue-900"
      title={title}
    >
      {active ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

function ClienteInfoLine({ label, value, copyKey, copiedKey, onCopy }) {
  return (
    <div className="grid min-h-[20px] grid-cols-[48px_minmax(0,1fr)_18px] items-center gap-1">
      <span className="text-blue-700">{label}:</span>
      <span className="truncate text-blue-800">
        {value || (
          <span aria-hidden="true" className="invisible">
            -
          </span>
        )}
      </span>
      {copyKey && value ? (
        <CopyButton
          active={copiedKey === copyKey}
          onClick={() => onCopy(value, copyKey)}
          title={`Copiar ${label.toLowerCase()}`}
        />
      ) : (
        <span aria-hidden="true" />
      )}
    </div>
  );
}

function ClienteLookup({
  buscarCliente,
  buscarClientePorCodigoExato,
  clientesSugeridos,
  modoVisualizacao,
  onAbrirCadastroCliente,
  onBuscarClienteChange,
  onSelecionarCliente,
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <PessoaSelector
          className="w-full sm:flex-1"
          disabled={modoVisualizacao}
          minChars={0}
          onChange={onBuscarClienteChange}
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;

            const clientePorCodigo = buscarClientePorCodigoExato(buscarCliente);
            if (clientePorCodigo) {
              e.preventDefault();
              onSelecionarCliente(clientePorCodigo);
            }
          }}
          onSelect={onSelecionarCliente}
          placeholder="Digite nome, CPF ou telefone do cliente..."
          showSuggestions={clientesSugeridos.length > 0}
          suggestions={clientesSugeridos}
          value={buscarCliente}
        />
        <ActionButton
          onClick={onAbrirCadastroCliente}
          disabled={modoVisualizacao}
          icon={Plus}
          intent="create"
          size="md"
          className="w-full whitespace-nowrap sm:w-auto"
        >
          <span>Novo</span>
        </ActionButton>
      </div>

      {buscarCliente.length >= 2 && clientesSugeridos.length === 0 && (
        <div className="py-2 text-center text-sm text-gray-500">Nenhum cliente encontrado</div>
      )}
    </div>
  );
}

function ClienteCupomBadgeList({ copiadoClienteCampo, cuponsAtivos, onCopiarCampoCliente }) {
  if (cuponsAtivos.length === 0) {
    return <span className="text-blue-500">-</span>;
  }

  return cuponsAtivos.map((c) => {
    const codigoCupom = String(c.code || c.codigo || c.id || "");
    if (!codigoCupom) return null;

    const chaveCopia = `cupom-${codigoCupom}`;
    const tooltipCupom = buildPdvCouponTooltip(c);

    return (
      <span
        key={codigoCupom}
        tabIndex={0}
        title={tooltipCupom}
        aria-label={tooltipCupom}
        className="inline-flex max-w-full items-center gap-1 rounded border border-yellow-300 bg-yellow-100 px-1.5 py-0.5 font-mono text-[11px] text-yellow-800"
      >
        <span className="truncate">{codigoCupom}</span>
        <button
          type="button"
          onClick={() => onCopiarCampoCliente(codigoCupom, chaveCopia)}
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
  });
}

function ClienteFidelidadeResumo({
  cashback,
  copiadoClienteCampo,
  cuponsAtivos,
  debitoFidelidade,
  nivelFidelidade,
  onCopiarCampoCliente,
  saldoCarimbos,
}) {
  return (
    <div className="space-y-1.5 text-xs text-blue-800">
      <div className="flex items-center justify-between gap-3">
        <span>Nivel fidelidade:</span>
        <span className="font-semibold capitalize text-blue-950">{nivelFidelidade}</span>
      </div>
      <div className="flex items-center justify-between gap-3">
        <span>Carimbos fidelidade:</span>
        <span className="font-semibold text-blue-950">{saldoCarimbos} carimbo(s)</span>
      </div>
      {debitoFidelidade > 0 && (
        <div className="flex items-center justify-between gap-3">
          <span>Debito fidelidade:</span>
          <span className="font-semibold text-red-600">{debitoFidelidade} carimbo(s)</span>
        </div>
      )}
      <div className="flex items-center justify-between gap-3">
        <span>Cashback acumulado:</span>
        <span className="font-semibold text-green-700">R$ {formatBRL(cashback)}</span>
      </div>
      <div className="flex items-start justify-between gap-3">
        <span className="pt-0.5">Cupons:</span>
        <span className="flex min-w-0 flex-wrap justify-end gap-1">
          <ClienteCupomBadgeList
            copiadoClienteCampo={copiadoClienteCampo}
            cuponsAtivos={cuponsAtivos}
            onCopiarCampoCliente={onCopiarCampoCliente}
          />
        </span>
      </div>
    </div>
  );
}

function ClienteCreditoResumo({ creditoCliente }) {
  return (
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
  );
}

function alertaPdvClasses(prioridade) {
  if (prioridade === "importante") {
    return "border-red-200 bg-red-50 text-red-900";
  }
  if (prioridade === "info") {
    return "border-blue-200 bg-blue-50 text-blue-900";
  }
  return "border-amber-200 bg-amber-50 text-amber-900";
}

function ClienteAlertasPdv({ cliente }) {
  const alertas = getClienteAlertasPdvAtivos(cliente);

  if (alertas.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {alertas.map((alerta, index) => (
        <div
          key={`${alerta.titulo}-${index}`}
          className={`rounded-lg border px-3 py-2 text-sm ${alertaPdvClasses(alerta.prioridade)}`}
        >
          <div className="flex min-w-0 items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <div className="min-w-0">
              <div className="font-semibold leading-tight">{alerta.titulo}</div>
              {alerta.mensagem && (
                <div className="mt-0.5 whitespace-pre-wrap break-words text-xs leading-snug">
                  {alerta.mensagem}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ClienteResumoSelecionado({
  cashback,
  cliente,
  codigoCliente,
  copiadoClienteCampo,
  creditoCliente,
  cuponsAtivos,
  debitoFidelidade,
  nivelFidelidade,
  onCopiarCampoCliente,
  saldoCarimbos,
  telefoneCliente,
}) {
  return (
    <EntityCard
      compact
      className="overflow-hidden border-blue-200 bg-blue-50 text-sm shadow-none"
      bodyClassName="grid grid-cols-1 md:grid-cols-[1fr_1.05fr_1fr]"
    >
      <div className="min-w-0 border-b border-blue-200 px-3 py-3 md:border-b-0 md:border-r">
        <CustomerIdentity
          className="max-w-full"
          code={codigoCliente}
          codeClassName="border border-blue-200 bg-white/80 text-blue-800"
          codeLabel="Codigo"
          customer={cliente}
          fallback={`Cliente #${codigoCliente || "-"}`}
          nameClassName="font-semibold text-blue-950"
          nameWrapperClassName="max-w-full"
        />
        <div className="mt-1.5 flex flex-col gap-1 text-xs">
          <ClienteInfoLine label="CPF" value={cliente.cpf} />
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
        <ClienteFidelidadeResumo
          cashback={cashback}
          copiadoClienteCampo={copiadoClienteCampo}
          cuponsAtivos={cuponsAtivos}
          debitoFidelidade={debitoFidelidade}
          nivelFidelidade={nivelFidelidade}
          onCopiarCampoCliente={onCopiarCampoCliente}
          saldoCarimbos={saldoCarimbos}
        />
      </div>

      <div className="flex min-w-0 flex-col gap-2 bg-blue-50 px-3 py-3">
        <ClienteCreditoResumo creditoCliente={creditoCliente} />
      </div>
    </EntityCard>
  );
}

function ClienteAcoesResumo({
  modoVisualizacao,
  onAbrirHistoricoCliente,
  onAbrirModalAdicionarCredito,
  onAbrirVendasEmAberto,
  totalVendasAbertas,
  vendasEmAbertoInfo,
}) {
  return (
    <div className="flex flex-col gap-2 md:flex-row md:items-center">
      {totalVendasAbertas > 0 ? (
        <div className="flex min-h-[46px] w-full min-w-0 flex-col gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 sm:flex-row sm:items-center sm:justify-between md:w-auto md:flex-none">
          <div className="flex min-w-0 items-center gap-2">
            <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-600" />
            <div className="min-w-0">
              <div className="text-sm font-semibold leading-tight">
                {totalVendasAbertas} venda(s) em aberto
              </div>
              <div className="truncate leading-tight">
                Total: {formatMoneyBRL(vendasEmAbertoInfo?.total_em_aberto || 0)}
              </div>
            </div>
          </div>
          <ActionButton
            onClick={onAbrirVendasEmAberto}
            intent="warning"
            size="sm"
            className="w-full sm:w-auto sm:min-w-[128px]"
          >
            Ver Vendas
          </ActionButton>
        </div>
      ) : (
        <div />
      )}

      <div className="hidden min-w-0 flex-1 md:block" />

      <div className="grid min-h-[46px] w-full grid-cols-1 gap-2 sm:grid-cols-2 md:flex md:w-auto md:flex-none md:items-center md:justify-end">
        <ActionButton
          onClick={onAbrirHistoricoCliente}
          icon={History}
          intent="neutral"
          tone="soft"
          size="sm"
          className="w-full md:w-auto md:min-w-[132px]"
        >
          Historico
        </ActionButton>
        {!modoVisualizacao && (
          <ActionButton
            onClick={onAbrirModalAdicionarCredito}
            icon={Wallet}
            intent="create"
            size="sm"
            className="w-full md:w-auto md:min-w-[150px]"
          >
            Inserir Credito
          </ActionButton>
        )}
      </div>
    </div>
  );
}

function ClientePetSelector({ cliente, modoVisualizacao, onSelecionarPet, vendaAtual }) {
  const location = useLocation();
  const retornoNovoPet = buildReturnTo(location.pathname, location.search, {
    novo_pet_id: null,
    novo_pet_nome: null,
    tutor_id: cliente?.id,
    tutor_nome: cliente?.nome,
  });

  return (
    <PetSelector
      tutorSelecionado={cliente}
      petId={vendaAtual.pet?.id || ""}
      pets={cliente.pets}
      disabled={modoVisualizacao}
      allowEmpty
      showNovoPetButton={!modoVisualizacao}
      returnTo={retornoNovoPet}
      petLabel="Pet (opcional)"
      placeholder="Sem pet especifico"
      emptyOptionLabel="Sem pet especifico"
      onSelectPet={onSelecionarPet}
    />
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
  const telefoneCliente = cliente?.telefone || cliente?.celular || cliente?.whatsapp || "";
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
          <ActionButton onClick={onRemoverCliente} intent="delete" tone="ghost" size="xs">
            Remover
          </ActionButton>
        )}
      </div>

      {!cliente ? (
        <ClienteLookup
          buscarCliente={buscarCliente}
          buscarClientePorCodigoExato={buscarClientePorCodigoExato}
          clientesSugeridos={clientesSugeridos}
          modoVisualizacao={modoVisualizacao}
          onAbrirCadastroCliente={onAbrirCadastroCliente}
          onBuscarClienteChange={onBuscarClienteChange}
          onSelecionarCliente={onSelecionarCliente}
        />
      ) : (
        <div className="space-y-2">
          <ClienteResumoSelecionado
            cashback={cashback}
            cliente={cliente}
            codigoCliente={codigoCliente}
            copiadoClienteCampo={copiadoClienteCampo}
            creditoCliente={creditoCliente}
            cuponsAtivos={cuponsAtivos}
            debitoFidelidade={debitoFidelidade}
            nivelFidelidade={nivelFidelidade}
            onCopiarCampoCliente={onCopiarCampoCliente}
            saldoCarimbos={saldoCarimbos}
            telefoneCliente={telefoneCliente}
          />

          <ClienteAlertasPdv cliente={cliente} />

          <ClienteAcoesResumo
            modoVisualizacao={modoVisualizacao}
            onAbrirHistoricoCliente={onAbrirHistoricoCliente}
            onAbrirModalAdicionarCredito={onAbrirModalAdicionarCredito}
            onAbrirVendasEmAberto={onAbrirVendasEmAberto}
            totalVendasAbertas={totalVendasAbertas}
            vendasEmAbertoInfo={vendasEmAbertoInfo}
          />

          <ClientePetSelector
            cliente={cliente}
            modoVisualizacao={modoVisualizacao}
            onSelecionarPet={onSelecionarPet}
            vendaAtual={vendaAtual}
          />
        </div>
      )}
    </Panel>
  );
}
