import CalculadoraDosesForm from "./calculadoraDoses/CalculadoraDosesForm";
import CalculadoraDosesHeader from "./calculadoraDoses/CalculadoraDosesHeader";
import CalculadoraDosesResultado from "./calculadoraDoses/CalculadoraDosesResultado";
import { useVetCalculadoraDoses } from "./calculadoraDoses/useVetCalculadoraDoses";

export default function VetCalculadoraDoses() {
  const calculadora = useVetCalculadoraDoses();

  return (
    <div className="p-6 space-y-6">
      <CalculadoraDosesHeader />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <CalculadoraDosesForm {...calculadora} />
        <CalculadoraDosesResultado {...calculadora} />
      </div>
    </div>
  );
}
