import { FileText } from "lucide-react";
import ActionButton from "../../components/ui/ActionButton";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import Panel from "../../components/ui/Panel";
import { REQUEST_STATUS } from "./lgpdConstants";
import LGPDRequestCard from "./LGPDRequestCard";

export default function LGPDSolicitacoesPanel({
  handleSelectRequest,
  loading,
  requestToProcess,
  requestsFilter,
  selectedClienteId,
  setNewRequestModalOpen,
  setRequestsFilter,
  visibleRequests,
}) {
  return (
    <Panel
      title={selectedClienteId ? "2. Solicitacoes deste titular" : "2. Fila de solicitacoes"}
      subtitle={
        selectedClienteId
          ? "Clique em uma solicitacao para tratar em uma janela separada."
          : "Fila operacional geral enquanto nenhum titular esta selecionado."
      }
      actions={
        selectedClienteId ? (
          <ActionButton
            icon={FileText}
            intent="neutral"
            tone="soft"
            onClick={() => setNewRequestModalOpen(true)}
          >
            Registrar pedido LGPD
          </ActionButton>
        ) : (
          <select
            id="lgpd-requests-filter"
            name="lgpd_requests_filter"
            value={requestsFilter}
            onChange={(event) => setRequestsFilter(event.target.value)}
            className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
          >
            <option value="">Todos os status</option>
            {REQUEST_STATUS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        )
      }
    >
      {loading ? (
        <LoadingState compact label="Carregando solicitacoes..." />
      ) : visibleRequests.length === 0 ? (
        <EmptyState
          compact
          title={
            selectedClienteId
              ? "Nenhuma solicitacao para este titular"
              : "Nenhuma solicitacao neste filtro"
          }
          description={
            selectedClienteId
              ? "Use Abrir exclusao LGPD para exclusao/anonimizacao ou Registrar pedido LGPD para outros direitos do titular."
              : "Quando um titular pedir acesso, exportacao, correcao ou exclusao, o acompanhamento aparece aqui."
          }
        />
      ) : (
        <div className="max-h-[560px] space-y-2 overflow-y-auto pr-1">
          {visibleRequests.map((request) => (
            <LGPDRequestCard
              key={request.id}
              request={request}
              selected={requestToProcess?.id === request.id}
              onSelect={handleSelectRequest}
            />
          ))}
        </div>
      )}
    </Panel>
  );
}
