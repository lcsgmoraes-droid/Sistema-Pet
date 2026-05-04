import ModuleTabs from "../ui/ModuleTabs";

const ClientesNovoTabsBar = ({ tipoFiltro, setTipoFiltro, setPaginaAtual }) => {
  const tabs = [
    { id: "todos", label: "Todos" },
    { id: "cliente", label: "Clientes" },
    { id: "fornecedor", label: "Fornecedores" },
    { id: "veterinario", label: "Veterinarios" },
    { id: "funcionario", label: "Funcionarios" },
  ];

  const handleChange = (tabId) => {
    setTipoFiltro(tabId);
    setPaginaAtual(1);
  };

  return (
    <ModuleTabs
      active={tipoFiltro}
      ariaLabel="Filtros de pessoas"
      className="mb-6"
      onChange={handleChange}
      tabs={tabs}
    />
  );
};

export default ClientesNovoTabsBar;
