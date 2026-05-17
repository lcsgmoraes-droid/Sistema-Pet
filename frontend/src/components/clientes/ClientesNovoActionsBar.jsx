import { GitMerge, Plus, Search, UploadCloud, X } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import IconActionButton from "../ui/IconActionButton";
import Panel from "../ui/Panel";

const ClientesNovoActionsBar = ({
  searchTerm,
  setSearchTerm,
  abrirPessoaPorCodigoNoEnter,
  setShowModalImportacao,
  openModal,
  tipoFiltro,
  pessoasSelecionadasFusao = [],
  onAbrirFusao,
  onLimparSelecaoFusao,
}) => {
  const labelNovo =
    tipoFiltro === "cliente"
      ? "Cliente"
      : tipoFiltro === "fornecedor"
        ? "Fornecedor"
        : tipoFiltro === "veterinario"
          ? "Veterinario"
          : tipoFiltro === "funcionario"
            ? "Funcionario"
            : "Cadastro";

  return (
    <Panel className="mb-6" padding="md">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative min-w-0 flex-1 lg:max-w-xl">
          <Search
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
            aria-hidden="true"
          />
          <input
            className="h-10 w-full rounded-lg border border-slate-200 bg-white py-2 pl-10 pr-4 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            type="text"
            placeholder="Buscar por codigo, nome, CPF/CNPJ, email ou telefone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                abrirPessoaPorCodigoNoEnter();
              }
            }}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          {pessoasSelecionadasFusao.length > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1">
              <ActionButton
                disabled={pessoasSelecionadasFusao.length !== 2}
                icon={GitMerge}
                intent="warning"
                onClick={onAbrirFusao}
                size="md"
                title={
                  pessoasSelecionadasFusao.length === 2
                    ? "Fundir pessoas selecionadas"
                    : "Selecione exatamente 2 pessoas"
                }
              >
                Fundir ({pessoasSelecionadasFusao.length})
              </ActionButton>
              <IconActionButton
                aria-label="Limpar selecao"
                icon={X}
                intent="warning"
                onClick={onLimparSelecaoFusao}
                size="md"
                title="Limpar selecao"
                tone="ghost"
              />
            </div>
          )}
          <ActionButton
            icon={UploadCloud}
            intent="neutral"
            onClick={() => setShowModalImportacao(true)}
            size="lg"
            tone="soft"
          >
            Importar Excel
          </ActionButton>
          <ActionButton
            icon={Plus}
            intent="create"
            onClick={() => openModal(null, tipoFiltro)}
            size="lg"
          >
            Novo {labelNovo}
          </ActionButton>
        </div>
      </div>
    </Panel>
  );
};

export default ClientesNovoActionsBar;
