import { FileText } from "lucide-react";

export default function ConsultaDocumentosPanel({
  consultaIdAtual,
  modoSomenteLeitura,
  temPrescricao,
  baixandoPdf,
  onBaixarProntuario,
  onBaixarReceita,
}) {
  const prontuarioDisponivel = Boolean(consultaIdAtual && modoSomenteLeitura);
  const receitaDisponivel = prontuarioDisponivel && temPrescricao;
  const classeBotao =
    "inline-flex items-center justify-center gap-2 rounded-lg border border-blue-200 bg-white px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <section id="documentos-clinicos" className="rounded-xl border border-blue-200 bg-blue-50 p-5">
      <div className="flex items-center gap-2 text-blue-900">
        <FileText size={19} />
        <h2 className="font-semibold">Documentos clínicos</h2>
      </div>
      <p className="mt-1 text-sm text-blue-800">
        Prontuário do atendimento e receita para o tutor.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onBaixarProntuario}
          disabled={!prontuarioDisponivel || baixandoPdf}
          className={classeBotao}
        >
          <FileText size={16} />
          {baixandoPdf ? "Baixando..." : "Baixar prontuário PDF"}
        </button>
        <button
          type="button"
          onClick={onBaixarReceita}
          disabled={!receitaDisponivel || baixandoPdf}
          className={classeBotao}
        >
          <FileText size={16} />
          {baixandoPdf ? "Baixando..." : "Baixar receita PDF"}
        </button>
      </div>
      {!prontuarioDisponivel ? (
        <p className="mt-3 text-xs text-blue-700">
          Os PDFs ficam disponíveis depois de salvar e assinar a consulta. A receita também exige um
          medicamento na etapa Diagnóstico / Prescrição.
        </p>
      ) : !temPrescricao ? (
        <p className="mt-3 text-xs text-blue-700">
          Esta consulta não tem receita emitida. O prontuário já pode ser baixado.
        </p>
      ) : null}
    </section>
  );
}
