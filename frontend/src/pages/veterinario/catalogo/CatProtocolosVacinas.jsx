import CatalogoErro from "./CatalogoErro";
import ProtocoloVacinaModal from "./ProtocoloVacinaModal";
import ProtocolosVacinasTabela from "./ProtocolosVacinasTabela";
import ProtocolosVacinasToolbar from "./ProtocolosVacinasToolbar";
import { useCatProtocolosVacinas } from "./useCatProtocolosVacinas";

export default function CatProtocolosVacinas() {
  const protocolos = useCatProtocolosVacinas();

  return (
    <div className="space-y-3">
      <ProtocolosVacinasToolbar onNovo={protocolos.abrirNovo} />
      <CatalogoErro erro={protocolos.erro} />
      <ProtocolosVacinasTabela
        carregando={protocolos.carregando}
        lista={protocolos.lista}
        removendoId={protocolos.removendoId}
        onEditar={protocolos.abrirEdicao}
        onExcluir={protocolos.excluir}
      />
      {protocolos.modalAberto && (
        <ProtocoloVacinaModal
          editando={protocolos.editando}
          form={protocolos.form}
          salvando={protocolos.salvando}
          onClose={protocolos.fecharModal}
          onSave={protocolos.salvar}
          onSetCampo={protocolos.setCampo}
        />
      )}
    </div>
  );
}
