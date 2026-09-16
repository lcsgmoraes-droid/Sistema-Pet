import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, ArrowUp, FileSpreadsheet, FileText, RefreshCw, Search, X } from "lucide-react";
import toast from "react-hot-toast";
import { buscarPessoasParaRelatorio } from "../../api/clientes";
import { useEscapeToClose } from "../../utils/modalEscape";
import ActionButton from "../ui/ActionButton";
import {
  COLUNAS_PADRAO_RELATORIO_PESSOAS,
  COLUNAS_RELATORIO_PESSOAS,
  ORDENACOES_RELATORIO_PESSOAS,
  PRESETS_RELATORIO_PESSOAS,
  TIPOS_RELATORIO_PESSOAS,
  exportarPessoasExcel,
  exportarPessoasPdf,
  obterColunasRelatorio,
  ordenarPessoasRelatorio,
} from "./pessoasRelatorioUtils";

const campoClasse =
  "mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100";

export default function PessoasRelatorioModal({
  isOpen,
  onClose,
  tipoInicial = "todos",
  buscaInicial = "",
}) {
  const [tipo, setTipo] = useState(tipoInicial);
  const [busca, setBusca] = useState(buscaInicial);
  const [ordenacao, setOrdenacao] = useState("nome_asc");
  const [colunas, setColunas] = useState(COLUNAS_PADRAO_RELATORIO_PESSOAS);
  const [pessoas, setPessoas] = useState([]);
  const [empresa, setEmpresa] = useState({});
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");
  const [atualizacao, setAtualizacao] = useState(0);
  const [exportando, setExportando] = useState("");
  const requisicaoAtual = useRef(0);

  useEscapeToClose({ isOpen, onClose, disabled: Boolean(exportando) });

  useEffect(() => {
    if (!isOpen) return undefined;

    const requisicao = ++requisicaoAtual.current;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setErro("");
      try {
        const resultado = await buscarPessoasParaRelatorio({
          tipo_cadastro: tipo === "todos" ? undefined : tipo,
          search: busca.trim() || undefined,
        });
        if (requisicao === requisicaoAtual.current) {
          setPessoas(resultado.pessoas);
          setEmpresa(resultado.empresa);
        }
      } catch (error) {
        if (requisicao !== requisicaoAtual.current) return;
        console.error("Erro ao carregar relatorio de pessoas:", error);
        setPessoas([]);
        setErro(error?.response?.data?.detail || "Nao foi possivel carregar os cadastros.");
      } finally {
        if (requisicao === requisicaoAtual.current) setLoading(false);
      }
    }, 300);

    return () => {
      window.clearTimeout(timer);
      requisicaoAtual.current += 1;
    };
  }, [atualizacao, busca, isOpen, tipo]);

  const pessoasOrdenadas = useMemo(
    () => ordenarPessoasRelatorio(pessoas, ordenacao),
    [ordenacao, pessoas],
  );
  const colunasAtivas = useMemo(() => obterColunasRelatorio(colunas), [colunas]);
  const colunasNaTela = useMemo(() => {
    const selecionadas = obterColunasRelatorio(colunas);
    const chavesSelecionadas = new Set(colunas);
    return [
      ...selecionadas,
      ...COLUNAS_RELATORIO_PESSOAS.filter((coluna) => !chavesSelecionadas.has(coluna.key)),
    ];
  }, [colunas]);

  if (!isOpen) return null;

  const alternarColuna = (chave) => {
    setColunas((anteriores) =>
      anteriores.includes(chave)
        ? anteriores.filter((coluna) => coluna !== chave)
        : [...anteriores, chave],
    );
  };

  const moverColuna = (chave, direcao) => {
    setColunas((anteriores) => {
      const indice = anteriores.indexOf(chave);
      const destino = indice + direcao;
      if (indice < 0 || destino < 0 || destino >= anteriores.length) return anteriores;
      const proximas = [...anteriores];
      [proximas[indice], proximas[destino]] = [proximas[destino], proximas[indice]];
      return proximas;
    });
  };

  const exportar = async (formato) => {
    if (colunas.length === 0) {
      toast.error("Selecione pelo menos uma coluna para o relatorio.");
      return;
    }
    if (pessoasOrdenadas.length === 0) {
      toast.error("Nao ha cadastros para exportar com estes filtros.");
      return;
    }

    setExportando(formato);
    try {
      const opcoes = { pessoas: pessoasOrdenadas, colunas, tipo, busca: busca.trim(), empresa };
      if (formato === "excel") await exportarPessoasExcel(opcoes);
      else await exportarPessoasPdf(opcoes);
      toast.success(`Relatorio em ${formato === "excel" ? "Excel" : "PDF"} gerado.`);
    } catch (error) {
      console.error(`Erro ao gerar relatorio em ${formato}:`, error);
      toast.error("Nao foi possivel gerar o arquivo. Tente novamente.");
    } finally {
      setExportando("");
    }
  };

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/50 p-3 md:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !exportando) onClose();
      }}
    >
      <div
        aria-labelledby="titulo-relatorio-pessoas"
        aria-modal="true"
        className="flex max-h-[94vh] w-full max-w-7xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        role="dialog"
      >
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4 md:px-6">
          <div>
            <h2 id="titulo-relatorio-pessoas" className="text-xl font-bold text-slate-900">
              Relatorio personalizado de pessoas
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Escolha quem entra, a ordem das linhas e as colunas do arquivo.
            </p>
          </div>
          <button
            aria-label="Fechar relatorio"
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            disabled={Boolean(exportando)}
            onClick={onClose}
            type="button"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 overflow-y-auto lg:grid-cols-[360px_minmax(0,1fr)] lg:overflow-hidden">
          <aside className="space-y-5 border-b border-slate-200 p-5 lg:overflow-y-auto lg:border-b-0 lg:border-r">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              <label className="text-sm font-medium text-slate-700">
                Quem deve aparecer
                <select
                  className={campoClasse}
                  value={tipo}
                  onChange={(e) => setTipo(e.target.value)}
                >
                  {TIPOS_RELATORIO_PESSOAS.map((opcao) => (
                    <option key={opcao.value} value={opcao.value}>
                      {opcao.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700">
                Ordem das linhas
                <select
                  className={campoClasse}
                  value={ordenacao}
                  onChange={(e) => setOrdenacao(e.target.value)}
                >
                  {ORDENACOES_RELATORIO_PESSOAS.map((opcao) => (
                    <option key={opcao.value} value={opcao.value}>
                      {opcao.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="block text-sm font-medium text-slate-700">
              Buscar dentro dos cadastros
              <div className="relative mt-1">
                <Search
                  className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                  aria-hidden="true"
                />
                <input
                  className={`${campoClasse} mt-0 pl-9`}
                  placeholder="Nome, documento ou telefone..."
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                />
              </div>
            </label>

            <section>
              <div className="mb-2 flex items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">Colunas e ordem</h3>
                  <p className="text-xs text-slate-500">As colunas marcadas saem nesta ordem.</p>
                </div>
                <button
                  className="text-xs font-medium text-slate-500 hover:text-slate-800"
                  onClick={() => setColunas([])}
                  type="button"
                >
                  Limpar
                </button>
              </div>

              <div className="mb-3 flex flex-wrap gap-2">
                <button
                  className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                  onClick={() => setColunas(PRESETS_RELATORIO_PESSOAS.basico)}
                  type="button"
                >
                  Nome + telefone
                </button>
                <button
                  className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
                  onClick={() => setColunas(PRESETS_RELATORIO_PESSOAS.endereco)}
                  type="button"
                >
                  Contato + endereco
                </button>
              </div>

              <div className="max-h-80 space-y-1 overflow-y-auto rounded-xl border border-slate-200 p-2">
                {colunasNaTela.map((coluna) => {
                  const indice = colunas.indexOf(coluna.key);
                  const selecionada = indice >= 0;
                  return (
                    <div
                      className={`flex items-center gap-2 rounded-lg px-2 py-2 ${
                        selecionada ? "bg-emerald-50" : "hover:bg-slate-50"
                      }`}
                      key={coluna.key}
                    >
                      <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2">
                        <input
                          checked={selecionada}
                          className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                          onChange={() => alternarColuna(coluna.key)}
                          type="checkbox"
                        />
                        <span className="truncate text-sm text-slate-700">{coluna.label}</span>
                      </label>
                      {selecionada ? (
                        <div className="flex items-center gap-1">
                          <span className="w-5 text-center text-xs font-semibold text-emerald-700">
                            {indice + 1}
                          </span>
                          <button
                            aria-label={`Mover ${coluna.label} para cima`}
                            className="rounded p-1 text-slate-500 hover:bg-white hover:text-slate-900 disabled:opacity-30"
                            disabled={indice === 0}
                            onClick={() => moverColuna(coluna.key, -1)}
                            type="button"
                          >
                            <ArrowUp className="h-3.5 w-3.5" />
                          </button>
                          <button
                            aria-label={`Mover ${coluna.label} para baixo`}
                            className="rounded p-1 text-slate-500 hover:bg-white hover:text-slate-900 disabled:opacity-30"
                            disabled={indice === colunas.length - 1}
                            onClick={() => moverColuna(coluna.key, 1)}
                            type="button"
                          >
                            <ArrowDown className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </section>
          </aside>

          <main className="min-w-0 space-y-4 p-5 lg:overflow-y-auto md:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold text-slate-900">Previa do relatorio</h3>
                <p className="text-sm text-slate-500">
                  {loading
                    ? "Buscando cadastros..."
                    : `${pessoasOrdenadas.length.toLocaleString("pt-BR")} cadastro(s) encontrado(s)`}
                </p>
              </div>
              <ActionButton
                icon={RefreshCw}
                loading={loading}
                onClick={() => setAtualizacao((valor) => valor + 1)}
                tone="soft"
              >
                Atualizar previa
              </ActionButton>
            </div>

            {erro ? (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                {erro}
              </div>
            ) : colunasAtivas.length === 0 ? (
              <div className="rounded-xl border border-dashed border-amber-300 bg-amber-50 p-8 text-center text-sm text-amber-800">
                Marque pelo menos uma coluna para montar o relatorio.
              </div>
            ) : !loading && pessoasOrdenadas.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
                Nenhum cadastro encontrado com estes filtros.
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl border border-slate-200">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                    <thead className="bg-emerald-50 text-xs uppercase tracking-wide text-emerald-800">
                      <tr>
                        {colunasAtivas.map((coluna) => (
                          <th
                            className="whitespace-nowrap px-3 py-3 font-semibold"
                            key={coluna.key}
                          >
                            {coluna.label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
                      {pessoasOrdenadas.slice(0, 10).map((pessoa) => (
                        <tr key={pessoa.id}>
                          {colunasAtivas.map((coluna) => (
                            <td className="max-w-72 whitespace-nowrap px-3 py-2.5" key={coluna.key}>
                              <span
                                className="block max-w-72 truncate"
                                title={coluna.value(pessoa) || "-"}
                              >
                                {coluna.value(pessoa) || "-"}
                              </span>
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {pessoasOrdenadas.length > 10 ? (
                  <p className="border-t border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                    Mostrando 10 linhas na previa. O arquivo tera os{" "}
                    {pessoasOrdenadas.length.toLocaleString("pt-BR")} cadastros.
                  </p>
                ) : null}
              </div>
            )}
          </main>
        </div>

        <footer className="flex flex-col-reverse gap-3 border-t border-slate-200 bg-slate-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between md:px-6">
          <p className="text-xs text-slate-500">Somente cadastros ativos entram no relatorio.</p>
          <div className="flex flex-wrap justify-end gap-2">
            <ActionButton disabled={Boolean(exportando)} onClick={onClose} tone="soft">
              Fechar
            </ActionButton>
            <ActionButton
              disabled={
                loading || Boolean(erro) || pessoasOrdenadas.length === 0 || colunas.length === 0
              }
              icon={FileSpreadsheet}
              intent="create"
              loading={exportando === "excel"}
              onClick={() => exportar("excel")}
              size="md"
            >
              Baixar Excel
            </ActionButton>
            <ActionButton
              disabled={
                loading || Boolean(erro) || pessoasOrdenadas.length === 0 || colunas.length === 0
              }
              icon={FileText}
              intent="pdf"
              loading={exportando === "pdf"}
              onClick={() => exportar("pdf")}
              size="md"
            >
              Baixar PDF
            </ActionButton>
          </div>
        </footer>
      </div>
    </div>
  );
}
