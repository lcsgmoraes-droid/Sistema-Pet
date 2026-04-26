import { AlertCircle } from "lucide-react";

export default function CatalogoErro({ erro }) {
  if (!erro) return null;

  return (
    <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
      <AlertCircle size={16} />
      <span>{erro}</span>
    </div>
  );
}
