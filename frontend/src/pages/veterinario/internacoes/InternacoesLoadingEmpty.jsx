import { BedDouble } from "lucide-react";

export function InternacoesLoadingState() {
  return (
    <div className="flex justify-center py-10">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
    </div>
  );
}

export function InternacoesEmptyState({ aba }) {
  return (
    <div className="p-10 text-center bg-white border border-gray-200 rounded-xl">
      <BedDouble size={36} className="mx-auto text-gray-200 mb-3" />
      <p className="text-gray-400 text-sm">
        Nenhuma internação {aba === "ativas" ? "ativa" : "registrada"}.
      </p>
    </div>
  );
}
