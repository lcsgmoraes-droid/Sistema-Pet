import { AlertCircle } from "lucide-react";

export default function InternacoesAlert({ erro, onClose }) {
  if (!erro) return null;

  return (
    <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
      <AlertCircle size={16} />
      <span>{erro}</span>
      <button type="button" className="ml-auto" onClick={onClose} aria-label="Fechar alerta">
        x
      </button>
    </div>
  );
}
