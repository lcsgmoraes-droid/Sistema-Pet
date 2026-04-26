import CatalogoErro from "./CatalogoErro";
import MedicamentoModal from "./MedicamentoModal";
import MedicamentosTabela from "./MedicamentosTabela";
import MedicamentosToolbar from "./MedicamentosToolbar";
import { useCatMedicamentos } from "./useCatMedicamentos";

export default function CatMedicamentos() {
  const catalogo = useCatMedicamentos();

  return (
    <div className="space-y-3">
      <MedicamentosToolbar busca={catalogo.busca} onBuscaChange={catalogo.setBusca} onNovo={catalogo.abrirNovo} />

      <CatalogoErro erro={catalogo.erro} />

      <MedicamentosTabela
        buscando={catalogo.buscando}
        lista={catalogo.lista}
        onEditar={catalogo.abrirEdicao}
        onExcluir={catalogo.excluir}
        removendoId={catalogo.removendoId}
      />

      {catalogo.modalAberto && (
        <MedicamentoModal
          editando={catalogo.editando}
          form={catalogo.form}
          onClose={catalogo.fecharModal}
          onSave={catalogo.salvar}
          salvando={catalogo.salvando}
          setCampo={catalogo.setCampo}
        />
      )}
    </div>
  );
}
