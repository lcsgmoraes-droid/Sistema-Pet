export default function ComissoesList({
  destacarComissoes,
  funcionarios,
  guiaClasses,
  onDuplicate,
  onEdit,
}) {
  return (
    <div className={`bg-white rounded-lg shadow ${destacarComissoes ? guiaClasses.box : ""}`}>
      {funcionarios.length === 0 ? (
        <div className="p-8 text-center text-gray-500">
          <p className="text-lg mb-2">Nenhuma comissão configurada</p>
          <p className="text-sm">Clique em "Nova Comissão" para começar</p>
        </div>
      ) : (
        <div className="divide-y">
          {funcionarios.map((funcionario) => (
            <div
              key={funcionario.id}
              className="p-4 hover:bg-gray-50 transition-colors cursor-pointer"
              onClick={() => onEdit(funcionario.id)}
            >
              <div className="flex justify-between items-center">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-blue-600 font-semibold">
                        {funcionario.nome.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-800">{funcionario.nome}</h3>
                      <p className="text-sm text-gray-500">{funcionario.cargo}</p>
                    </div>
                  </div>
                  <div className="mt-2 flex gap-4 text-sm text-gray-600">
                    <span>
                      <strong>{funcionario.categorias}</strong> categorias
                    </span>
                    <span>
                      <strong>{funcionario.subcategorias}</strong> subcategorias
                    </span>
                    <span>
                      <strong>{funcionario.produtos}</strong> produtos específicos
                    </span>
                    <span>
                      <strong>{funcionario.gerais || 0}</strong> regra geral
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      onEdit(funcionario.id);
                    }}
                    className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
                  >
                    Editar
                  </button>
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      onDuplicate(funcionario.id);
                    }}
                    className="px-3 py-1 text-gray-600 hover:bg-gray-100 rounded"
                    title="Duplicar configuração para outro parceiro"
                  >
                    Duplicar
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
