import { BedDouble } from "lucide-react";
import EmptyState from "../../../components/ui/EmptyState";
import LoadingState from "../../../components/ui/LoadingState";

export function InternacoesLoadingState() {
  return <LoadingState label="Carregando internacoes..." />;
}

export function InternacoesEmptyState({ aba }) {
  return (
    <EmptyState
      icon={BedDouble}
      title={`Nenhuma internacao ${aba === "ativas" ? "ativa" : "registrada"}.`}
    />
  );
}
