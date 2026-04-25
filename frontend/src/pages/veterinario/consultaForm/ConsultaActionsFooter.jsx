import { Lock, Save } from "lucide-react";

export default function ConsultaActionsFooter({
  modoSomenteLeitura,
  etapa,
  totalEtapas,
  salvando,
  diagnosticoPreenchido,
  onCancel,
  onVoltarConsultas,
  onVoltarEtapa,
  onSalvarRascunho,
  onFinalizar,
}) {
  const ultimaEtapa = etapa >= totalEtapas - 1;

  return (
    <div className="flex items-center justify-between pt-2">
      <button
        onClick={onCancel}
        className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
      >
        Cancelar
      </button>

      <div className="flex gap-3">
        {modoSomenteLeitura ? (
          <button
            onClick={onVoltarConsultas}
            className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Voltar para consultas
          </button>
        ) : (
          <>
            {etapa > 0 && (
              <button
                onClick={onVoltarEtapa}
                className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                ← Voltar
              </button>
            )}

            {!ultimaEtapa ? (
              <button
                onClick={onSalvarRascunho}
                disabled={salvando}
                className="flex items-center gap-2 px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
              >
                <Save size={14} />
                {salvando ? "Salvando…" : "Salvar e continuar"}
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={onSalvarRascunho}
                  disabled={salvando}
                  className="flex items-center gap-2 px-4 py-2 text-sm border border-blue-300 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-60"
                >
                  <Save size={14} />
                  {salvando ? "Salvando…" : "Salvar rascunho"}
                </button>
                <button
                  onClick={onFinalizar}
                  disabled={salvando || !diagnosticoPreenchido}
                  className="flex items-center gap-2 px-5 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60"
                  title={!diagnosticoPreenchido ? "Preencha o diagnóstico para finalizar" : ""}
                >
                  <Lock size={14} />
                  {salvando ? "Finalizando…" : "Dar alta / finalizar"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
