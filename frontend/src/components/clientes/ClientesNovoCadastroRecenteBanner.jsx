import { FiCheck, FiCopy, FiFilter, FiX } from "react-icons/fi";

const ClientesNovoCadastroRecenteBanner = ({
  cliente,
  campoCopiado,
  onCopiarCampo,
  onLimparFiltro,
}) => {
  if (!cliente) return null;

  const telefonePrincipal = cliente.celular || cliente.telefone || "";
  const codigoExibicao = cliente.codigo || cliente.id || "";

  return (
    <div className="mb-6 rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 via-white to-emerald-50 p-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-3">
          <span className="inline-flex w-fit items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700 shadow-sm">
            <FiFilter size={14} />
            Cadastro filtrado automaticamente
          </span>

          <div>
            <p className="text-base font-semibold text-emerald-950">
              Cliente pronto para uso imediato
            </p>
            <p className="text-sm text-emerald-900">
              {cliente.nome || "Cliente sem nome"}{" "}
              {codigoExibicao ? `- codigo ${codigoExibicao}` : ""}
            </p>
          </div>

          <div className="flex flex-wrap gap-2 text-xs text-emerald-900">
            {codigoExibicao && (
              <span className="rounded-full border border-emerald-200 bg-white px-3 py-1 font-medium">
                Codigo: {codigoExibicao}
              </span>
            )}
            {telefonePrincipal && (
              <span className="rounded-full border border-emerald-200 bg-white px-3 py-1 font-medium">
                Telefone: {telefonePrincipal}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onCopiarCampo(codigoExibicao, "codigo")}
            disabled={!codigoExibicao}
            className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-white px-4 py-2 text-sm font-medium text-emerald-800 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {campoCopiado === "codigo" ? <FiCheck size={16} /> : <FiCopy size={16} />}
            Copiar codigo
          </button>

          <button
            type="button"
            onClick={() => onCopiarCampo(cliente.nome, "nome")}
            disabled={!cliente.nome}
            className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-white px-4 py-2 text-sm font-medium text-emerald-800 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {campoCopiado === "nome" ? <FiCheck size={16} /> : <FiCopy size={16} />}
            Copiar nome
          </button>

          <button
            type="button"
            onClick={onLimparFiltro}
            className="inline-flex items-center gap-2 rounded-lg border border-transparent bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
          >
            <FiX size={16} />
            Limpar filtro
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClientesNovoCadastroRecenteBanner;
