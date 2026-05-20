import { AlertCircle, FileText, Trash2 } from "lucide-react";
import PetIdentity from "../../../components/ui/PetIdentity";

import {
  formatDataConsulta,
  formatHoraConsulta,
  STATUS_COLOR,
  STATUS_LABEL,
} from "./consultasUtils";

export default function ConsultasTableCard({
  carregando,
  consultas,
  consultasSelecionadas = [],
  erro,
  erroExclusao,
  excluindoConsultas = false,
  onAbrirConsulta,
  onExcluirSelecionadas,
  onSelecionarConsulta,
  onSelecionarTodas,
  todasSelecionadas = false,
}) {
  const totalSelecionadas = consultasSelecionadas.length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {totalSelecionadas > 0 && (
        <div className="flex flex-col gap-3 border-b border-red-100 bg-red-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <span className="text-sm font-medium text-red-700">
            {totalSelecionadas} consulta{totalSelecionadas > 1 ? "s" : ""} selecionada{totalSelecionadas > 1 ? "s" : ""}
          </span>
          <button
            type="button"
            onClick={onExcluirSelecionadas}
            disabled={excluindoConsultas}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Trash2 size={16} />
            {excluindoConsultas ? "Excluindo..." : "Excluir selecionadas"}
          </button>
        </div>
      )}
      {erroExclusao && (
        <div className="flex items-center gap-2 border-b border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle size={16} />
          <span>{erroExclusao}</span>
        </div>
      )}
      {carregando ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      ) : erro ? (
        <div className="flex items-center gap-2 text-red-600 p-6">
          <AlertCircle size={18} />
          <span className="text-sm">{erro}</span>
        </div>
      ) : consultas.length === 0 ? (
        <div className="p-12 text-center">
          <FileText size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 text-sm">Nenhuma consulta encontrada.</p>
        </div>
      ) : (
        <div className="erp-data-table-wrap overflow-x-auto">
          <table className="w-full min-w-[920px] text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="w-12 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={todasSelecionadas}
                    onChange={onSelecionarTodas}
                    aria-label="Selecionar todas as consultas"
                    className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Codigo</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Data</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Pet</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Veterinario</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Motivo</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Diagnostico</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {consultas.map((consulta) => (
                <ConsultaTableRow
                  key={consulta.id}
                  consulta={consulta}
                  selecionada={consultasSelecionadas.includes(Number(consulta.id))}
                  onAbrirConsulta={onAbrirConsulta}
                  onSelecionarConsulta={onSelecionarConsulta}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ConsultaTableRow({ consulta, onAbrirConsulta, onSelecionarConsulta, selecionada }) {
  const dataAtendimento = consulta.inicio_atendimento || consulta.created_at;

  return (
    <tr
      className="hover:bg-blue-50 transition-colors cursor-pointer"
      onClick={() => onAbrirConsulta(consulta.id)}
    >
      <td className="px-4 py-3" onClick={(event) => event.stopPropagation()}>
        <input
          type="checkbox"
          checked={selecionada}
          onChange={() => onSelecionarConsulta(consulta.id)}
          aria-label={`Selecionar consulta #${consulta.id}`}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="font-semibold text-gray-800">#{consulta.id}</div>
        <div className="text-[11px] text-gray-400">Consulta</div>
      </td>
      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
        {formatDataConsulta(dataAtendimento)}
        {" "}
        <span className="text-xs ml-1 text-gray-400">{formatHoraConsulta(dataAtendimento)}</span>
      </td>
      <td className="px-4 py-3 font-medium text-gray-800">
        <PetIdentity
          fallback=""
          nameClassName="font-medium text-gray-800"
          record={consulta}
        />
      </td>
      <td className="px-4 py-3 text-gray-600">{consulta.veterinario_nome ?? "-"}</td>
      <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{consulta.motivo_consulta ?? "-"}</td>
      <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{consulta.diagnostico ?? "-"}</td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[consulta.status] ?? "bg-gray-100"}`}>
          {STATUS_LABEL[consulta.status] ?? consulta.status}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={(event) => {
            event.stopPropagation();
            onAbrirConsulta(consulta.id);
          }}
          className="text-blue-500 hover:text-blue-700 text-xs underline"
        >
          Abrir
        </button>
      </td>
    </tr>
  );
}
