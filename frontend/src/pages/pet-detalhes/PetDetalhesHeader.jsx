import { FiArrowLeft, FiCheckCircle, FiEdit2, FiPhone, FiUser, FiXCircle } from "react-icons/fi";
import { PawPrint } from "lucide-react";
import CustomerIdentity from "../../components/ui/CustomerIdentity";

export default function PetDetalhesHeader({ onBack, onEdit, onToggleStatus, pet }) {
  return (
    <div className="mb-6">
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
      >
        <FiArrowLeft />
        Voltar para Gerenciamento de Pets
      </button>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-6">
            {pet.foto_url ? (
              <img
                src={pet.foto_url}
                alt={pet.nome}
                className="w-24 h-24 rounded-full object-cover border-4 border-gray-200"
              />
            ) : (
              <div className="w-24 h-24 rounded-full bg-blue-100 flex items-center justify-center border-4 border-gray-200">
                <PawPrint className="text-blue-600" size={48} />
              </div>
            )}
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-900">{pet.nome}</h1>
                {pet.ativo ? (
                  <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium flex items-center gap-1">
                    <FiCheckCircle size={14} />
                    Ativo
                  </span>
                ) : (
                  <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium flex items-center gap-1">
                    <FiXCircle size={14} />
                    Inativo
                  </span>
                )}
              </div>
              <p className="text-gray-500 mb-1">
                {pet.especie} {pet.raca && `â€¢ ${pet.raca}`} {pet.sexo && `â€¢ ${pet.sexo}`}
              </p>
              <p className="text-sm text-gray-400">{pet.codigo}</p>

              <div className="mt-3 flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2 text-gray-700">
                  <FiUser size={16} />
                  <span className="font-medium">Tutor:</span>
                  <CustomerIdentity
                    codeLabel="Cod. tutor"
                    fallback={`Tutor #${pet.cliente_id || "-"}`}
                    layout="inline"
                    nameClassName="font-medium text-blue-600"
                    record={pet}
                  />
                </div>
                {pet.cliente_celular && (
                  <div className="flex items-center gap-2 text-gray-700">
                    <FiPhone size={16} />
                    <span>{pet.cliente_celular}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={onEdit}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            >
              <FiEdit2 />
              Editar
            </button>
            <button
              onClick={onToggleStatus}
              className={`px-4 py-2 border-2 rounded-lg transition-colors font-medium ${
                pet.ativo
                  ? "border-red-300 text-red-600 hover:bg-red-50"
                  : "border-green-300 text-green-600 hover:bg-green-50"
              }`}
            >
              {pet.ativo ? "Desativar" : "Reativar"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
