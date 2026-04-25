import { BedDouble, MessageSquare, Syringe } from "lucide-react";

export default function FluxosVinculadosConsulta({
  consultaIdAtual,
  abrirFluxoConsulta,
}) {
  return (
    <div className="rounded-xl border border-purple-100 bg-purple-50 px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-purple-900">Fluxos vinculados à consulta</h3>
          <p className="text-xs text-purple-700">
            Use a consulta #{consultaIdAtual || "-"} como referência para exames, vacinas, IA e internação.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => abrirFluxoConsulta("/veterinario/assistente-ia")}
            disabled={!consultaIdAtual}
            className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
          >
            <MessageSquare size={15} />
            IA da consulta
          </button>
          <button
            type="button"
            onClick={() => abrirFluxoConsulta("/veterinario/vacinas", { acao: "novo" })}
            disabled={!consultaIdAtual}
            className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
          >
            <Syringe size={15} />
            Registrar vacina
          </button>
          <button
            type="button"
            onClick={() => abrirFluxoConsulta("/veterinario/internacoes", { abrir_nova: "1" })}
            disabled={!consultaIdAtual}
            className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
          >
            <BedDouble size={15} />
            Encaminhar para internação
          </button>
        </div>
      </div>
      {!consultaIdAtual && (
        <p className="mt-3 text-xs text-purple-700">
          Salve o rascunho primeiro para liberar os outros fluxos já amarrados a esta consulta.
        </p>
      )}
    </div>
  );
}
