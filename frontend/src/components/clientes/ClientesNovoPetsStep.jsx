import { PawPrint } from "lucide-react";
import { FiPlus } from "react-icons/fi";
import { buildNovoPetPath } from "../../utils/petReturnFlow";

const ClientesNovoPetsStep = ({ pets, editingCliente, navigate }) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <PawPrint className="text-blue-600" size={24} />
            Pets do Cliente
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Use o modulo dedicado para gerenciar pets com informacoes completas
          </p>
        </div>
      </div>

      <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-5">
        <div className="flex items-start gap-3">
          <PawPrint className="text-blue-600 flex-shrink-0 mt-1" size={24} />
          <div>
            <h4 className="font-semibold text-blue-900 mb-2">
              Gestao profissional de pets
            </h4>
            <p className="text-sm text-blue-800 mb-3">
              Agora os pets possuem um <strong>modulo dedicado</strong> com
              funcionalidades completas: historico medico, vacinas, consultas,
              servicos e muito mais.
            </p>
            <ul className="text-sm text-blue-800 space-y-1 mb-4">
              <li>Cadastro completo com campos veterinarios</li>
              <li>Historico de saude e medicacoes</li>
              <li>Controle de vacinas e consultas</li>
              <li>Timeline de eventos</li>
              <li>Preparado para uso clinico real</li>
            </ul>
          </div>
        </div>
      </div>

      {pets.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">
            Pets cadastrados ({pets.length})
          </h4>
          <div className="space-y-2">
            {pets.map((pet) => (
              <div
                key={pet.id || pet.nome}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-center gap-3">
                  <PawPrint className="text-blue-600" size={20} />
                  <div>
                    <p className="font-medium text-gray-900">{pet.nome}</p>
                    <p className="text-sm text-gray-600">
                      {pet.especie} {pet.raca && `• ${pet.raca}`}
                    </p>
                  </div>
                </div>
                {pet.id && (
                  <button
                    onClick={() => navigate(`/pets/${pet.id}`)}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors"
                  >
                    Ver detalhes
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          type="button"
          onClick={() => {
            if (editingCliente?.id) {
              navigate(`/pets?cliente_id=${editingCliente.id}`);
            } else {
              alert("Salve o cliente primeiro para gerenciar pets");
            }
          }}
          className="flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition-all font-semibold shadow-md"
        >
          <PawPrint size={24} />
          <div className="text-left">
            <div>Gerenciar pets</div>
            <div className="text-xs font-normal opacity-90">
              Modulo completo de gestao
            </div>
          </div>
        </button>

        <button
          type="button"
          onClick={() => {
            if (editingCliente?.id) {
              navigate(
                buildNovoPetPath({
                  tutorId: editingCliente.id,
                  tutorNome: editingCliente.nome,
                })
              );
            } else {
              alert("Salve o cliente primeiro para adicionar pets");
            }
          }}
          className="flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-lg transition-all font-semibold shadow-md"
        >
          <FiPlus size={24} />
          <div className="text-left">
            <div>Adicionar pet</div>
            <div className="text-xs font-normal opacity-90">
              Cadastro completo
            </div>
          </div>
        </button>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          <strong>Dica:</strong> Pets podem ser adicionados agora ou depois.
          Todas as informacoes medicas e historico ficam no modulo dedicado de
          pets.
        </p>
      </div>

      {!editingCliente && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <p className="text-sm text-orange-800">
            <strong>Atencao:</strong> Salve o cliente primeiro (etapa 6) para
            poder gerenciar seus pets.
          </p>
        </div>
      )}
    </div>
  );
};

export default ClientesNovoPetsStep;
