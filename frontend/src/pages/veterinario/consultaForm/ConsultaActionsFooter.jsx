import { ArrowRight, Bed, CalendarPlus, Lock, Save } from "lucide-react";

export default function ConsultaActionsFooter({
  modoSomenteLeitura,
  etapa,
  totalEtapas,
  salvando,
  diagnosticoPreenchido,
  consultaIdAtual,
  onCancel,
  onVoltarConsultas,
  onVoltarEtapa,
  onAgendarRetorno,
  onAbrirInternacao,
  onSalvarRascunho,
  onSalvarAssinar,
  onFinalizar,
}) {
  const ultimaEtapa = etapa >= totalEtapas - 1;

  return (
    <div className="flex items-center justify-between gap-3 pt-2">
      <button
        type="button"
        onClick={onCancel}
        className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
      >
        Cancelar
      </button>

      <div className="flex gap-3">
        {modoSomenteLeitura ? (
          <button
            type="button"
            onClick={onVoltarConsultas}
            className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Voltar para consultas
          </button>
        ) : (
          <>
            {etapa > 0 && (
              <button
                type="button"
                onClick={onVoltarEtapa}
                className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Voltar
              </button>
            )}

            {!ultimaEtapa ? (
              <button
                type="button"
                onClick={onSalvarRascunho}
                disabled={salvando}
                className="flex items-center gap-2 px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
              >
                {salvando ? <Save size={14} /> : <ArrowRight size={14} />}
                {salvando ? "Salvando..." : "Proximo"}
              </button>
            ) : (
              <div className="flex flex-wrap justify-end gap-2">
                <button
                  type="button"
                  onClick={onSalvarRascunho}
                  disabled={salvando}
                  className="flex items-center gap-2 px-4 py-2 text-sm border border-blue-300 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-60"
                >
                  <Save size={14} />
                  {salvando ? "Salvando..." : "Salvar rascunho"}
                </button>
                <button
                  type="button"
                  onClick={onAgendarRetorno}
                  disabled={salvando || !consultaIdAtual}
                  className="flex items-center gap-2 px-4 py-2 text-sm border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 disabled:opacity-60"
                  title={
                    !consultaIdAtual ? "Salve a consulta em rascunho antes de agendar retorno" : ""
                  }
                >
                  <CalendarPlus size={14} />
                  Agendar retorno
                </button>
                <button
                  type="button"
                  onClick={onAbrirInternacao}
                  disabled={salvando || !consultaIdAtual}
                  className="flex items-center gap-2 px-4 py-2 text-sm border border-emerald-300 text-emerald-700 rounded-lg hover:bg-emerald-50 disabled:opacity-60"
                  title={
                    !consultaIdAtual ? "Salve a consulta em rascunho antes de abrir internacao" : ""
                  }
                >
                  <Bed size={14} />
                  Internacao
                </button>
                <button
                  type="button"
                  onClick={onSalvarAssinar || onFinalizar}
                  disabled={salvando || !diagnosticoPreenchido}
                  className="flex items-center gap-2 px-5 py-2 text-sm bg-slate-900 text-white rounded-lg hover:bg-slate-700 disabled:opacity-60"
                  title={!diagnosticoPreenchido ? "Preencha o diagnostico para assinar" : ""}
                >
                  <Lock size={14} />
                  {salvando ? "Assinando..." : "Salvar e assinar consulta"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
