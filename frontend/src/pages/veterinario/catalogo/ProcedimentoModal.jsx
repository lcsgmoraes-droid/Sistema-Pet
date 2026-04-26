import ProcedimentoDadosForm from "./ProcedimentoDadosForm";
import ProcedimentoInsumosSection from "./ProcedimentoInsumosSection";
import { Modal } from "./shared";

export default function ProcedimentoModal({
  adicionarInsumo,
  atualizarInsumo,
  editando,
  form,
  onClose,
  onSave,
  produtos,
  removerInsumo,
  resumoMargem,
  salvando,
  setCampo,
}) {
  return (
    <Modal
      titulo={editando ? "Editar procedimento" : "Novo procedimento"}
      subtitulo="Monte o procedimento com duracao, preco e insumos que devem sair do estoque."
      onClose={onClose}
      onSave={onSave}
      salvando={salvando}
    >
      <div className="space-y-4">
        <ProcedimentoDadosForm form={form} setCampo={setCampo} />

        <ProcedimentoInsumosSection
          adicionarInsumo={adicionarInsumo}
          atualizarInsumo={atualizarInsumo}
          form={form}
          produtos={produtos}
          removerInsumo={removerInsumo}
          resumoMargem={resumoMargem}
        />
      </div>
    </Modal>
  );
}
