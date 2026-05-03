import { CreditCard } from "lucide-react";
import EmptyState from "../ui/EmptyState";

function OperadoraCartaoEmptyState() {
  return (
    <EmptyState
      className="bg-gray-50"
      description='Clique em "Nova Operadora" para comecar'
      icon={CreditCard}
      title="Nenhuma operadora cadastrada"
    />
  );
}

export default OperadoraCartaoEmptyState;
