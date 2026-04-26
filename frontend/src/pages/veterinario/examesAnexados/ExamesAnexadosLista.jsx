import {
  Bot,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  FileText,
  Sparkles,
} from "lucide-react";
import ExameAnexadoPainelIA from "../components/ExameAnexadoPainelIA";
import { formatarData } from "./examesAnexadosUtils";

export default function ExamesAnexadosLista({
  itens,
  total,
  exameExpandidoId,
  onToggleExame,
  onAbrirConsulta,
  onVerPet,
  onAtualizarResumo,
  onNovoExame,
}) {
  return (
    <>
      <div className="text-sm text-gray-500">
        Total: <strong>{total || 0}</strong> exame(s) com anexo
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {itens.length === 0 ? (
          <div className="p-10 text-center space-y-2">
            <FileText size={30} className="mx-auto text-gray-300" />
            <p className="text-gray-500">Nenhum exame anexado encontrado para esse filtro.</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {itens.map((item) => (
              <ExameAnexadoItem
                key={item.exame_id}
                item={item}
                expandido={String(exameExpandidoId) === String(item.exame_id)}
                onToggleExame={onToggleExame}
                onAbrirConsulta={onAbrirConsulta}
                onVerPet={onVerPet}
                onAtualizarResumo={onAtualizarResumo}
                onNovoExame={onNovoExame}
              />
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

function ExameAnexadoItem({
  item,
  expandido,
  onToggleExame,
  onAbrirConsulta,
  onVerPet,
  onAtualizarResumo,
  onNovoExame,
}) {
  return (
    <li className="px-4 py-3 transition-colors hover:bg-orange-50">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm font-semibold text-gray-800">{item.nome_exame || "Exame"}</p>
          <p className="text-xs text-gray-600">
            Tutor: {item.tutor_nome || "-"} | Pet: {item.pet_nome || "-"}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700">
            <CalendarDays size={12} /> {formatarData(item.data_upload)}
          </span>
          <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700">
            {item.status || "-"}
          </span>
          {item.tem_interpretacao_ia && (
            <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-violet-100 text-violet-700">
              <Sparkles size={12} /> IA pronta
            </span>
          )}
          <button
            type="button"
            onClick={() => onAbrirConsulta(item)}
            className="text-xs px-3 py-1.5 border border-orange-200 text-orange-700 rounded-md hover:bg-orange-100"
          >
            {item.consulta_id ? `Abrir consulta #${item.consulta_id}` : "Abrir consulta"}
          </button>
          <button
            type="button"
            onClick={() => onVerPet(item.pet_id)}
            className="text-xs px-3 py-1.5 border border-gray-200 rounded-md hover:bg-gray-50"
          >
            Ver pet
          </button>
          <button
            type="button"
            onClick={() => onToggleExame(item.exame_id)}
            className="inline-flex items-center gap-1 text-xs px-3 py-1.5 border border-indigo-200 text-indigo-700 rounded-md hover:bg-indigo-50"
          >
            <Bot size={13} />
            {expandido ? "Fechar IA" : "Abrir IA"}
            {expandido ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>
      </div>

      {expandido && (
        <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
          <ExameAnexadoPainelIA
            resumo={item}
            onAtualizado={onAtualizarResumo}
            onNovoExame={onNovoExame}
            onAbrirConsulta={() => onAbrirConsulta(item)}
          />
        </div>
      )}
    </li>
  );
}
