import { FiSearch } from "react-icons/fi";
import ActionButton from "../../../components/ui/ActionButton";
import Panel from "../../../components/ui/Panel";

const campoClasses =
  "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

export default function GrupoAnaliseFiltros({
  busca,
  carregando,
  empresaId,
  empresas,
  onBuscaChange,
  onEmpresaChange,
  onSubmit,
  placeholder,
}) {
  return (
    <Panel padding="sm">
      <form className="flex flex-col gap-3 md:flex-row" onSubmit={onSubmit}>
        <label className="min-w-0 flex-1">
          <span className="sr-only">Pesquisar</span>
          <input
            value={busca}
            onChange={(event) => onBuscaChange(event.target.value)}
            placeholder={placeholder}
            className={`w-full ${campoClasses}`}
          />
        </label>
        {onEmpresaChange ? (
          <label>
            <span className="sr-only">Empresa</span>
            <select
              value={empresaId}
              onChange={(event) => onEmpresaChange(event.target.value)}
              className={campoClasses}
            >
              <option value="">Todas as empresas</option>
              {empresas.map((empresa) => (
                <option key={empresa.empresa_id} value={empresa.empresa_id}>
                  {empresa.empresa_nome}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <ActionButton type="submit" icon={FiSearch} intent="info" loading={carregando}>
          Pesquisar
        </ActionButton>
      </form>
    </Panel>
  );
}

export { campoClasses };
