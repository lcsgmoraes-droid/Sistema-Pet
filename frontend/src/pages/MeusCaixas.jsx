import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  DollarSign,
  Calendar,
  Clock,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Download,
  Printer,
  Users,
} from "lucide-react";
import { listarCaixas, obterCaixaAberto, obterResumoCaixa } from "../api/caixa";
import ImpressaoResumoCaixa from "../components/caixa/ImpressaoResumoCaixa";
import ImpressaoTermicaCaixa from "../components/caixa/ImpressaoTermicaCaixa";
import ModalMovimentacoesCaixa from "../components/ModalMovimentacoesCaixa";
import ModalAuditoriaCaixa from "../components/caixa/ModalAuditoriaCaixa";
import ModalReabrirCaixa from "../components/caixa/ModalReabrirCaixa";
import { getAccessToken } from "../auth/tokenStorage";
import { useAuth } from "../contexts/AuthContext";
import { formatMoneyBRL } from "../utils/formatters";

export default function MeusCaixas() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [caixas, setCaixas] = useState([]);
  const [caixaAberto, setCaixaAberto] = useState(null);
  const [caixaRevisao, setCaixaRevisao] = useState(null);
  const [dataOcorrencia, setDataOcorrencia] = useState("");
  const [motivoRevisao, setMotivoRevisao] = useState("");
  const [loading, setLoading] = useState(true);
  const [resumoImpressao, setResumoImpressao] = useState(null);
  const [resumoTermico, setResumoTermico] = useState(null);
  const [caixaExtrato, setCaixaExtrato] = useState(null);
  const [caixaAuditoria, setCaixaAuditoria] = useState(null);
  const [caixaReabertura, setCaixaReabertura] = useState(null);
  const [filtros, setFiltros] = useState({
    data_inicio: "",
    data_fim: "",
    status: "",
  });

  useEffect(() => {
    carregarCaixas();
  }, [filtros]);

  const carregarCaixas = async () => {
    try {
      setLoading(true);
      const params = {};

      if (filtros.data_inicio) params.data_inicio = filtros.data_inicio;
      if (filtros.data_fim) params.data_fim = filtros.data_fim;
      if (filtros.status) params.status_filter = filtros.status;

      const response = await listarCaixas(params);
      const aberto = await obterCaixaAberto().catch(() => ({ desconhecido: true }));
      setCaixas(response);
      setCaixaAberto(aberto);
    } catch (error) {
      console.error("Erro ao carregar caixas:", error);
      alert("Erro ao carregar histórico de caixas");
    } finally {
      setLoading(false);
    }
  };

  const iniciarRevisao = (event) => {
    event.preventDefault();
    if (!caixaRevisao || motivoRevisao.trim().length < 10) return;
    const params = new URLSearchParams({
      caixa_revisao_id: String(caixaRevisao.id),
      data_ocorrencia: dataOcorrencia,
      motivo_revisao: motivoRevisao.trim(),
    });
    navigate(`/pdv?${params.toString()}`);
  };

  const handleDownloadPDF = async (caixaId, numeroCaixa) => {
    try {
      const apiBaseUrl = import.meta.env.VITE_API_URL || "/api";
      const token = getAccessToken();
      const response = await fetch(`${apiBaseUrl}/caixas/${caixaId}/pdf`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Erro ao gerar PDF");
      }

      // Converter resposta em blob
      const blob = await response.blob();

      // Criar URL temporária e fazer download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Caixa_${numeroCaixa}_${new Date().toISOString().split("T")[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      alert("PDF baixado com sucesso!");
    } catch (error) {
      console.error("Erro ao baixar PDF:", error);
      alert("Erro ao gerar PDF do caixa");
    }
  };

  const handleImprimirResumo = async (caixaId) => {
    try {
      setResumoImpressao(await obterResumoCaixa(caixaId));
    } catch (error) {
      console.error("Erro ao carregar resumo para impressão:", error);
      alert("Erro ao carregar o relatório do caixa");
    }
  };

  const handleImprimirTermico = async (caixaId) => {
    try {
      setResumoTermico(await obterResumoCaixa(caixaId));
    } catch (error) {
      console.error("Erro ao carregar relatório térmico:", error);
      alert("Erro ao carregar o relatório do caixa");
    }
  };

  const getStatusBadge = (caixa) => {
    if (caixa.status === "aberto") {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
          <CheckCircle className="w-4 h-4" />
          Aberto
        </span>
      );
    }
    // Fechado — verificar se tem diferença
    const temDiferenca =
      caixa.diferenca !== null && caixa.diferenca !== undefined && Math.abs(caixa.diferenca) > 0.01;
    if (temDiferenca) {
      const dif = caixa.diferenca;
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800">
          <AlertTriangle className="w-4 h-4" />
          Diferença {dif > 0 ? "+" : "-"}
          {formatMoneyBRL(Math.abs(dif))}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
        <CheckCircle className="w-4 h-4 text-green-600" />
        Fechado OK
      </span>
    );
  };

  const calcularDiferenca = (esperado, informado) => {
    const dif = informado - esperado;
    return {
      valor: Math.abs(dif),
      tipo: dif > 0 ? "sobra" : dif < 0 ? "falta" : "ok",
    };
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Caixas</h1>
        <p className="text-gray-600 mt-1">Histórico e gestão dos caixas disponíveis</p>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Data Início</label>
            <input
              type="date"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({ ...filtros, data_inicio: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Data Fim</label>
            <input
              type="date"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({ ...filtros, data_fim: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <select
              value={filtros.status}
              onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="aberto">Aberto</option>
              <option value="fechado">Fechado</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFiltros({ data_inicio: "", data_fim: "", status: "" })}
              className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            >
              Limpar Filtros
            </button>
          </div>
        </div>
      </div>

      {/* Lista de Caixas */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando caixas...</p>
        </div>
      ) : caixas.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow-sm">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">Nenhum caixa encontrado</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {caixas.map((caixa) => {
            const diferenca =
              caixa.status === "fechado" && caixa.valor_esperado
                ? calcularDiferenca(caixa.valor_esperado, caixa.valor_informado)
                : null;

            return (
              <div
                key={caixa.id}
                className={`bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow ${
                  caixa.status === "fechado" &&
                  caixa.diferenca !== null &&
                  Math.abs(caixa.diferenca ?? 0) > 0.01
                    ? "border-l-4 border-l-amber-400"
                    : caixa.status === "fechado" &&
                        caixa.diferenca !== null &&
                        Math.abs(caixa.diferenca ?? 0) <= 0.01
                      ? "border-l-4 border-l-green-400"
                      : ""
                }`}
              >
                <div className="p-6">
                  {/* Header do Card */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 bg-blue-100 rounded-lg flex items-center justify-center">
                        <DollarSign className="w-8 h-8 text-blue-600" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">
                          Caixa #{caixa.numero_caixa}
                        </h3>
                        <p className="text-sm text-gray-600">Aberto por {caixa.usuario_nome}</p>
                        {caixa.usuario_fechamento_nome && (
                          <p className="text-sm text-gray-600">
                            Fechado por {caixa.usuario_fechamento_nome}
                          </p>
                        )}
                        {caixa.compartilhado && (
                          <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                            <Users className="h-3 w-3" /> Caixa compartilhado
                          </span>
                        )}
                      </div>
                    </div>
                    {getStatusBadge(caixa)}
                  </div>

                  {/* Datas */}
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar className="w-4 h-4" />
                      <span>Abertura: {new Date(caixa.data_abertura).toLocaleString("pt-BR")}</span>
                    </div>
                    {caixa.data_fechamento && (
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Clock className="w-4 h-4" />
                        <span>
                          Fechamento: {new Date(caixa.data_fechamento).toLocaleString("pt-BR")}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Valores */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs text-gray-600 mb-1">Abertura</div>
                      <div className="text-lg font-semibold text-gray-900">
                        {formatMoneyBRL(caixa.valor_abertura)}
                      </div>
                    </div>

                    {caixa.status === "fechado" && caixa.valor_esperado && (
                      <>
                        <div className="bg-blue-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 mb-1">Esperado</div>
                          <div className="text-lg font-semibold text-blue-900">
                            {formatMoneyBRL(caixa.valor_esperado)}
                          </div>
                        </div>

                        <div className="bg-green-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 mb-1">Informado</div>
                          <div className="text-lg font-semibold text-green-900">
                            {formatMoneyBRL(caixa.valor_informado)}
                          </div>
                        </div>

                        <div
                          className={`rounded-lg p-3 ${
                            diferenca.tipo === "ok"
                              ? "bg-green-50"
                              : diferenca.tipo === "sobra"
                                ? "bg-blue-50"
                                : "bg-red-50"
                          }`}
                        >
                          <div className="text-xs text-gray-600 mb-1">Diferença</div>
                          <div
                            className={`text-lg font-semibold ${
                              diferenca.tipo === "ok"
                                ? "text-green-700"
                                : diferenca.tipo === "sobra"
                                  ? "text-blue-900"
                                  : "text-red-900"
                            }`}
                          >
                            {diferenca.tipo === "ok" && "✓ Caixa Batido"}
                            {diferenca.tipo === "sobra" && `+ ${formatMoneyBRL(diferenca.valor)}`}
                            {diferenca.tipo === "falta" && `- ${formatMoneyBRL(diferenca.valor)}`}
                          </div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Observações */}
                  {(caixa.observacoes_abertura || caixa.observacoes_fechamento) && (
                    <div className="border-t pt-4 mb-4">
                      {caixa.observacoes_abertura && (
                        <p className="text-sm text-gray-600 mb-2">
                          <span className="font-medium">Obs. Abertura:</span>{" "}
                          {caixa.observacoes_abertura}
                        </p>
                      )}
                      {caixa.observacoes_fechamento && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Obs. Fechamento:</span>{" "}
                          {caixa.observacoes_fechamento}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Ações */}
                  <button
                    type="button"
                    onClick={() => setCaixaAuditoria(caixa.id)}
                    className="mb-4 rounded-lg bg-blue-50 px-4 py-2 font-medium text-blue-700"
                  >
                    Auditar vendas e lançamentos
                  </button>
                  {caixa.status === "fechado" && (
                    <div className="border-t pt-4 flex flex-wrap gap-3">
                      <button
                        onClick={() => setCaixaReabertura(caixa)}
                        disabled={Boolean(caixaAberto)}
                        title={
                          caixaAberto
                            ? "Feche o caixa atual antes de reabrir este caixa."
                            : undefined
                        }
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <RefreshCw className="w-4 h-4" />
                        Reabrir Caixa
                      </button>
                      {user?.is_admin && (
                        <button
                          onClick={() => {
                            setCaixaRevisao(caixa);
                            setDataOcorrencia("");
                            setMotivoRevisao("");
                          }}
                          className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition-colors"
                        >
                          <RefreshCw className="w-4 h-4" />
                          Revisar lançamentos
                        </button>
                      )}
                      <button
                        onClick={() => handleDownloadPDF(caixa.id, caixa.numero_caixa)}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        Baixar PDF
                      </button>
                      <button
                        onClick={() => handleImprimirTermico(caixa.id)}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-900 text-white rounded-lg transition-colors"
                      >
                        <Printer className="w-4 h-4" /> Imprimir na térmica
                      </button>
                      <button
                        onClick={() => handleImprimirResumo(caixa.id)}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-900 text-white rounded-lg transition-colors"
                        title="Imprimir o resumo do caixa na térmica ou salvar em PDF"
                      >
                        <Printer className="w-4 h-4" /> Imprimir resumo
                      </button>
                      <button
                        onClick={() => setCaixaExtrato(caixa.id)}
                        className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700"
                      >
                        Movimentações e comprovantes
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {caixaRevisao && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <form
            onSubmit={iniciarRevisao}
            className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
          >
            <h2 className="text-xl font-semibold">Revisar caixa #{caixaRevisao.numero_caixa}</h2>
            <p className="mt-2 text-sm text-gray-600">
              Informe quando a venda ou o pagamento aconteceu. O caixa atual continua aberto. A
              correção ficará registrada com seu nome e justificativa.
            </p>
            <label className="mt-5 block text-sm font-medium" htmlFor="data-revisao">
              Data e hora da ocorrência
            </label>
            <input
              id="data-revisao"
              type="datetime-local"
              required
              value={dataOcorrencia}
              min={caixaRevisao.data_abertura.slice(0, 16)}
              max={caixaRevisao.data_fechamento.slice(0, 16)}
              onChange={(event) => setDataOcorrencia(event.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            />
            <label className="mt-4 block text-sm font-medium" htmlFor="motivo-revisao">
              Motivo da correção
            </label>
            <textarea
              id="motivo-revisao"
              required
              minLength={10}
              value={motivoRevisao}
              onChange={(event) => setMotivoRevisao(event.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              placeholder="Ex.: pagamento recebido ontem, mas não lançado"
            />
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setCaixaRevisao(null)}
                className="rounded px-4 py-2 text-gray-700"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="rounded bg-amber-600 px-4 py-2 font-medium text-white"
              >
                Ir ao PDV em revisão
              </button>
            </div>
          </form>
        </div>
      )}
      {resumoImpressao && (
        <ImpressaoResumoCaixa
          resumo={resumoImpressao}
          onAfterPrint={() => setResumoImpressao(null)}
        />
      )}
      <ImpressaoTermicaCaixa
        documento={resumoTermico ? { resumo: resumoTermico } : null}
        onAfterPrint={() => setResumoTermico(null)}
      />
      {caixaExtrato && (
        <ModalMovimentacoesCaixa caixaId={caixaExtrato} onClose={() => setCaixaExtrato(null)} />
      )}
      {caixaAuditoria && (
        <ModalAuditoriaCaixa caixaId={caixaAuditoria} onClose={() => setCaixaAuditoria(null)} />
      )}
      {caixaReabertura && (
        <ModalReabrirCaixa
          caixa={caixaReabertura}
          onClose={() => setCaixaReabertura(null)}
          onSuccess={() => navigate("/pdv")}
        />
      )}
    </div>
  );
}
