import { useEffect, useState } from "react";
import {
  FLOATING_CALCULATOR_ENABLED_KEY,
  FLOATING_CALCULATOR_PREF_EVENT,
  isFloatingCalculatorEnabled,
  setFloatingCalculatorEnabled,
} from "../../utils/floatingCalculatorPreference";

export default function CalculadoraRacaoHeader() {
  const [calculadoraFlutuanteAtiva, setCalculadoraFlutuanteAtiva] = useState(() =>
    isFloatingCalculatorEnabled(),
  );

  useEffect(() => {
    const atualizarCalculadoraFlutuante = (event) => {
      if (event.type === "storage" && event.key !== FLOATING_CALCULATOR_ENABLED_KEY) {
        return;
      }

      setCalculadoraFlutuanteAtiva(event.detail?.enabled ?? isFloatingCalculatorEnabled());
    };

    window.addEventListener(FLOATING_CALCULATOR_PREF_EVENT, atualizarCalculadoraFlutuante);
    window.addEventListener("storage", atualizarCalculadoraFlutuante);

    return () => {
      window.removeEventListener(FLOATING_CALCULATOR_PREF_EVENT, atualizarCalculadoraFlutuante);
      window.removeEventListener("storage", atualizarCalculadoraFlutuante);
    };
  }, []);

  const alterarCalculadoraFlutuante = (event) => {
    const enabled = setFloatingCalculatorEnabled(event.target.checked);
    setCalculadoraFlutuanteAtiva(enabled);
  };

  return (
    <div className="calculadora-header">
      <div className="calculadora-header-copy">
        <h1>Calculadora de Racao</h1>
        <p>Calcule duracao, custo/dia e compare produtos</p>
      </div>

      <label
        className={`floating-calculator-toggle ${calculadoraFlutuanteAtiva ? "is-active" : ""}`}
      >
        <input
          type="checkbox"
          aria-label="Calculadora flutuante"
          checked={calculadoraFlutuanteAtiva}
          onChange={alterarCalculadoraFlutuante}
        />
        <span className="floating-calculator-toggle-text">Calculadora flutuante</span>
        <span className="floating-calculator-toggle-switch" aria-hidden="true">
          <span />
        </span>
        <span className="floating-calculator-toggle-status">
          {calculadoraFlutuanteAtiva ? "Ativa" : "Desativada"}
        </span>
      </label>
    </div>
  );
}
