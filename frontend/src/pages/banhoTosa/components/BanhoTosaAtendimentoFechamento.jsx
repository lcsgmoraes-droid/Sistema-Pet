import { useState } from "react";
import toast from "react-hot-toast";
import { CheckCircle2, ExternalLink, Receipt, RefreshCw, XCircle } from "lucide-react";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import InputTexto from "../../../components/v2/InputTexto/InputTexto";
import InputCheckTexto from "../../../components/v2/InputCheckTexto/InputCheckTexto";
import { perguntarCorePet } from "../../../services/corepetDialog";
import { formatMoneyBRL } from "../../../utils/formatters";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatNumber } from "../banhoTosaUtils";
import ResumoCard from "./BanhoTosaAtendimentoResumoCard";

export default function Fechamento({
  atendimento,
  custo,
  saving,
  executar,
  onDelivered,
  onCancelled,
}) {
  const [confirmado, setConfirmado] = useState(false);
  const [semCobranca, setSemCobranca] = useState(false);
  const [motivoSemCobranca, setMotivoSemCobranca] = useState("");
  const [observacoesSaida, setObservacoesSaida] = useState(atendimento?.observacoes_saida || "");
  const {
    cobertoPorPacote,
    temVenda,
    valorPendente,
    podeSemCobranca,
    pacoteSemExtras,
    podeEntregar,
    encerrado,
    contratos,
  } = estadoFechamento(atendimento, semCobranca, motivoSemCobranca);
  const resumoValor = valorResumoAtendimento(atendimento, custo, cobertoPorPacote, valorPendente);
  const mensagemEncerramento =
    atendimento?.status === "entregue"
      ? "Atendimento já entregue e encerrado."
      : "Atendimento cancelado ou marcado como ausência.";
  const orientacaoEntrega = podeSemCobranca
    ? "Confirme a entrega sem cobrança e informe o motivo acima."
    : "Gere a cobrança dos serviços adicionais antes da entrega.";

  async function gerarVenda() {
    let pdvUrl = null;
    await executar(
      "venda",
      async () => {
        const response = await banhoTosaApi.gerarVendaAtendimento(atendimento.id);
        pdvUrl = response.data?.pdv_url;
      },
      "Cobrança enviada ao PDV.",
    );
    if (pdvUrl) window.open(pdvUrl, "_blank", "noopener,noreferrer");
  }

  async function entregar() {
    const sucesso = await executar(
      "entrega",
      () =>
        banhoTosaApi.moverEtapaAtendimento(atendimento.id, {
          tipo: "entregue",
          iniciar_timer: false,
          observacoes_saida: observacoesSaida.trim() || null,
          entrega_sem_cobranca: podeSemCobranca && semCobranca,
          motivo_sem_cobranca: podeSemCobranca && semCobranca ? motivoSemCobranca.trim() : null,
        }),
      "Entrega confirmada e atendimento encerrado.",
    );
    if (sucesso) {
      setConfirmado(false);
      onDelivered?.();
    }
  }

  async function cancelar() {
    const motivo = await perguntarCorePet({
      titulo: "Cancelar atendimento",
      mensagem:
        "O pet sairá da fila, as vendas avulsas deste atendimento serão canceladas e os créditos de pacote serão devolvidos. A cobrança do pacote e o histórico serão preservados. Informe o motivo:",
      confirmarTexto: "Cancelar atendimento",
      cancelarTexto: "Voltar",
      variante: "danger",
      obrigatorio: true,
      minimoCaracteres: 3,
    });
    if (motivo == null) return;
    if (motivo.trim().length < 3) {
      toast.error("Informe um motivo com pelo menos 3 caracteres.");
      return;
    }
    const sucesso = await executar(
      "cancelar",
      () => banhoTosaApi.cancelarProcessoAtendimento(atendimento.id, { motivo: motivo.trim() }),
      "Atendimento cancelado. O histórico foi preservado.",
    );
    if (sucesso) onCancelled?.();
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <ResumoCard label={resumoValor.label} value={formatMoneyBRL(resumoValor.valor)} />
        <ResumoCard label="Custo" value={formatMoneyBRL(custo?.custo_total || 0)} />
        <ResumoCard
          label="Margem prevista"
          value={formatMoneyBRL(custo?.margem_valor || 0)}
          subtitle={`${formatNumber(custo?.margem_percentual || 0, 1)}%`}
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <Receipt size={19} className="text-blue-600" />
          <h3 className="font-semibold text-slate-950">Cobrança</h3>
        </div>
        {cobertoPorPacote && (
          <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
            <p className="font-semibold">Serviços cobertos pelos pacotes vinculados.</p>
            {contratos.map((contrato) => (
              <div key={contrato.credito_id} className="mt-3 space-y-2">
                <p>
                  {contrato.pacote_nome || "Pacote"} · {labelPagamento(contrato.status_pagamento)}
                  {Number(contrato.valor_restante) > 0 &&
                    ` · Em aberto: ${formatMoneyBRL(contrato.valor_restante)}`}
                </p>
                {contrato.pdv_url && (
                  <BotaoInteracao
                    icon={ExternalLink}
                    onClick={() => window.open(contrato.pdv_url, "_blank", "noopener,noreferrer")}
                  >
                    Ver pagamento do pacote
                  </BotaoInteracao>
                )}
              </div>
            ))}
          </div>
        )}
        <CobrancaAtendimento
          atendimento={atendimento}
          temVenda={temVenda}
          podeSemCobranca={podeSemCobranca}
          encerrado={encerrado}
          semCobranca={semCobranca}
          setSemCobranca={setSemCobranca}
          motivoSemCobranca={motivoSemCobranca}
          setMotivoSemCobranca={setMotivoSemCobranca}
          pacoteSemExtras={pacoteSemExtras}
          saving={saving}
          executar={executar}
          gerarVenda={gerarVenda}
        />
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 size={19} className="text-emerald-600" />
          <h3 className="font-semibold text-slate-950">Entrega do pet</h3>
        </div>
        {encerrado ? (
          <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">
            {mensagemEncerramento}
          </p>
        ) : (
          <>
            <div className="mt-3">
              <InputTexto
                label="Observações de saída"
                placeholder="Orientações passadas ao tutor"
                value={observacoesSaida}
                onChange={setObservacoesSaida}
              />
            </div>
            <div className="mt-3">
              <InputCheckTexto
                checked={confirmado}
                disabled={!podeEntregar}
                onChange={setConfirmado}
              >
                Confirmo que o pet foi entregue ao tutor e a cobrança foi orientada
              </InputCheckTexto>
            </div>
            {!podeEntregar && (
              <p className="mt-2 text-xs font-medium text-amber-700">{orientacaoEntrega}</p>
            )}
            <BotaoInteracao
              className="mt-4 w-full justify-center"
              disabled={!confirmado || !podeEntregar}
              icon={CheckCircle2}
              larguraTotal
              loading={saving === "entrega"}
              onClick={entregar}
            >
              Confirmar entrega e encerrar
            </BotaoInteracao>
          </>
        )}
      </section>
      {!encerrado && (
        <section className="rounded-xl border border-red-200 bg-white p-4">
          <p className="mb-3 text-sm text-slate-600">
            Para um check-in feito por engano, cancele o atendimento e preserve o histórico.
          </p>
          <BotaoInteracao
            icon={XCircle}
            loading={saving === "cancelar"}
            disabled={Boolean(saving)}
            onClick={cancelar}
          >
            Cancelar atendimento e retirar da fila
          </BotaoInteracao>
        </section>
      )}
    </div>
  );
}

function estadoFechamento(atendimento, semCobranca, motivoSemCobranca) {
  const cobertoPorPacote = Boolean(atendimento?.pacote_credito_id);
  const temVenda = Boolean(atendimento?.venda_id);
  const valorPendente = atendimento?.valor_cobranca_pendente;
  const podeSemCobranca =
    !temVenda && !cobertoPorPacote && Number(valorPendente) === 0 && valorPendente != null;
  const pacoteSemExtras = cobertoPorPacote && valorPendente != null && Number(valorPendente) === 0;
  const podeEntregar =
    temVenda ||
    pacoteSemExtras ||
    (podeSemCobranca && semCobranca && motivoSemCobranca.trim().length >= 3);
  const encerrado = ["entregue", "cancelado", "no_show"].includes(atendimento?.status);
  const contratos = atendimento?.pacotes_financeiro?.length
    ? atendimento.pacotes_financeiro
    : [
        {
          credito_id: atendimento?.pacote_credito_id,
          pacote_nome: atendimento?.pacote_nome,
          status_pagamento: atendimento?.pacote_status_pagamento,
          valor_restante: atendimento?.pacote_valor_restante,
          pdv_url: atendimento?.pacote_pdv_url,
        },
      ];

  return {
    cobertoPorPacote,
    temVenda,
    valorPendente,
    podeSemCobranca,
    pacoteSemExtras,
    podeEntregar,
    encerrado,
    contratos,
  };
}

function CobrancaAtendimento({
  atendimento,
  temVenda,
  podeSemCobranca,
  encerrado,
  semCobranca,
  setSemCobranca,
  motivoSemCobranca,
  setMotivoSemCobranca,
  pacoteSemExtras,
  saving,
  executar,
  gerarVenda,
}) {
  if (temVenda) {
    return (
      <div className="mt-3">
        <p className="text-sm font-semibold text-slate-800">
          Venda {atendimento.venda_numero || `#${atendimento.venda_id}`} ·{" "}
          {labelPagamento(atendimento.venda_status_pagamento)}
        </p>
        <p className="mt-1 text-sm text-slate-500">
          Pago: {formatMoneyBRL(atendimento.venda_total_pago || 0)} · Restante:{" "}
          {formatMoneyBRL(atendimento.venda_valor_restante || 0)}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <BotaoInteracao
            icon={ExternalLink}
            onClick={() => window.open(atendimento.pdv_url, "_blank", "noopener,noreferrer")}
          >
            Abrir no PDV
          </BotaoInteracao>
          <BotaoInteracao
            icon={RefreshCw}
            loading={saving === "sync"}
            onClick={() =>
              executar(
                "sync",
                () => banhoTosaApi.sincronizarFechamentoAtendimento(atendimento.id),
                "Fechamento sincronizado.",
              )
            }
          >
            Sincronizar
          </BotaoInteracao>
        </div>
      </div>
    );
  }
  if (atendimento?.entrega_sem_cobranca) {
    return (
      <p className="mt-3 text-sm text-slate-600">Entrega sem cobrança registrada no histórico.</p>
    );
  }
  if (podeSemCobranca && !encerrado) {
    return (
      <div className="mt-3 space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
        <p className="text-sm text-amber-900">
          Os serviços estão com valor zero. Confira se o preço está correto. Se não houver cobrança,
          registre o motivo para encerrar sem gerar venda.
        </p>
        <InputCheckTexto checked={semCobranca} onChange={setSemCobranca}>
          Confirmo a entrega sem cobrança deste atendimento
        </InputCheckTexto>
        {semCobranca && (
          <InputTexto
            label="Motivo da entrega sem cobrança"
            value={motivoSemCobranca}
            onChange={setMotivoSemCobranca}
            required
            maxLength={1000}
            placeholder="Ex.: cortesia autorizada pelo responsável"
          />
        )}
      </div>
    );
  }
  if (!pacoteSemExtras && !encerrado) {
    return (
      <div className="mt-3">
        <p className="text-sm text-slate-600">
          Gere a venda antes de confirmar a entrega. O PDV abrirá com os serviços do atendimento.
        </p>
        <BotaoInteracao
          className="mt-3"
          icon={Receipt}
          loading={saving === "venda"}
          onClick={gerarVenda}
        >
          Gerar cobrança no PDV
        </BotaoInteracao>
      </div>
    );
  }
  return null;
}

function valorResumoAtendimento(atendimento, custo, cobertoPorPacote, valorPendente) {
  if (cobertoPorPacote) {
    return { label: "Valor de tabela", valor: custo?.valor_cobrado ?? 0 };
  }
  return {
    label: "Valor",
    valor: atendimento?.venda_total ?? valorPendente ?? custo?.valor_cobrado ?? 0,
  };
}

function labelPagamento(status) {
  return (
    {
      pago: "Pago",
      parcial: "Pagamento parcial",
      pendente: "Pagamento pendente",
      quitado_pacote: "Quitado por pacote",
      sem_venda: "Sem cobrança gerada",
      sem_cobranca: "Sem cobrança",
      cancelado: "Cobrança cancelada",
      coberto_pacote: "Coberto por pacote",
    }[status] || "Aguardando pagamento"
  );
}
