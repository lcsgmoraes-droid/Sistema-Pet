import { Check, Trash2 } from "lucide-react";
import { formatDateTime, formatQuantity } from "./internacaoUtils";

export default function AgendaProcedimentosPanel({
  agendaForm,
  setAgendaForm,
  internacoesOrdenadas,
  internacaoSelecionadaAgenda,
  agendaCarregando,
  agendaOrdenada,
  internacaoPorId,
  salvando,
  onAdicionarProcedimentoAgenda,
  onAbrirInsumoRapido,
  onReabrirProcedimento,
  onAbrirModalFeito,
  onRemoverProcedimentoAgenda,
}) {
  return (
    <div className="space-y-3">
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-gray-700">Novo procedimento / lembrete</p>
            <p className="mt-1 text-xs text-gray-500">
              Preencha o que estava previsto para o paciente: horário, nome do medicamento/procedimento,
              dose clínica, quantidade prevista e via. Se quiser apenas baixar um material usado na rotina,
              use o botão de insumo rápido.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onAbrirInsumoRapido(agendaForm.internacao_id)}
            className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
          >
            + Lançar insumo rápido
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <select
            value={agendaForm.internacao_id}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, internacao_id: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="">Selecione o internado...</option>
            {internacoesOrdenadas.map((internacao) => (
              <option key={internacao.id} value={internacao.id}>
                {internacao.pet_nome ?? `Pet #${internacao.pet_id}`}
                {internacao.box ? ` (${internacao.box})` : ""}
              </option>
            ))}
          </select>
          <input
            type="datetime-local"
            value={agendaForm.horario}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, horario: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Medicamento / procedimento"
            value={agendaForm.medicamento}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, medicamento: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Dose"
            value={agendaForm.dose}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, dose: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="number"
            min="0"
            step="0.01"
            placeholder="Qtd. prevista"
            value={agendaForm.quantidade_prevista}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, quantidade_prevista: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Unidade (mL, mg, comp, un...)"
            value={agendaForm.unidade_quantidade}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, unidade_quantidade: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Via (oral, IV, IM...)"
            value={agendaForm.via}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, via: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="text"
            value={agendaForm.internacao_id ? (internacaoSelecionadaAgenda?.box || "Sem baia") : "Selecione um internado"}
            disabled
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-600"
          />
          <input
            type="number"
            min="0"
            placeholder="Lembrete (min)"
            value={agendaForm.lembrete_min}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, lembrete_min: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Observações"
            value={agendaForm.observacoes}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, observacoes: event.target.value }))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm md:col-span-2"
          />
          <button
            type="button"
            onClick={onAdicionarProcedimentoAgenda}
            disabled={salvando}
            className="bg-purple-600 hover:bg-purple-700 text-white rounded-lg px-3 py-2 text-sm disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Adicionar na agenda"}
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <p className="text-sm font-semibold text-gray-700 mb-3">Horários de hoje e próximos</p>
        {agendaCarregando ? (
          <p className="text-xs text-gray-400">Carregando agenda de procedimentos...</p>
        ) : agendaOrdenada.length === 0 ? (
          <p className="text-xs text-gray-400">Nenhum procedimento agendado ainda.</p>
        ) : (
          <div className="space-y-2">
            {agendaOrdenada.map((item) => (
              <AgendaProcedimentoCard
                key={item.id}
                item={item}
                baiaExibicao={obterBaiaExibicao(item, internacaoPorId)}
                salvando={salvando}
                onReabrirProcedimento={onReabrirProcedimento}
                onAbrirModalFeito={onAbrirModalFeito}
                onRemoverProcedimentoAgenda={onRemoverProcedimentoAgenda}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function obterBaiaExibicao(item, internacaoPorId) {
  const internacaoAtual = internacaoPorId.get(String(item.internacao_id));
  return (internacaoAtual?.box || item.baia || "").trim() || "Sem baia";
}

function AgendaProcedimentoCard({
  item,
  baiaExibicao,
  salvando,
  onReabrirProcedimento,
  onAbrirModalFeito,
  onRemoverProcedimentoAgenda,
}) {
  const ts = new Date(item.horario).getTime();
  const diffMin = Math.round((ts - Date.now()) / 60000);
  const alerta = obterClasseAlertaProcedimento(item, diffMin);

  return (
    <div className="border border-slate-200 rounded-xl p-3 bg-gradient-to-r from-white to-slate-50/40 shadow-sm flex flex-col md:flex-row md:items-center gap-3 md:gap-4">
      <div className="min-w-[160px] bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
        <p className="text-lg font-semibold text-slate-800 leading-none tabular-nums">
          {formatDateTime(item.horario)}
        </p>
        <span className={`inline-block mt-2 text-[11px] px-2 py-0.5 rounded-full font-medium ${alerta}`}>
          {item.feito ? "Concluído" : diffMin <= 0 ? "Atrasado" : `Em ${diffMin} min`}
        </span>
      </div>

      <div className="flex-1">
        <p className="text-base font-semibold text-indigo-800 leading-tight">{item.medicamento}</p>
        <p className="text-sm text-slate-600 mt-0.5">
          {item.pet_nome} - Baia {baiaExibicao}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold">
            Dose: {item.dose || "-"}
          </span>
          {(item.quantidade_prevista || item.unidade_quantidade) && (
            <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200">
              Previsto: {formatQuantity(item.quantidade_prevista, item.unidade_quantidade)}
            </span>
          )}
          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            Via: {item.via || "-"}
          </span>
          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            Lembrete: {item.lembrete_min || 30} min
          </span>
        </div>
        {item.observacoes && <p className="text-xs text-slate-500 mt-2 italic">{item.observacoes}</p>}
        {item.feito && <ProcedimentoExecutadoResumo item={item} />}
      </div>

      <div className="flex gap-2">
        {item.feito ? (
          <button
            type="button"
            onClick={onReabrirProcedimento}
            className="px-2.5 py-1.5 text-xs border border-emerald-200 bg-emerald-50 text-emerald-700 rounded-lg transition-colors flex items-center gap-1"
          >
            <Check size={12} />
            Concluído
          </button>
        ) : (
          <button
            type="button"
            onClick={() => onAbrirModalFeito(item)}
            disabled={salvando}
            className="px-2.5 py-1.5 text-xs border border-emerald-200 text-emerald-700 rounded-lg hover:bg-emerald-50 transition-colors flex items-center gap-1 disabled:opacity-60"
          >
            <Check size={12} />
            Feito
          </button>
        )}
        <button
          type="button"
          onClick={() => onRemoverProcedimentoAgenda(item.id)}
          disabled={salvando || item.feito}
          title={
            item.feito
              ? "Procedimento concluído não pode ser excluído do histórico clínico."
              : "Excluir procedimento agendado"
          }
          className="px-2.5 py-1.5 text-xs border border-rose-200 text-rose-700 rounded-lg hover:bg-rose-50 transition-colors flex items-center gap-1 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Trash2 size={12} />
          Excluir
        </button>
      </div>
    </div>
  );
}

function obterClasseAlertaProcedimento(item, diffMin) {
  if (item.feito) return "bg-emerald-100 text-emerald-700 border border-emerald-200";
  if (diffMin <= 0) return "bg-rose-100 text-rose-700 border border-rose-200";
  if (diffMin <= Number(item.lembrete_min || 30)) return "bg-amber-100 text-amber-700 border border-amber-200";
  return "bg-sky-100 text-sky-700 border border-sky-200";
}

function ProcedimentoExecutadoResumo({ item }) {
  return (
    <div className="mt-2 bg-emerald-50 border border-emerald-200 rounded-md px-2 py-1.5">
      <p className="text-[11px] text-emerald-700 font-semibold">
        Feito por: {item.feito_por || "-"} - {item.horario_execucao ? formatDateTime(item.horario_execucao) : "-"}
      </p>
      {(item.quantidade_executada || item.quantidade_desperdicio) && (
        <p className="text-[11px] text-emerald-800">
          Feito: {formatQuantity(item.quantidade_executada, item.unidade_quantidade)} - Desperdício:{" "}
          {formatQuantity(item.quantidade_desperdicio, item.unidade_quantidade)}
        </p>
      )}
      {item.observacao_execucao && (
        <p className="text-[11px] text-emerald-800">Obs. execução: {item.observacao_execucao}</p>
      )}
    </div>
  );
}
