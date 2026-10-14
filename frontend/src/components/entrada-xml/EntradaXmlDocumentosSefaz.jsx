import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import Panel from "../ui/Panel";

const ITENS_POR_PAGINA = 20;
const TIPOS_NFE = "resNFe,procNFe";

const STATUS_DOCUMENTO = {
  aguardando_xml: "Aguardando XML",
  pendente_importacao: "XML em processamento",
  importada: "Importada",
  duplicada: "Já importada",
  saida_descartada: "Nota própria (saída)",
  nao_destinada: "Não destinada a este CNPJ",
  erro_processamento: "Erro de importação",
};

function formatarDataEmissao(valor) {
  if (!valor) return "-";
  const data = String(valor).slice(0, 10);
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(data);
  return partes ? `${partes[3]}/${partes[2]}/${partes[1]}` : data;
}

export default function EntradaXmlDocumentosSefaz({ api, abrirDetalhes, formatMoneyBRL }) {
  const [documentos, setDocumentos] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [status, setStatus] = useState("");
  const [revisao, setRevisao] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let ativa = true;

    async function carregarDocumentos() {
      setCarregando(true);
      setErro("");
      try {
        const { data } = await api.get("/sefaz/documentos", {
          params: {
            page: pagina,
            page_size: ITENS_POR_PAGINA,
            tipos: TIPOS_NFE,
            ...(status ? { status } : {}),
          },
        });
        if (!ativa) return;
        setDocumentos(Array.isArray(data.items) ? data.items : []);
        setTotal(Number(data.total || 0));
      } catch (error) {
        if (!ativa) return;
        const detalhe = error?.response?.data?.detail;
        setErro(
          typeof detalhe === "string" && detalhe.trim()
            ? detalhe
            : "Não foi possível carregar as NF-e capturadas.",
        );
      } finally {
        if (ativa) setCarregando(false);
      }
    }

    carregarDocumentos();
    return () => {
      ativa = false;
    };
  }, [api, pagina, revisao, status]);

  const totalPaginas = Math.max(1, Math.ceil(total / ITENS_POR_PAGINA));

  return (
    <Panel
      className="mb-6"
      padding="lg"
      title="NF-e capturadas pela SEFAZ"
      subtitle="Resumos e XML recebidos para este CNPJ. Esta lista é separada das notas de entrada abaixo."
      actions={
        <button
          type="button"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          disabled={carregando}
          onClick={() => setRevisao((valor) => valor + 1)}
        >
          Atualizar lista
        </button>
      }
    >
      <p className="mb-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
        Um resumo ainda não contém o XML completo nem os itens e não gera entrada no estoque. O XML
        integral depende da manifestação fiscal ou do arquivo enviado pelo fornecedor. Esta tela não
        envia manifestação automaticamente.
      </p>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 text-sm">
        <label className="flex items-center gap-2 text-slate-700">
          Status
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPagina(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          >
            <option value="">Todos</option>
            <option value="aguardando_xml">Aguardando XML</option>
            <option value="pendente_importacao">XML em processamento</option>
            <option value="importada">Importadas</option>
            <option value="duplicada">Já importadas</option>
            <option value="saida_descartada">Notas próprias</option>
            <option value="nao_destinada">Não destinadas</option>
            <option value="erro_processamento">Erro de importação</option>
          </select>
        </label>
        <span className="text-slate-500">{total} documento(s) nesta consulta</span>
      </div>

      {erro && (
        <div
          role="alert"
          className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {erro}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-600">
            <tr>
              <th className="px-3 py-2">NF-e / chave</th>
              <th className="px-3 py-2">Emitente</th>
              <th className="px-3 py-2">Emissão</th>
              <th className="px-3 py-2 text-right">Valor</th>
              <th className="px-3 py-2">Situação</th>
              <th className="px-3 py-2">Ação</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {documentos.map((documento) => (
              <tr key={documento.id}>
                <td className="max-w-[270px] px-3 py-3 align-top">
                  <strong className="block text-slate-800">
                    {documento.numero_nota ? `NF ${documento.numero_nota}` : "NF-e"}
                  </strong>
                  <span className="break-all font-mono text-xs text-slate-500">
                    {documento.chave_acesso || "Chave não informada"}
                  </span>
                </td>
                <td className="px-3 py-3 align-top">
                  <span className="block text-slate-800">
                    {documento.emitente_nome || "Não informado"}
                  </span>
                  <span className="text-xs text-slate-500">{documento.emitente_cnpj || ""}</span>
                </td>
                <td className="px-3 py-3 align-top">
                  {formatarDataEmissao(documento.data_emissao)}
                </td>
                <td className="px-3 py-3 text-right align-top">
                  {documento.valor_total == null
                    ? "-"
                    : formatMoneyBRL(Number(documento.valor_total))}
                </td>
                <td className="px-3 py-3 align-top">
                  <span className="inline-flex rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                    {STATUS_DOCUMENTO[documento.status] || documento.status || "Sem status"}
                  </span>
                </td>
                <td className="px-3 py-3 align-top">
                  {documento.nota_entrada_id ? (
                    <button
                      type="button"
                      className="font-medium text-indigo-700 underline"
                      onClick={() => abrirDetalhes(documento.nota_entrada_id)}
                    >
                      Ver entrada
                    </button>
                  ) : (
                    <span className="text-slate-400">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!carregando && !erro && documentos.length === 0 && (
        <p className="py-6 text-center text-sm text-slate-500">
          Nenhuma NF-e nesta listagem. Isso não confirma a ausência de notas na SEFAZ; confira o
          status da sincronização.
        </p>
      )}
      {carregando && (
        <p className="py-4 text-center text-sm text-slate-500">Carregando documentos...</p>
      )}

      {totalPaginas > 1 && (
        <div className="mt-3 flex items-center justify-end gap-3 text-sm text-slate-600">
          <button
            type="button"
            disabled={pagina === 1 || carregando}
            onClick={() => setPagina((valor) => valor - 1)}
            className="font-medium text-indigo-700 disabled:text-slate-400"
          >
            Anterior
          </button>
          <span>
            Página {pagina} de {totalPaginas}
          </span>
          <button
            type="button"
            disabled={pagina >= totalPaginas || carregando}
            onClick={() => setPagina((valor) => valor + 1)}
            className="font-medium text-indigo-700 disabled:text-slate-400"
          >
            Próxima
          </button>
        </div>
      )}
    </Panel>
  );
}

EntradaXmlDocumentosSefaz.propTypes = {
  api: PropTypes.shape({ get: PropTypes.func.isRequired }).isRequired,
  abrirDetalhes: PropTypes.func.isRequired,
  formatMoneyBRL: PropTypes.func.isRequired,
};
