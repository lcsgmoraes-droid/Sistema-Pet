import CategoriaFinanceiraModal from "./CategoriaFinanceiraModal";
import ModalNovaContaPagarDialog from "./ModalNovaContaPagarDialog";
import { useModalNovaContaPagarController } from "./useModalNovaContaPagarController";

export default function ModalNovaContaPagar({ isOpen, onClose, onSave, contaEdicao = null }) {
  const controller = useModalNovaContaPagarController({
    isOpen,
    onClose,
    onSave,
    contaEdicao,
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <ModalNovaContaPagarDialog
        controller={controller}
        onClose={onClose}
        onOpenCategoria={() => controller.setShowModalCategoria(true)}
      />

      <CategoriaFinanceiraModal
        formCategoria={controller.formCategoria}
        isOpen={controller.showModalCategoria}
        onAdicionarSubcategoria={controller.adicionarSubcategoriaNova}
        onClose={() => controller.setShowModalCategoria(false)}
        onKeyDownSubcategoria={controller.handleKeyDownSubcategoria}
        onRemoverSubcategoria={controller.removerSubcategoriaNova}
        onSubmit={controller.handleSubmitCategoria}
        onUpdateSubcategoria={controller.atualizarSubcategoriaNova}
        setFormCategoria={controller.setFormCategoria}
      />
    </div>
  );
}
