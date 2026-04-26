import { FlaskConical, Stethoscope } from "lucide-react";

function BotaoModo({ ativo, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-lg border ${
        ativo ? "bg-cyan-600 text-white border-cyan-600" : "bg-white text-gray-600 border-gray-200"
      }`}
    >
      <span className="inline-flex items-center gap-2">{children}</span>
    </button>
  );
}

export default function AssistenteIAModoToggle({ modo, setModo }) {
  return (
    <div className="flex flex-wrap gap-2">
      <BotaoModo ativo={modo === "atendimento"} onClick={() => setModo("atendimento")}>
        <Stethoscope size={14} /> Vincular atendimento
      </BotaoModo>
      <BotaoModo ativo={modo === "livre"} onClick={() => setModo("livre")}>
        <FlaskConical size={14} /> Conversa livre
      </BotaoModo>
    </div>
  );
}
