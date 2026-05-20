import { Fragment } from "react";
import {
  ArrowRight,
  DollarSign,
  Edit2,
  MessageCircle,
  PawPrint,
  Trash2,
  UsersRound,
} from "lucide-react";
import EmptyState from "../ui/EmptyState";
import IconActionButton from "../ui/IconActionButton";
import PaginationControls from "../ui/PaginationControls";
import Panel from "../ui/Panel";

function formatarDocumentoPessoa(cliente) {
  if (cliente.tipo_pessoa === "PF") return cliente.cpf || "-";
  return cliente.cnpj || "-";
}

function PessoaMobileCard({
  cliente,
  clienteDestacado,
  clienteSelecionadoFusao,
  expandedPets,
  handleDelete,
  handleDeletePet,
  highlightedPetId,
  openModal,
  setExpandedPets,
  setHighlightedPetId,
  togglePessoaFusao,
}) {
  const pets = Array.isArray(cliente.pets) ? cliente.pets : [];
  const petsAberto = Boolean(expandedPets[cliente.id]);

  return (
    <article
      id={`cliente-${cliente.id}`}
      onClick={() => openModal(cliente)}
      className={`rounded-lg border bg-white p-3 shadow-sm transition-colors ${
        clienteSelecionadoFusao
          ? "border-amber-200 bg-amber-50"
          : clienteDestacado
            ? "border-emerald-200 bg-emerald-50"
            : "border-slate-200"
      }`}
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={clienteSelecionadoFusao}
          onClick={(event) => event.stopPropagation()}
          onChange={() => togglePessoaFusao?.(cliente.id)}
          className="mt-1 h-5 w-5 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
          aria-label={`Selecionar ${cliente.nome} para fusao`}
        />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
            <span className="rounded-full bg-slate-100 px-2 py-0.5 font-mono">
              ID {cliente.codigo || "-"}
            </span>
            {cliente.tipo_pessoa ? (
              <span className="rounded-full bg-slate-100 px-2 py-0.5">
                {cliente.tipo_pessoa}
              </span>
            ) : null}
            {clienteDestacado ? (
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-700">
                Recem cadastrado
              </span>
            ) : null}
          </div>

          <h3 className="mt-2 text-sm font-semibold leading-5 text-slate-950">
            {cliente.nome}
          </h3>
          {cliente.tipo_pessoa === "PJ" && cliente.razao_social ? (
            <p className="mt-0.5 text-xs text-slate-500">{cliente.razao_social}</p>
          ) : null}

          <div className="mt-2 flex flex-wrap gap-1.5">
            {cliente.parceiro_ativo ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                <DollarSign size={12} />
                Parceiro
              </span>
            ) : null}
            {cliente.de_parceiro ? (
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                Pet Shop Parceiro
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">
          <dt className="font-semibold uppercase text-slate-500">Documento</dt>
          <dd className="mt-1 break-words text-slate-800">
            {formatarDocumentoPessoa(cliente)}
          </dd>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">
          <dt className="font-semibold uppercase text-slate-500">Celular</dt>
          <dd className="mt-1 break-words text-slate-800">{cliente.celular || "-"}</dd>
        </div>
      </dl>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            setExpandedPets({
              ...expandedPets,
              [cliente.id]: !expandedPets[cliente.id],
            });
          }}
          className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
        >
          <PawPrint size={16} className="text-slate-400" />
          {pets.length} pet{pets.length === 1 ? "" : "s"}
          {pets.length > 0 ? (
            <ArrowRight
              size={14}
              className={`transition-transform ${petsAberto ? "rotate-90" : ""}`}
            />
          ) : null}
        </button>

        <div className="ml-auto flex items-center gap-1.5" onClick={(event) => event.stopPropagation()}>
          {cliente.celular ? (
            <IconActionButton
              onClick={() => {
                const celular = cliente.celular.replace(/\D/g, "");
                window.open(`https://wa.me/55${celular}`, "_blank");
              }}
              icon={MessageCircle}
              intent="create"
              tone="ghost"
              title="Abrir WhatsApp"
              aria-label="Abrir WhatsApp"
            />
          ) : null}
          <IconActionButton
            onClick={() => openModal(cliente)}
            icon={Edit2}
            intent="edit"
            tone="ghost"
            title="Editar"
            aria-label="Editar"
          />
          {!cliente.de_parceiro ? (
            <IconActionButton
              onClick={() => handleDelete(cliente.id)}
              icon={Trash2}
              intent="delete"
              tone="ghost"
              title="Excluir"
              aria-label="Excluir"
            />
          ) : null}
        </div>
      </div>

      {petsAberto && pets.length > 0 ? (
        <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          {pets.map((pet) => (
            <div
              key={pet.id}
              className={`rounded-lg border p-3 ${
                highlightedPetId === pet.id
                  ? "border-blue-300 bg-blue-50"
                  : "border-slate-200 bg-slate-50"
              }`}
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900">{pet.nome}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {[pet.especie, pet.raca].filter(Boolean).join(" - ") || "Sem especie/raca"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {pet.sexo || "-"} |{" "}
                    {pet.data_nascimento
                      ? new Date(pet.data_nascimento).toLocaleDateString("pt-BR")
                      : "Sem nascimento"}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <IconActionButton
                    onClick={() => {
                      setHighlightedPetId(pet.id);
                      openModal(cliente, null, pet.id);
                    }}
                    icon={Edit2}
                    intent="edit"
                    tone="ghost"
                    size="xs"
                    title="Editar pet"
                    aria-label="Editar pet"
                  />
                  <IconActionButton
                    onClick={() => handleDeletePet(pet.id)}
                    icon={Trash2}
                    intent="delete"
                    tone="ghost"
                    size="xs"
                    title="Excluir pet"
                    aria-label="Excluir pet"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

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
  pessoasSelecionadasFusao = [],
  togglePessoaFusao,
}) => {
  return (
    <>
      <PaginationControls
        currentPage={paginaAtual}
        itemName="pessoas"
        itemsPerPage={registrosPorPagina}
        loading={loading}
        onItemsPerPageChange={(value) => {
          setRegistrosPorPagina(Number(value));
          setPaginaAtual(1);
        }}
        onPageChange={setPaginaAtual}
        totalItems={totalRegistros}
        variant="top"
      />

      <Panel className="overflow-hidden" padding="none">
        {filteredClientes.length > 0 ? (
          <>
            <div className="space-y-3 bg-slate-50 p-3 md:hidden">
              {filteredClientes.map((cliente) => (
                <PessoaMobileCard
                  key={cliente.id}
                  cliente={cliente}
                  clienteDestacado={highlightedClienteId === cliente.id}
                  clienteSelecionadoFusao={pessoasSelecionadasFusao.includes(
                    cliente.id,
                  )}
                  expandedPets={expandedPets}
                  handleDelete={handleDelete}
                  handleDeletePet={handleDeletePet}
                  highlightedPetId={highlightedPetId}
                  openModal={openModal}
                  setExpandedPets={setExpandedPets}
                  setHighlightedPetId={setHighlightedPetId}
                  togglePessoaFusao={togglePessoaFusao}
                />
              ))}
            </div>

            <div className="hidden overflow-x-auto md:block">
              <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="w-12 px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                    Fusao
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                    Nome
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                    CPF/CNPJ
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                    Celular
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                    Pets
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                    Segmento
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">
                    Acoes
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {filteredClientes.map((cliente) => {
                  const clienteDestacado = highlightedClienteId === cliente.id;
                  const clienteSelecionadoFusao = pessoasSelecionadasFusao.includes(cliente.id);

                  return (
                    <Fragment key={cliente.id}>
                      <tr
                        id={`cliente-${cliente.id}`}
                        onClick={() => openModal(cliente)}
                        className={`cursor-pointer transition-colors ${
                          clienteSelecionadoFusao
                            ? "bg-amber-50 hover:bg-amber-100"
                            : clienteDestacado
                            ? "bg-emerald-50 hover:bg-emerald-100"
                            : "hover:bg-gray-50"
                        }`}
                      >
                        <td
                          className="px-4 py-3"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={clienteSelecionadoFusao}
                            onChange={() => togglePessoaFusao?.(cliente.id)}
                            className="h-4 w-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                            aria-label={`Selecionar ${cliente.nome} para fusao`}
                          />
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                          {cliente.codigo}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex flex-col gap-1">
                            <span className="text-sm font-medium text-slate-900">
                              {cliente.nome}
                            </span>
                            {cliente.tipo_pessoa === "PJ" &&
                              cliente.razao_social && (
                                <span className="text-xs text-slate-500">
                                  {cliente.razao_social}
                                </span>
                              )}
                            {cliente.parceiro_ativo && (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full w-fit">
                                <DollarSign size={12} />
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
                              <ArrowRight
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
                              <IconActionButton
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
                                icon={MessageCircle}
                                intent="create"
                                tone="ghost"
                                title="Abrir WhatsApp"
                                aria-label="Abrir WhatsApp"
                              />
                            )}
                            <IconActionButton
                              onClick={() => openModal(cliente)}
                              icon={Edit2}
                              intent="edit"
                              tone="ghost"
                              title="Editar"
                              aria-label="Editar"
                            />
                            {!cliente.de_parceiro && (
                              <IconActionButton
                                onClick={() => handleDelete(cliente.id)}
                                icon={Trash2}
                                intent="delete"
                                tone="ghost"
                                title="Excluir"
                                aria-label="Excluir"
                              />
                            )}
                          </div>
                        </td>
                      </tr>

                      {expandedPets[cliente.id] &&
                        cliente.pets &&
                        cliente.pets.length > 0 && (
                          <tr>
                            <td colSpan="8" className="px-4 py-3 bg-gray-50">
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
                                      <IconActionButton
                                        onClick={() => {
                                          setHighlightedPetId(pet.id);
                                          openModal(cliente, null, pet.id);
                                        }}
                                        icon={Edit2}
                                        intent="edit"
                                        tone="ghost"
                                        size="xs"
                                        title="Editar pet"
                                        aria-label="Editar pet"
                                      />
                                      <IconActionButton
                                        onClick={() => handleDeletePet(pet.id)}
                                        icon={Trash2}
                                        intent="delete"
                                        tone="ghost"
                                        size="xs"
                                        title="Excluir pet"
                                        aria-label="Excluir pet"
                                      />
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
          </>
        ) : (
          <EmptyState
            className="rounded-none border-0 shadow-none"
            icon={UsersRound}
            title="Nenhuma pessoa encontrada"
            description="Use a busca ou cadastre uma nova pessoa para iniciar."
          />
        )}

        <PaginationControls
          currentPage={paginaAtual}
          itemName="pessoas"
          itemsPerPage={registrosPorPagina}
          loading={loading}
          onItemsPerPageChange={(value) => {
            setRegistrosPorPagina(Number(value));
            setPaginaAtual(1);
          }}
          onPageChange={setPaginaAtual}
          totalItems={totalRegistros}
          variant="bottom"
        />
      </Panel>
    </>
  );
};

export default ClientesNovoTabelaSection;
