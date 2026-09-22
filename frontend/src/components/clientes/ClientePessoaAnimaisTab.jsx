import { PawPrint } from "lucide-react";
import { FiPlus } from "react-icons/fi";
import ActionButton from "../ui/ActionButton";
import { buildNovoPetPath } from "../../utils/petReturnFlow";

export default function ClientePessoaAnimaisTab({ cliente, navigate, pets }) {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-5 dark:border-blue-500/30 dark:bg-blue-500/10">
        <div className="flex items-start gap-3">
          <PawPrint className="mt-1 flex-shrink-0 text-blue-600 dark:text-blue-300" size={24} />
          <div>
            <h4 className="mb-2 font-semibold text-blue-900 dark:text-blue-100">
              Gestão profissional de pets
            </h4>
            <p className="mb-3 text-sm text-blue-800 dark:text-blue-200">
              Os pets possuem um módulo dedicado com histórico médico, vacinas, consultas,
              serviços e muito mais.
            </p>
          </div>
        </div>
      </div>

      {pets.length > 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h4 className="mb-3 font-medium text-slate-900 dark:text-slate-100">
            Pets cadastrados ({pets.length})
          </h4>
          <div className="space-y-2">
            {pets.map((pet) => (
              <div
                key={pet.id || pet.nome}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800"
              >
                <div className="flex items-center gap-3">
                  <PawPrint className="text-blue-600 dark:text-blue-300" size={20} />
                  <div>
                    <p className="font-medium text-slate-900 dark:text-slate-100">{pet.nome}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {pet.especie} {pet.raca && `• ${pet.raca}`}
                    </p>
                  </div>
                </div>
                {pet.id ? (
                  <ActionButton intent="info" size="sm" onClick={() => navigate(`/pets/${pet.id}`)}>
                    Ver detalhes
                  </ActionButton>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ActionButton
          icon={PawPrint}
          intent="info"
          size="lg"
          onClick={() => navigate(`/pets?cliente_id=${cliente.id}`)}
        >
          Gerenciar pets
        </ActionButton>

        <ActionButton
          icon={FiPlus}
          intent="create"
          size="lg"
          onClick={() =>
            navigate(buildNovoPetPath({ tutorId: cliente.id, tutorNome: cliente.nome }))
          }
        >
          Adicionar pet
        </ActionButton>
      </div>
    </div>
  );
}
