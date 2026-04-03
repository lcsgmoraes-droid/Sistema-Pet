const ClientesNovoTabsBar = ({ tipoFiltro, setTipoFiltro, setPaginaAtual }) => {
  const tabs = [
    { value: "todos", label: "Todos" },
    { value: "cliente", label: "Clientes" },
    { value: "fornecedor", label: "Fornecedores" },
    { value: "veterinario", label: "Veterinários" },
    { value: "funcionario", label: "Funcionários" },
  ];

  return (
    <div className="mb-6 border-b border-gray-200">
      <div className="flex gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => {
              setTipoFiltro(tab.value);
              setPaginaAtual(1);
            }}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === tab.value
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default ClientesNovoTabsBar;
