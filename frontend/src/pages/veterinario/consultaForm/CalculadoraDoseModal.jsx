import CalculadoraDoseFields from "./CalculadoraDoseFields";
import CalculadoraDoseResultado from "./CalculadoraDoseResultado";
import ConsultaModalShell from "./ConsultaModalShell";

export default function CalculadoraDoseModal({
  isOpen,
  onClose,
  css,
  petSelecionadoLabel,
  calculadoraForm,
  setCalculadoraForm,
  medicamentosCatalogo,
  medicamentoSelecionado,
  resultado,
}) {
  return (
    <ConsultaModalShell
      isOpen={isOpen}
      title="Calculadora rápida de dose"
      subtitle="Modal livre para cálculo rápido durante a consulta."
      onClose={onClose}
      closeAriaLabel="Fechar calculadora"
    >
      <CalculadoraDoseFields
        css={css}
        petSelecionadoLabel={petSelecionadoLabel}
        calculadoraForm={calculadoraForm}
        setCalculadoraForm={setCalculadoraForm}
        medicamentosCatalogo={medicamentosCatalogo}
        medicamentoSelecionado={medicamentoSelecionado}
      />

      <CalculadoraDoseResultado resultado={resultado} />

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
        >
          Fechar
        </button>
      </div>
    </ConsultaModalShell>
  );
}
