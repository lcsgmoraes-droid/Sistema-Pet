import CopyableCode from "../../components/ui/CopyableCode";
import StatusBadge from "../../components/ui/StatusBadge";
import { REQUEST_STATUS_LABEL, REQUEST_TYPE_LABEL, STATUS_INTENT } from "./lgpdConstants";
import { formatDate } from "./lgpdUtils";

export default function LGPDRequestCard({ request, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(request)}
      className={[
        "w-full rounded-lg border p-3 text-left transition-colors",
        selected ? "border-blue-400 bg-blue-50" : "border-slate-200 bg-white hover:bg-slate-50",
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-950">
              {REQUEST_TYPE_LABEL[request.request_type] || request.request_type}
            </span>
            <CopyableCode label="ID" value={request.id} />
          </div>
          <div className="mt-1 flex min-w-0 flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>{request.subject_type || "customer"}</span>
            <CopyableCode label="Titular" value={request.subject_id} />
            <span>Canal: {request.channel || "-"}</span>
          </div>
        </div>
        <StatusBadge status={request.status} intent={STATUS_INTENT[request.status]}>
          {REQUEST_STATUS_LABEL[request.status] || request.status}
        </StatusBadge>
      </div>
      {request.requester_name || request.requester_email ? (
        <p className="mt-2 truncate text-xs text-slate-600">
          Solicitante: {request.requester_name || "-"}{" "}
          {request.requester_email ? `- ${request.requester_email}` : ""}
        </p>
      ) : null}
      {request.details ? (
        <p className="mt-2 line-clamp-2 text-xs text-slate-500">{request.details}</p>
      ) : null}
      <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-500 sm:grid-cols-2">
        <span>Criada: {formatDate(request.created_at)}</span>
        <span>Prazo: {formatDate(request.due_at)}</span>
      </div>
    </button>
  );
}
