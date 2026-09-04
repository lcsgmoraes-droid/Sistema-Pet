import { AlertTriangle, Check, Copy, CreditCard, History, Plus, User, Wallet } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { formatBRL, formatMoneyBRL } from "../../utils/formatters";
import { getClienteAlertasPdvAtivos } from "../../utils/clienteAlertasPdv";
import { filtrarCuponsValidosPdv } from "../../utils/pdvCuponsAtivos";
import { buildPdvCouponTooltip } from "../../utils/pdvCouponTooltip";
import { buildReturnTo } from "../../utils/petReturnFlow";
import { calcularResumoEmAbertoCliente } from "../../utils/pdvClienteFinanceiro";
import ImprimirSaldoCredito from "../ImprimirSaldoCredito";
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

function ClienteCreditoResumo({ cliente, creditoCliente }) {
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
      <div className="mt-2">
        <ImprimirSaldoCredito cliente={cliente} saldo={creditoCliente} />
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
        <ClienteCreditoResumo cliente={cliente} creditoCliente={creditoCliente} />
      </div>
    </EntityCard>
  );
}

function ClienteAcoesResumo({
  modoVisualizacao,
  onAbrirHistoricoCliente,
  onAbrirModalAdicionarCredito,
  onAbrirVendasEmAberto,
  onVerCrediario,
  resumoEmAberto,
}) {
  const temVendasEmAberto = resumoEmAberto.total_vendas > 0;
  const temCrediarioEmAberto = resumoEmAberto.total_parcelas_crediario > 0;
  const temValorEmAberto = resumoEmAberto.total_geral_em_aberto > 0;

  return (
    <div
      className={`flex min-h-[64px] w-full min-w-0 flex-wrap items-center gap-3 rounded-lg border px-3 py-2.5 ${
        temValorEmAberto
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "border-emerald-200 bg-emerald-50 text-emerald-900"
      }`}
    >
      <div className="flex min-w-[220px] flex-1 items-center gap-2.5">
        <AlertTriangle
          className={`h-5 w-5 flex-shrink-0 ${
            temValorEmAberto ? "text-amber-600" : "text-emerald-600"
          }`}
        />
        <div className="min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <span className="text-sm font-semibold leading-tight">Total em aberto</span>
            <span className="text-lg font-bold leading-tight">
              {formatMoneyBRL(resumoEmAberto.total_geral_em_aberto)}
            </span>
          </div>
          <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs leading-tight">
            {temVendasEmAberto && (
              <span>
                {resumoEmAberto.total_vendas} venda(s):{" "}
                {formatMoneyBRL(resumoEmAberto.total_vendas_em_aberto)}
              </span>
            )}
            {temCrediarioEmAberto && (
              <span className="inline-flex items-center gap-1">
                <CreditCard className="h-3.5 w-3.5" />
                {resumoEmAberto.total_parcelas_crediario} parcela(s) do crediário:{" "}
                {formatMoneyBRL(resumoEmAberto.total_crediario_em_aberto)}
              </span>
            )}
            {resumoEmAberto.total_crediario_vencido > 0 && (
              <span className="font-semibold text-red-700">
                Vencido: {formatMoneyBRL(resumoEmAberto.total_crediario_vencido)}
              </span>
            )}
            {!temValorEmAberto && <span>Nenhuma pendência financeira</span>}
          </div>
        </div>
      </div>

      <div className="flex w-full flex-wrap gap-2 lg:w-auto lg:justify-end">
        {temVendasEmAberto && (
          <ActionButton
            onClick={onAbrirVendasEmAberto}
            intent="warning"
            size="sm"
            className="min-w-[128px] flex-1 lg:flex-none"
          >
            Ver vendas
          </ActionButton>
        )}
        {temCrediarioEmAberto && (
          <ActionButton
            onClick={onVerCrediario}
            intent="neutral"
            size="sm"
            className="min-w-[128px] flex-1 lg:flex-none"
          >
            Ver parcelas
          </ActionButton>
        )}
        <ActionButton
          onClick={onAbrirHistoricoCliente}
          icon={History}
          intent="neutral"
          tone="soft"
          size="sm"
          className="min-w-[128px] flex-1 lg:flex-none"
        >
          Histórico
        </ActionButton>
        {!modoVisualizacao && (
          <ActionButton
            onClick={onAbrirModalAdicionarCredito}
            icon={Wallet}
            intent="create"
            size="sm"
            className="min-w-[144px] flex-1 lg:flex-none"
          >
            Inserir crédito
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
  const navigate = useNavigate();
  const cliente = vendaAtual.cliente;
  const saldoCarimbos = Number(saldoCampanhas?.total_carimbos || 0);
  const debitoFidelidade = Math.max(
    Number(saldoCampanhas?.carimbos_em_debito || 0),
    saldoCarimbos < 0 ? Math.abs(saldoCarimbos) : 0,
  );
  const creditoCliente = Number(cliente?.credito || 0);
  const cuponsAtivos = filtrarCuponsValidosPdv(saldoCampanhas?.cupons_ativos);
  const resumoEmAberto = calcularResumoEmAbertoCliente(vendasEmAbertoInfo);
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
            onVerCrediario={() =>
              navigate(
                `/financeiro/contas-receber?cliente_id=${cliente.id}&filtro=em_aberto&periodo=todos`,
              )
            }
            resumoEmAberto={resumoEmAberto}
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
