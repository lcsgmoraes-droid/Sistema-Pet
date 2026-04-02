import { CreditCard } from "lucide-react";

function OperadoraCartaoEmptyState() {
  return (
    <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
      <CreditCard className="w-12 h-12 text-gray-400 mx-auto mb-3" />
      <p className="text-gray-600">Nenhuma operadora cadastrada</p>
      <p className="text-sm text-gray-500">Clique em "Nova Operadora" para comecar</p>
    </div>
  );
}

export default OperadoraCartaoEmptyState;
