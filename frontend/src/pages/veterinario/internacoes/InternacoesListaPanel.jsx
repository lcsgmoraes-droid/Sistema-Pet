import { Activity, ArrowUpCircle, BedDouble, Clock } from "lucide-react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  STATUS_CORES,
  formatData,
  formatDateTime,
  formatQuantity,
  montarSerieEvolucao,
} from "./internacaoUtils";

export default function InternacoesListaPanel({
  aba,
  internacoesOrdenadas,
  expandida,
  evolucoes,
  procedimentosInternacao,
  onAbrirDetalhe,
  onAbrirInsumoRapido,
  onAbrirEvolucao,
  onAbrirAlta,
  onAbrirFichaPet,
  onAbrirHistoricoPet,
}) {
  return (
    <div className="space-y-3">
      {aba === "ativas" && (
        <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
          <p className="text-sm font-semibold text-gray-700">Ficha de internados</p>
          <p className="text-xs text-gray-500">
            Evoluções + procedimentos concluídos ficam centralizados por internação.
          </p>
        </div>
      )}

      {internacoesOrdenadas.map((internacao) => (
        <InternacaoCard
          key={internacao.id}
          internacao={internacao}
          aberta={expandida === internacao.id}
          evolucoes={evolucoes[internacao.id] ?? []}
          procedimentos={procedimentosInternacao[internacao.id] ?? []}
          onAbrirDetalhe={onAbrirDetalhe}
          onAbrirInsumoRapido={onAbrirInsumoRapido}
          onAbrirEvolucao={onAbrirEvolucao}
          onAbrirAlta={onAbrirAlta}
          onAbrirFichaPet={onAbrirFichaPet}
          onAbrirHistoricoPet={onAbrirHistoricoPet}
        />
      ))}
    </div>
  );
}

function InternacaoCard({
  internacao,
  aberta,
  evolucoes,
  procedimentos,
  onAbrirDetalhe,
  onAbrirInsumoRapido,
  onAbrirEvolucao,
  onAbrirAlta,
  onAbrirFichaPet,
  onAbrirHistoricoPet,
}) {
  const estaAtiva = internacao.status === "ativa" || internacao.status === "internado";

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div
        className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => onAbrirDetalhe(internacao.id)}
      >
        <BedDouble size={18} className="text-purple-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-800">
            {internacao.pet_nome ?? `Pet #${String(internacao.pet_id ?? "").slice(0, 6)}`}
          </p>
          {internacao.tutor_nome && <p className="text-xs text-gray-500">Tutor: {internacao.tutor_nome}</p>}
          <p className="text-xs text-gray-400 truncate">{internacao.motivo ?? internacao.motivo_internacao}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-xs text-gray-400">Entrada: {formatData(internacao.data_entrada)}</p>
          {internacao.data_saida && <p className="text-xs text-gray-400">Alta: {formatData(internacao.data_saida)}</p>}
          {internacao.box && <p className="text-xs text-gray-500">Box: {internacao.box}</p>}
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            STATUS_CORES[internacao.status] ?? "bg-gray-100"
          }`}
        >
          {internacao.status}
        </span>
        {estaAtiva && (
          <AcoesInternacao
            internacao={internacao}
            onAbrirInsumoRapido={onAbrirInsumoRapido}
            onAbrirEvolucao={onAbrirEvolucao}
            onAbrirAlta={onAbrirAlta}
            onAbrirFichaPet={onAbrirFichaPet}
            onAbrirHistoricoPet={onAbrirHistoricoPet}
          />
        )}
      </div>

      {aberta && (
        <DetalheInternacao
          internacao={internacao}
          evolucoes={evolucoes}
          procedimentos={procedimentos}
        />
      )}
    </div>
  );
}

function AcoesInternacao({
  internacao,
  onAbrirInsumoRapido,
  onAbrirEvolucao,
  onAbrirAlta,
  onAbrirFichaPet,
  onAbrirHistoricoPet,
}) {
  return (
    <div className="flex gap-2" onClick={(event) => event.stopPropagation()}>
      <button
        type="button"
        onClick={() => onAbrirInsumoRapido(internacao.id)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-emerald-200 text-emerald-700 rounded-lg hover:bg-emerald-50"
      >
        + Insumo
      </button>
      <button
        type="button"
        onClick={() => onAbrirEvolucao(internacao.id)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-blue-200 text-blue-600 rounded-lg hover:bg-blue-50"
      >
        <Activity size={12} />
        Evolução
      </button>
      <button
        type="button"
        onClick={() => onAbrirAlta(internacao.id)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-green-200 text-green-600 rounded-lg hover:bg-green-50"
      >
        <ArrowUpCircle size={12} />
        Alta
      </button>
      <button
        type="button"
        onClick={() => onAbrirFichaPet(internacao.pet_id)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50"
      >
        Ficha do pet
      </button>
      <button
        type="button"
        onClick={() => onAbrirHistoricoPet(internacao.pet_id, internacao.pet_nome ?? `Pet #${internacao.pet_id}`)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-indigo-200 text-indigo-600 rounded-lg hover:bg-indigo-50"
      >
        Detalhes
      </button>
    </div>
  );
}

function DetalheInternacao({ internacao, evolucoes, procedimentos }) {
  return (
    <div className="border-t border-gray-100 bg-gray-50 px-5 py-4">
      <CurvaEvolucao evolucoes={evolucoes} />

      {(internacao.observacoes_alta || internacao.observacoes) && (
        <div className="mb-3 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
          <p className="text-xs font-semibold text-green-700 mb-1">Observação da alta</p>
          <p className="text-xs text-green-800">{internacao.observacoes_alta || internacao.observacoes}</p>
        </div>
      )}

      <EvolucoesResumo evolucoes={evolucoes} />
      <ProcedimentosResumo procedimentos={procedimentos} />
    </div>
  );
}

function CurvaEvolucao({ evolucoes }) {
  const serie = montarSerieEvolucao(evolucoes);
  if (serie.length < 2) return null;

  return (
    <div className="mb-4 rounded-xl border border-blue-100 bg-white p-4">
      <p className="text-xs font-semibold text-gray-500 mb-3">Curva de evolução</p>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={serie}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="horario" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="vital" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="peso" orientation="right" tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Line yAxisId="vital" type="monotone" dataKey="temperatura" name="Temperatura" stroke="#ef4444" strokeWidth={2} dot={false} connectNulls />
          <Line yAxisId="vital" type="monotone" dataKey="fc" name="FC" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls />
          <Line yAxisId="vital" type="monotone" dataKey="fr" name="FR" stroke="#14b8a6" strokeWidth={2} dot={false} connectNulls />
          <Line yAxisId="peso" type="monotone" dataKey="peso" name="Peso" stroke="#7c3aed" strokeWidth={2} dot={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function EvolucoesResumo({ evolucoes }) {
  return (
    <>
      <p className="text-xs font-semibold text-gray-500 mb-3">Evoluções</p>
      {evolucoes.length === 0 ? (
        <p className="text-xs text-gray-400">Nenhuma evolução registrada ainda.</p>
      ) : (
        <div className="space-y-2">
          {evolucoes.map((evolucao, index) => (
            <div key={index} className="bg-white border border-gray-100 rounded-lg px-3 py-2 text-xs">
              <div className="flex items-center gap-2 text-gray-400 mb-1">
                <Clock size={10} />
                <span>{formatDateTime(evolucao.data_hora)}</span>
              </div>
              <div className="flex gap-4 text-gray-600">
                {evolucao.temperatura && <span>Temp: {evolucao.temperatura}°C</span>}
                {evolucao.freq_cardiaca && <span>FC: {evolucao.freq_cardiaca} bpm</span>}
                {evolucao.freq_respiratoria && <span>FR: {evolucao.freq_respiratoria} rpm</span>}
              </div>
              {evolucao.observacoes && <p className="text-gray-500 mt-1">{evolucao.observacoes}</p>}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function ProcedimentosResumo({ procedimentos }) {
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold text-gray-500 mb-2">Procedimentos desta internação</p>
      {procedimentos.length === 0 ? (
        <p className="text-xs text-gray-400">Nenhum procedimento registrado ainda.</p>
      ) : (
        <div className="space-y-2">
          {procedimentos.map((procedimento, index) => (
            <ProcedimentoResumoCard
              key={`${procedimento.id ?? index}_proc`}
              procedimento={procedimento}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ProcedimentoResumoCard({ procedimento, index }) {
  return (
    <div className="bg-white border border-emerald-100 rounded-lg px-3 py-2 text-xs">
      <div className="flex items-center gap-2 text-emerald-700 mb-1">
        <Clock size={10} />
        <span>
          {procedimento.horario_execucao
            ? formatDateTime(procedimento.horario_execucao)
            : formatDateTime(procedimento.data_hora)}
        </span>
      </div>
      <div className="mb-1">
        <span
          className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${
            procedimento.status === "agendado"
              ? "bg-amber-100 text-amber-700 border border-amber-200"
              : "bg-emerald-100 text-emerald-700 border border-emerald-200"
          }`}
        >
          {procedimento.status === "agendado" ? "Agendado" : "Concluído"}
        </span>
      </div>
      <p className="text-sm font-semibold text-emerald-800">{procedimento.medicamento || "Procedimento"}</p>
      <p className="text-gray-600">
        Dose: {procedimento.dose || "-"} - Via: {procedimento.via || "-"}
      </p>
      {(procedimento.quantidade_prevista != null ||
        procedimento.quantidade_executada != null ||
        procedimento.quantidade_desperdicio != null) && (
        <p className="text-gray-600">
          Previsto: {formatQuantity(procedimento.quantidade_prevista, procedimento.unidade_quantidade)} - Feito:{" "}
          {formatQuantity(procedimento.quantidade_executada, procedimento.unidade_quantidade)} - Desperdício:{" "}
          {formatQuantity(procedimento.quantidade_desperdicio, procedimento.unidade_quantidade)}
        </p>
      )}
      <p className="text-gray-500">Responsável: {procedimento.executado_por || "-"}</p>
      {Array.isArray(procedimento.insumos) && procedimento.insumos.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {procedimento.insumos.map((insumo, insumoIndex) => (
            <span
              key={`${procedimento.id ?? index}_insumo_${insumoIndex}`}
              className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700"
            >
              {insumo.nome || `Produto #${insumo.produto_id}`} - {formatQuantity(insumo.quantidade, insumo.unidade)}
            </span>
          ))}
        </div>
      )}
      {procedimento.observacao_execucao && (
        <p className="text-gray-500 mt-1">Obs.: {procedimento.observacao_execucao}</p>
      )}
    </div>
  );
}
