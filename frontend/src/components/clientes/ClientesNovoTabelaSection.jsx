import { Fragment } from "react";
import {
  FiArrowRight,
  FiDollarSign,
  FiEdit2,
  FiMessageCircle,
  FiTrash2,
  FiUser,
} from "react-icons/fi";
import { PawPrint } from "lucide-react";
import ClientesNovoPaginationControls from "./ClientesNovoPaginationControls";

const ClientesNovoTabelaSection = ({
  loading,
  totalRegistros,
  paginaAtual,
  registrosPorPagina,
  setRegistrosPorPagina,
  setPaginaAtual,
  filteredClientes,
  highlightedClienteId,
  expandedPets,
  setExpandedPets,
  highlightedPetId,
  setHighlightedPetId,
  openModal,
  handleDelete,
  handleDeletePet,
}) => {
  return (
    <>
      <ClientesNovoPaginationControls
        loading={loading}
        totalRegistros={totalRegistros}
        paginaAtual={paginaAtual}
        registrosPorPagina={registrosPorPagina}
        setRegistrosPorPagina={setRegistrosPorPagina}
        setPaginaAtual={setPaginaAtual}
        variant="top"
      />

      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        {filteredClientes.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nome
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    CPF/CNPJ
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Celular
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Pets
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Segmento
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acoes
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredClientes.map((cliente) => {
                  const clienteDestacado = highlightedClienteId === cliente.id;

                  return (
                    <Fragment key={cliente.id}>
                      <tr
                        id={`cliente-${cliente.id}`}
                        onClick={() => openModal(cliente)}
                        className={`cursor-pointer transition-colors ${
                          clienteDestacado
                            ? "bg-emerald-50 hover:bg-emerald-100"
                            : "hover:bg-gray-50"
                        }`}
                      >
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                          {cliente.codigo}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex flex-col gap-1">
                            <span className="text-sm font-medium text-gray-900">
                              {cliente.nome}
                            </span>
                            {cliente.tipo_pessoa === "PJ" &&
                              cliente.razao_social && (
                                <span className="text-xs text-gray-500">
                                  {cliente.razao_social}
                                </span>
                              )}
                            {cliente.parceiro_ativo && (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full w-fit">
                                <FiDollarSign size={12} />
                                Parceiro
                              </span>
                            )}
                            {cliente.de_parceiro && (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full w-fit">
                                Pet Shop Parceiro
                              </span>
                            )}
                            {clienteDestacado && (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full w-fit">
                                Recem cadastrado
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                          {cliente.tipo_pessoa === "PF"
                            ? cliente.cpf || "-"
                            : cliente.cnpj || "-"}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                          {cliente.celular || "-"}
                        </td>
                        <td
                          className="px-4 py-3 whitespace-nowrap"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={() =>
                              setExpandedPets({
                                ...expandedPets,
                                [cliente.id]: !expandedPets[cliente.id],
                              })
                            }
                            className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 transition-colors"
                          >
                            <PawPrint size={16} className="text-gray-400" />
                            <span>{cliente.pets?.length || 0}</span>
                            {cliente.pets && cliente.pets.length > 0 && (
                              <FiArrowRight
                                size={14}
                                className={`transform transition-transform ${
                                  expandedPets[cliente.id] ? "rotate-90" : ""
                                }`}
                              />
                            )}
                          </button>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-xs text-gray-400">-</span>
                        </td>
                        <td
                          className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="flex items-center justify-end gap-2">
                            {cliente.celular && (
                              <button
                                onClick={() => {
                                  const celular = cliente.celular.replace(
                                    /\D/g,
                                    "",
                                  );
                                  window.open(
                                    `https://wa.me/55${celular}`,
                                    "_blank",
                                  );
                                }}
                                className="text-green-600 hover:text-green-900 transition-colors"
                                title="Abrir WhatsApp"
                              >
                                <FiMessageCircle size={16} />
                              </button>
                            )}
                            <button
                              onClick={() => openModal(cliente)}
                              className="text-blue-600 hover:text-blue-900 transition-colors"
                              title="Editar"
                            >
                              <FiEdit2 size={16} />
                            </button>
                            {!cliente.de_parceiro && (
                              <button
                                onClick={() => handleDelete(cliente.id)}
                                className="text-red-600 hover:text-red-900 transition-colors"
                                title="Excluir"
                              >
                                <FiTrash2 size={16} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>

                      {expandedPets[cliente.id] &&
                        cliente.pets &&
                        cliente.pets.length > 0 && (
                          <tr>
                            <td colSpan="7" className="px-4 py-3 bg-gray-50">
                              <div className="space-y-2">
                                <p className="text-xs font-semibold text-gray-700 mb-2">
                                  Pets de {cliente.nome}:
                                </p>
                                {cliente.pets.map((pet) => (
                                  <div
                                    key={pet.id}
                                    className={`bg-white rounded-lg p-3 flex justify-between items-start border border-gray-200 ${
                                      highlightedPetId === pet.id
                                        ? "ring-2 ring-blue-400 shadow-lg bg-blue-50"
                                        : ""
                                    }`}
                                  >
                                    <div className="flex-1 grid grid-cols-4 gap-4">
                                      <div>
                                        <p className="text-xs text-gray-500">
                                          Nome
                                        </p>
                                        <p className="text-sm font-medium text-gray-900">
                                          {pet.nome}
                                        </p>
                                      </div>
                                      <div>
                                        <p className="text-xs text-gray-500">
                                          Especie/Raca
                                        </p>
                                        <p className="text-sm text-gray-700">
                                          {pet.especie}{" "}
                                          {pet.raca && `- ${pet.raca}`}
                                        </p>
                                      </div>
                                      <div>
                                        <p className="text-xs text-gray-500">
                                          Sexo
                                        </p>
                                        <p className="text-sm text-gray-700">
                                          {pet.sexo || "-"}
                                        </p>
                                      </div>
                                      <div>
                                        <p className="text-xs text-gray-500">
                                          Nascimento
                                        </p>
                                        <p className="text-sm text-gray-700">
                                          {pet.data_nascimento
                                            ? new Date(
                                                pet.data_nascimento,
                                              ).toLocaleDateString("pt-BR")
                                            : "-"}
                                        </p>
                                      </div>
                                    </div>
                                    <div className="flex gap-2 ml-4">
                                      <button
                                        onClick={() => {
                                          setHighlightedPetId(pet.id);
                                          openModal(cliente, null, pet.id);
                                        }}
                                        className="text-blue-600 hover:text-blue-900 p-1 transition-colors"
                                        title="Editar pet"
                                      >
                                        <FiEdit2 size={14} />
                                      </button>
                                      <button
                                        onClick={() => handleDeletePet(pet.id)}
                                        className="text-red-600 hover:text-red-900 p-1 transition-colors"
                                        title="Excluir pet"
                                      >
                                        <FiTrash2 size={14} />
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </td>
                          </tr>
                        )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <FiUser className="mx-auto text-gray-400 mb-4" size={48} />
            <p className="text-gray-600">Nenhum cliente encontrado</p>
          </div>
        )}

        <ClientesNovoPaginationControls
          loading={loading}
          totalRegistros={totalRegistros}
          paginaAtual={paginaAtual}
          registrosPorPagina={registrosPorPagina}
          setRegistrosPorPagina={setRegistrosPorPagina}
          setPaginaAtual={setPaginaAtual}
          variant="bottom"
        />
      </div>
    </>
  );
};

export default ClientesNovoTabelaSection;
