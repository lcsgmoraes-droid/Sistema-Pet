import { FiAlertCircle, FiArrowLeft } from "react-icons/fi";

export default function PetDetalhesErrorState({ error, onBack }) {
  return (
    <div className="p-6">
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
        <FiAlertCircle />
        {error || "Pet nÃ£o encontrado"}
      </div>
      <button
        onClick={onBack}
        className="mt-4 flex items-center gap-2 text-blue-600 hover:text-blue-700"
      >
        <FiArrowLeft />
        Voltar para lista de pets
      </button>
    </div>
  );
}
