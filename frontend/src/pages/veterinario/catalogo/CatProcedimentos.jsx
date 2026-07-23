import CatalogoErro from "./CatalogoErro";
import ProcedimentoModal from "./ProcedimentoModal";
import ProcedimentosModeloCorePetBanner from "./ProcedimentosModeloCorePetBanner";
import ProcedimentosTabela from "./ProcedimentosTabela";
import ProcedimentosToolbar from "./ProcedimentosToolbar";
import { useCatProcedimentos } from "./useCatProcedimentos";

export default function CatProcedimentos() {
  const catalogo = useCatProcedimentos();

  return (
    <div className="space-y-3">
      <ProcedimentosModeloCorePetBanner
        importando={catalogo.importandoModelo}
        onImportar={catalogo.importarModeloCorePet}
        status={catalogo.statusModelo}
      />

      <ProcedimentosToolbar onNovo={catalogo.abrirNovo} />

      <CatalogoErro erro={catalogo.erro} />

      <ProcedimentosTabela
        carregando={catalogo.carregando}
        lista={catalogo.lista}
        onEditar={catalogo.abrirEdicao}
        onExcluir={catalogo.excluir}
        removendoId={catalogo.removendoId}
      />

      {catalogo.modalAberto && (
        <ProcedimentoModal
          adicionarInsumo={catalogo.adicionarInsumo}
          atualizarInsumo={catalogo.atualizarInsumo}
          editando={catalogo.editando}
          form={catalogo.form}
          onClose={catalogo.fecharModal}
          onSave={catalogo.salvar}
          produtos={catalogo.produtos}
          removerInsumo={catalogo.removerInsumo}
          resumoMargem={catalogo.resumoMargem}
          salvando={catalogo.salvando}
          setCampo={catalogo.setCampo}
        />
      )}
    </div>
  );
}
