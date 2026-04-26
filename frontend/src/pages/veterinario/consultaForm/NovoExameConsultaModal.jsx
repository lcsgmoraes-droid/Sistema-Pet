import ConsultaModalShell from "./ConsultaModalShell";
import NovoExameFields from "./NovoExameFields";

export default function NovoExameConsultaModal({
  isOpen,
  onClose,
  css,
  consultaIdAtual,
  petSelecionadoLabel,
  petId,
  novoExameForm,
  setNovoExameForm,
  setNovoExameArquivo,
  salvarNovoExameRapido,
  salvandoNovoExame,
}) {
  return (
    <ConsultaModalShell
      isOpen={isOpen}
      title="Novo exame vinculado à consulta"
      subtitle={`Consulta #${consultaIdAtual || "-"} - ${petSelecionadoLabel}`}
      onClose={onClose}
      closeAriaLabel="Fechar modal de exame"
    >
      <NovoExameFields
        css={css}
        novoExameForm={novoExameForm}
        setNovoExameForm={setNovoExameForm}
        setNovoExameArquivo={setNovoExameArquivo}
      />

      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={onClose}
          className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={salvarNovoExameRapido}
          disabled={salvandoNovoExame || !petId || !novoExameForm.nome.trim()}
          className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {salvandoNovoExame ? "Salvando..." : "Salvar exame"}
        </button>
      </div>
    </ConsultaModalShell>
  );
}
