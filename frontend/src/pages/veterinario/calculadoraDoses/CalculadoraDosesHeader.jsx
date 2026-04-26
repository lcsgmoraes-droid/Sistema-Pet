import { Calculator } from "lucide-react";

export default function CalculadoraDosesHeader() {
  return (
    <div className="flex items-center gap-3">
      <div className="rounded-2xl bg-cyan-100 p-3 text-cyan-700">
        <Calculator size={24} />
      </div>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Calculadora de doses</h1>
        <p className="text-sm text-gray-500">Ferramenta livre para checagem rapida por mg/kg.</p>
      </div>
    </div>
  );
}
