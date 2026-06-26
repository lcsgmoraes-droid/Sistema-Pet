import ComissaoConfiguracaoModal from "./ComissaoConfiguracaoModal";
import ComissoesList from "./ComissoesList";
import ComissoesPageHeader from "./ComissoesPageHeader";
import { useComissoesPageController } from "./useComissoesPageController";

export default function ComissoesPage() {
  const page = useComissoesPageController();

  if (page.loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <ComissoesPageHeader
        destacarComissoes={page.destacarComissoes}
        guiaClasses={page.guiaClasses}
        onNewCommission={() => page.abrirModal()}
      />

      {page.error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {page.error}
        </div>
      )}

      <ComissoesList
        destacarComissoes={page.destacarComissoes}
        funcionarios={page.funcionarios}
        guiaClasses={page.guiaClasses}
        onDuplicate={page.duplicarConfiguracao}
        onEdit={page.abrirModal}
      />

      {page.showModal && (
        <ComissaoConfiguracaoModal
          funcionarioId={page.funcionarioSelecionado}
          configuracoes={page.configuracoes}
          arvoreProdutos={page.arvoreProdutos}
          loading={page.loadingArvore}
          onClose={page.fecharModal}
          onSave={page.salvarModal}
        />
      )}
    </div>
  );
}
