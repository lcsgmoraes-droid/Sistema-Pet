import { FileText, GitMerge, Plus, UploadCloud, X } from "lucide-react";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BuscaPessoa from "../v2/BuscaPessoa/BuscaPessoa";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import Panel from "../ui/Panel";

const ClientesNovoActionsBar = ({
  searchTerm,
  setSearchTerm,
  abrirPessoaPorCodigoNoEnter,
  setShowModalImportacao,
  openModal,
  tipoFiltro,
  modoFusaoAtivo = false,
  pessoasSelecionadasFusao = [],
  onAbrirFusao,
  onAbrirRelatorio,
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
          <BuscaPessoa
            className="h-10 w-full rounded-lg border border-slate-200 bg-white py-2 pl-10 pr-4 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            type="text"
            placeholder="Buscar por codigo, nome, CPF/CNPJ, email ou telefone..."
            value={searchTerm}
            onChange={setSearchTerm}
            showSuggestions={false}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                abrirPessoaPorCodigoNoEnter();
              }
            }}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          {modoFusaoAtivo && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1">
              <span className="px-1 text-xs font-medium text-amber-800">
                {pessoasSelecionadasFusao.length === 2
                  ? "2 pessoas selecionadas"
                  : "Selecione mais 1 pessoa para fundir"}
              </span>
              <BotaoInteracao
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
              </BotaoInteracao>
              <BotaoCancelar
                aria-label="Cancelar fusao"
                icon={X}
                intent="warning"
                onClick={onLimparSelecaoFusao}
                size="md"
                title="Cancelar fusao"
                tone="ghost"
              />
            </div>
          )}
          <BotaoInteracao
            icon={FileText}
            intent="info"
            onClick={onAbrirRelatorio}
            size="lg"
            tone="soft"
          >
            Relatorios
          </BotaoInteracao>
          <BotaoInteracao
            icon={UploadCloud}
            intent="neutral"
            onClick={() => setShowModalImportacao(true)}
            size="lg"
            tone="soft"
          >
            Importar Excel
          </BotaoInteracao>
          <BotaoInteracao
            icon={Plus}
            intent="create"
            onClick={() => openModal(null, tipoFiltro)}
            size="lg"
          >
            Novo {labelNovo}
          </BotaoInteracao>
        </div>
      </div>
    </Panel>
  );
};

export default ClientesNovoActionsBar;
