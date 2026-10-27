import { useEffect, useState } from "react";
import { CalendarPlus, CircleDollarSign, ExternalLink, History, PackageX } from "lucide-react";
import toast from "react-hot-toast";
import CustomerIdentity from "../../../components/ui/CustomerIdentity";
import EmptyState from "../../../components/ui/EmptyState";
import LoadingState from "../../../components/ui/LoadingState";
import Panel from "../../../components/ui/Panel";
import PetIdentity from "../../../components/ui/PetIdentity";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoMenuAcoes from "../../../components/v2/BotaoMenuAcoes/BotaoMenuAcoes";
import BotaoSalva from "../../../components/v2/BotaoSalva/BotaoSalva";
import InputData from "../../../components/v2/InputData/InputData";
import InputTextoLongo from "../../../components/v2/InputTextoLongo/InputTextoLongo";
import ModalPadrao from "../../../components/v2/ModalPadrao/ModalPadrao";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, getApiErrorMessage } from "../banhoTosaUtils";
import { formatarCreditos } from "../banhoTosaPacotesUtils";
import { formatarDataLocal } from "../../../utils/drePeriodos";

const pagamentos = {
  sem_venda: "Sem cobrança vinculada",
  pendente: "Pagamento em aberto",
  parcial: "Pagamento parcial",
  pago: "Pago",
  cancelado: "Venda cancelada",
};
// Ícones destas ações de pacote: prorrogar = CalendarPlus, encerrar saldo = PackageX,
// gerar cobrança = CircleDollarSign. Histórico/abrir seguem o padrão global.
const movimentosLabel = {
  reserva: "Reserva no agendamento",
  consumo: "Uso no atendimento",
  estorno: "Estorno",
  estorno_reserva: "Reserva devolvida",
  confirmacao: "Reserva confirmada no check-in",
  cancelamento_reserva: "Reserva devolvida",
  liberacao_reserva: "Reserva devolvida",
  prorrogacao: "Validade prorrogada",
  encerramento: "Saldo encerrado manualmente",
};
const titulosModal = {
  historico: "Histórico do pacote",
  prorrogar: "Prorrogar validade do pacote",
  encerrar: "Encerrar saldo do pacote",
};
const coresStatus = {
  expirado: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  disponivel: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  neutro: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
};

export default function BanhoTosaCreditosList({ creditos = [], onChanged }) {
  const [modal, setModal] = useState(null);
  const [dataValidade, setDataValidade] = useState("");
  const [motivo, setMotivo] = useState("");
  const [saving, setSaving] = useState(false);
  const [gerandoId, setGerandoId] = useState(null);
  const [historico, setHistorico] = useState({ loading: true, items: [], error: "" });
  useEffect(() => {
    if (modal?.tipo !== "historico") return;
    let ativo = true;
    setHistorico({ loading: true, items: [], error: "" });
    banhoTosaApi
      .listarMovimentosCreditoPacote(modal.credito.id)
      .then(
        (response) =>
          ativo &&
          setHistorico({
            loading: false,
            items: Array.isArray(response.data) ? response.data : [],
            error: "",
          }),
      )
      .catch(
        (error) =>
          ativo &&
          setHistorico({
            loading: false,
            items: [],
            error: getApiErrorMessage(error, "Não foi possível carregar o histórico."),
          }),
      );
    return () => {
      ativo = false;
    };
  }, [modal]);

  function abrir(tipo, credito) {
    setMotivo("");
    setDataValidade(credito.data_validade || "");
    setHistorico({ loading: true, items: [], error: "" });
    setModal({ tipo, credito });
  }
  async function salvar(event) {
    event.preventDefault();
    if (motivo.trim().length < 3)
      return toast.error(
        "Registre o motivo ou o combinado com o cliente (pelo menos 3 caracteres).",
      );
    if (
      modal.tipo === "prorrogar" &&
      (!dataValidade || dataValidade <= modal.credito.data_validade)
    ) {
      return toast.error("A nova validade deve ser posterior à validade atual.");
    }
    setSaving(true);
    try {
      if (modal.tipo === "prorrogar")
        await banhoTosaApi.prorrogarCreditoPacote(modal.credito.id, {
          data_validade: dataValidade,
          motivo: motivo.trim(),
        });
      else await banhoTosaApi.encerrarCreditoPacote(modal.credito.id, { motivo: motivo.trim() });
      toast.success(
        modal.tipo === "prorrogar"
          ? "Validade prorrogada; saldo preservado."
          : "Saldo encerrado. Histórico e cobrança foram preservados.",
      );
      setModal(null);
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível alterar o saldo."));
    } finally {
      setSaving(false);
    }
  }
  async function gerarVenda(credito) {
    setGerandoId(credito.id);
    try {
      await banhoTosaApi.gerarVendaCreditoPacote(credito.id);
      toast.success("Cobrança vinculada. Abra a venda para registrar o recebimento no PDV.");
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível gerar a cobrança."));
    } finally {
      setGerandoId(null);
    }
  }
  function fecharModal() {
    if (!saving) setModal(null);
  }

  return (
    <>
      <Panel
        title="Pacotes dos pets"
        subtitle="O agendamento reserva, o check-in confirma o uso e o cancelamento devolve a reserva. Vencimento não apaga saldo nem histórico."
        actions={
          <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
            {creditos.length} contratações
          </span>
        }
      >
        <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-700">
          {creditos.map((credito) => (
            <CreditoLinha
              key={credito.id}
              credito={credito}
              gerandoId={gerandoId}
              abrir={abrir}
              gerarVenda={gerarVenda}
            />
          ))}
          {creditos.length === 0 && (
            <EmptyState
              compact
              description="Vincule um pacote ao pet para acompanhar serviços, validade e pagamento."
              title="Nenhum pacote vinculado"
            />
          )}
        </div>
      </Panel>
      {modal && (
        <ModalPadrao
          titulo={titulosModal[modal.tipo]}
          tamanho="normal"
          onFechar={fecharModal}
          rodape={<RodapeCreditoModal tipo={modal.tipo} saving={saving} onFechar={fecharModal} />}
        >
          <p className="mb-4 text-sm font-semibold text-slate-700 dark:text-slate-200">
            {modal.credito.pacote_nome} · {modal.credito.pet_nome || modal.credito.cliente_nome}
          </p>
          {modal.tipo === "historico" ? (
            <HistoricoCredito historico={historico} />
          ) : (
            <AjusteCreditoForm
              modal={modal}
              dataValidade={dataValidade}
              setDataValidade={setDataValidade}
              motivo={motivo}
              setMotivo={setMotivo}
              onSubmit={salvar}
            />
          )}
        </ModalPadrao>
      )}
    </>
  );
}

function estadoCredito(credito) {
  const encerrado = ["encerrado", "cancelado"].includes(credito.status);
  const inicioFuturo = credito.data_inicio > formatarDataLocal();
  let rotuloSaldo = "disponíveis";
  if (inicioFuturo) rotuloSaldo = "previstos";
  if (credito.vencido) rotuloSaldo = "preservados";
  let cor = coresStatus.neutro;
  if (credito.disponivel) cor = coresStatus.disponivel;
  if (credito.vencido && !encerrado) cor = coresStatus.expirado;
  let label = "Sem saldo disponível";
  if (Number(credito.creditos_reservados || 0) > 0) label = "Reservado na agenda";
  if (credito.disponivel) label = "Disponível";
  if (inicioFuturo) label = `Inicia em ${formatDate(credito.data_inicio)}`;
  if (credito.vencido) label = "Expirado — saldo preservado";
  if (encerrado) label = "Encerrado";
  return { encerrado, rotuloSaldo, cor, label };
}
function acaoFinanceira(credito, gerandoId, gerarVenda) {
  if (credito.venda_id)
    return {
      icon: ExternalLink,
      label: "Abrir venda no PDV",
      onClick: () =>
        window.open(
          credito.pdv_url || `/pdv?venda_id=${credito.venda_id}`,
          "_blank",
          "noopener,noreferrer",
        ),
    };
  return {
    icon: CircleDollarSign,
    label: gerandoId === credito.id ? "Gerando cobrança..." : "Gerar cobrança no PDV",
    disabled: gerandoId !== null || Number(credito.valor_pacote || 0) <= 0,
    onClick: () => gerarVenda(credito),
  };
}
function CreditoLinha({ credito, gerandoId, abrir, gerarVenda }) {
  const estado = estadoCredito(credito);
  const acoes = [
    { icon: History, label: "Histórico", onClick: () => abrir("historico", credito) },
    {
      icon: CalendarPlus,
      label: "Prorrogar validade",
      disabled: estado.encerrado,
      onClick: () => abrir("prorrogar", credito),
    },
    {
      icon: PackageX,
      label: "Encerrar saldo",
      disabled:
        estado.encerrado || Number(credito.saldo_total_creditos ?? credito.saldo_creditos) <= 0,
      tom: "perigo",
      onClick: () => abrir("encerrar", credito),
    },
    acaoFinanceira(credito, gerandoId, gerarVenda),
  ];
  const corPagamento =
    credito.status_pagamento === "pago"
      ? "text-emerald-700 dark:text-emerald-300"
      : "text-amber-700 dark:text-amber-300";
  return (
    <div className="grid gap-3 p-3 md:grid-cols-[auto_1.3fr_1fr_0.9fr] md:items-start">
      <BotaoMenuAcoes
        rotulo={`Ações de ${credito.pacote_nome} para ${credito.pet_nome || credito.cliente_nome}`}
        acoes={acoes}
      />
      <div>
        <p className="font-semibold text-slate-900 dark:text-slate-100">{credito.pacote_nome}</p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400">
          <CustomerIdentity
            codeLabel="Cód. tutor"
            fallback="Tutor não informado"
            layout="inline"
            record={credito}
          />
          <span>·</span>
          {credito.pet_nome || credito.pet_id ? (
            <PetIdentity fallback={`Pet #${credito.pet_id}`} layout="inline" record={credito} />
          ) : (
            <span>Todos os pets (vínculo antigo)</span>
          )}
        </div>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          {formatDate(credito.data_inicio)} a {formatDate(credito.data_validade)}
        </p>
        <span
          className={`mt-2 inline-flex rounded-full px-2 py-1 text-xs font-semibold ${estado.cor}`}
        >
          {estado.label}
        </span>
        {credito.observacoes && (
          <p className="mt-2 whitespace-pre-line text-xs text-slate-500 dark:text-slate-400">
            {credito.observacoes}
          </p>
        )}
      </div>
      <div className="space-y-2">
        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {formatarCreditos(credito.saldo_creditos)} {estado.rotuloSaldo} ·{" "}
          {formatarCreditos(credito.creditos_reservados || 0)} reservados
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {formatarCreditos(credito.creditos_usados)} usados de{" "}
          {formatarCreditos(credito.creditos_total)} contratados
        </p>
        {(credito.servicos || []).map((item) => (
          <SaldoServicoCredito key={item.servico_id || "geral"} item={item} estado={estado} />
        ))}
      </div>
      <div className="space-y-1 text-sm">
        <p className={`font-semibold ${corPagamento}`}>
          {pagamentos[credito.status_pagamento] || "Pagamento a conferir"}
        </p>
        <p className="text-slate-700 dark:text-slate-300">
          Pacote: {formatCurrency(credito.valor_pacote)}
        </p>
        {credito.venda_id && (
          <>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Venda {credito.venda_numero || `#${credito.venda_id}`}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Recebido: {formatCurrency(credito.valor_pago)} · Falta:{" "}
              {formatCurrency(credito.valor_restante)}
            </p>
          </>
        )}
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Pagamento pendente não impede o uso do pacote.
        </p>
      </div>
    </div>
  );
}
function SaldoServicoCredito({ item, estado }) {
  const saldo = estado.encerrado ? 0 : (item.saldo_creditos ?? item.quantidade_creditos);
  return (
    <p className="text-xs text-slate-600 dark:text-slate-300">
      {item.servico_nome || "Serviços do pacote"}: {formatarCreditos(saldo)} {estado.rotuloSaldo},{" "}
      {formatarCreditos(item.creditos_reservados || 0)} reservados,{" "}
      {formatarCreditos(item.creditos_usados || 0)} usados
    </p>
  );
}
function RodapeCreditoModal({ tipo, saving, onFechar }) {
  if (tipo === "historico") return <BotaoCancelar onClick={onFechar}>Fechar</BotaoCancelar>;
  return (
    <>
      <BotaoCancelar disabled={saving} onClick={onFechar} />
      <BotaoSalva form="bt-credito-ajuste" loading={saving}>
        {tipo === "prorrogar" ? "Prorrogar validade" : "Confirmar encerramento"}
      </BotaoSalva>
    </>
  );
}
function HistoricoCredito({ historico }) {
  if (historico.loading) return <LoadingState label="Carregando histórico..." />;
  if (historico.error)
    return (
      <p role="alert" className="text-sm text-red-600 dark:text-red-400">
        {historico.error}
      </p>
    );
  return (
    <div className="space-y-3">
      {historico.items.map((item) => (
        <div
          key={item.id}
          className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700"
        >
          <p className="font-semibold text-slate-900 dark:text-slate-100">
            {movimentosLabel[item.tipo] || item.tipo} · {formatarCreditos(item.quantidade)}
          </p>
          {(item.agendamento_id || item.atendimento_id) && (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {referenciaMovimento(item)}
            </p>
          )}
          {item.observacoes && (
            <p className="mt-1 whitespace-pre-line text-slate-600 dark:text-slate-300">
              {item.observacoes}
            </p>
          )}
        </div>
      ))}
      {!historico.items.length && (
        <EmptyState
          compact
          title="Nenhuma movimentação"
          description="As reservas, usos e ajustes deste pacote aparecerão aqui."
        />
      )}
    </div>
  );
}
function referenciaMovimento(item) {
  if (item.agendamento_id) return `Agendamento #${item.agendamento_id}`;
  return `Atendimento #${item.atendimento_id}`;
}
function AjusteCreditoForm({ modal, dataValidade, setDataValidade, motivo, setMotivo, onSubmit }) {
  return (
    <form id="bt-credito-ajuste" onSubmit={onSubmit} className="space-y-4">
      {modal.tipo === "prorrogar" ? (
        <InputData
          id="bt-credito-nova-validade"
          label="Nova validade"
          required
          value={dataValidade}
          onChange={setDataValidade}
          help={`Validade atual: ${formatDate(modal.credito.data_validade)}. O saldo existente será preservado.`}
        />
      ) : (
        <p className="text-sm text-amber-700 dark:text-amber-300">
          O saldo não utilizado será encerrado manualmente. As movimentações e a cobrança serão
          mantidas. Reservas existentes precisam ser canceladas antes.
        </p>
      )}
      <InputTextoLongo
        id="bt-credito-motivo"
        label="Motivo / combinado com o cliente"
        maxLength={1000}
        required
        value={motivo}
        onChange={setMotivo}
      />
    </form>
  );
}
function formatDate(value) {
  return value
    ? new Date(`${String(value).slice(0, 10)}T00:00:00`).toLocaleDateString("pt-BR")
    : "—";
}
