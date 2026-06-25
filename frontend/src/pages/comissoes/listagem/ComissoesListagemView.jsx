import { BarChart3, FileText, History, RotateCcw } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import ErrorState from "../../../components/ui/ErrorState";
import LoadingState from "../../../components/ui/LoadingState";
import ComissaoDetalhe from "../ComissaoDetalhe";
import ComissoesListagemFechamentoModal from "./ComissoesListagemFechamentoModal";
import ComissoesListagemFiltros from "./ComissoesListagemFiltros";
import ComissoesListagemResumo from "./ComissoesListagemResumo";
import ComissoesListagemTabela from "./ComissoesListagemTabela";

export default function ComissoesListagemView({ controller }) {
  const {
    carregarComissoes,
    comissaoSelecionada,
    comissoes,
    erro,
    fecharDetalhe,
    irParaHistoricoFechamentos,
    irParaRelatorios,
    loading,
  } = controller;

  if (loading) {
    return <LoadingState className="min-h-screen" label="Carregando comiss??es..." />;
  }

  if (erro) {
    return (
      <div className="p-6">
        <ErrorState
          title="Erro ao carregar comiss??es"
          description={erro}
          action={
            <ActionButton icon={RotateCcw} intent="delete" onClick={carregarComissoes}>
              Tentar novamente
            </ActionButton>
          }
        />
      </div>
    );
  }

  if (comissoes.length === 0) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Demonstrativo de Comiss??es</h1>

        <EmptyState
          description="Ainda n??o h?? registros de comiss??es no sistema."
          icon={FileText}
          title="Nenhuma comiss??o encontrada"
        />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Demonstrativo de Comiss??es</h1>
          <p className="text-gray-600 mt-1">Total de registros: {comissoes.length}</p>
        </div>

        <div className="flex gap-3">
          <ActionButton
            onClick={irParaRelatorios}
            icon={BarChart3}
            intent="info"
            size="md"
            tone="soft"
          >
            Relat??rios
          </ActionButton>

          <ActionButton
            onClick={irParaHistoricoFechamentos}
            icon={History}
            intent="neutral"
            size="md"
            tone="soft"
          >
            Ver Hist??rico
          </ActionButton>
        </div>
      </div>

      <ComissoesListagemResumo controller={controller} />
      <ComissoesListagemFiltros controller={controller} />
      <ComissoesListagemTabela controller={controller} />

      {comissaoSelecionada && (
        <ComissaoDetalhe comissaoId={comissaoSelecionada} onClose={fecharDetalhe} />
      )}

      <ComissoesListagemFechamentoModal controller={controller} />
    </div>
  );
}
