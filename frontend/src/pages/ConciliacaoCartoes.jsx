import React, { useState, useEffect } from "react";
import {
  Upload,
  CheckCircle,
  AlertTriangle,
  XCircle,
  FileText,
  RefreshCw,
  Info,
  CreditCard,
} from "lucide-react";
import { api } from "../services/api";

/**
 * 🎯 PRINCÍPIO DE DESIGN: SIMPLICIDADE
 *
 * Usuário precisa entender em 5 segundos:
 * - ✅ Posso processar?
 * - ⚠️ Preciso confirmar?
 * - ❌ Tem risco?
 *
 * UI simples compensa complexidade do backend.
 */

export default function ConciliacaoCartoes() {
  const [validacoes, setValidacoes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [adquirentes, setAdquirentes] = useState([]);
  const [adquirenteSelecionado, setAdquirenteSelecionado] = useState(null);

  // Upload
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = React.useRef(null);

  // AJUSTE 6: Estado de processamento por validação
  const [processando, setProcessando] = useState({});

  // Carregar dados iniciais
  useEffect(() => {
    carregarAdquirentes();
    carregarValidacoes();
  }, []);

  const carregarAdquirentes = async () => {
    try {
      const res = await api.get("/conciliacao/templates");
      setAdquirentes(res.data.templates || []);
      if (res.data.templates?.length > 0) {
        setAdquirenteSelecionado(res.data.templates[0].id);
      }
    } catch (error) {
      console.error("❌ Erro ao carregar adquirentes:", error);
    }
  };

  const carregarValidacoes = async () => {
    setLoading(true);
    try {
      const res = await api.get("/conciliacao/validacoes", {
        params: {
          page: 1,
          per_page: 20,
        },
      });
      setValidacoes(res.data.items || []);
    } catch (error) {
      console.error("❌ Erro ao carregar validações:", error);
    } finally {
      setLoading(false);
    }
  };

  // Upload de arquivo
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file) => {
    if (!adquirenteSelecionado) {
      alert("Selecione um adquirente (Stone, Cielo, etc) antes de fazer upload");
      return;
    }

    setUploadingFile(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("adquirente_id", adquirenteSelecionado);

    try {
      const uploadRes = await api.post("/conciliacao/upload-operadora", formData);

      if (uploadRes.data.success) {
        // 2. Validar automaticamente
        const validarRes = await api.post("/conciliacao/validar", {
          importacao_id: uploadRes.data.importacao_id,
          data_inicio: new Date().toISOString().split("T")[0],
          data_fim: new Date().toISOString().split("T")[0],
          adquirente_id: adquirenteSelecionado,
        });

        alert(
          `✅ Arquivo importado com sucesso!\n\nParcelas confirmadas: ${uploadRes.data.parcelas_confirmadas}\nConfiança: ${validarRes.data.confianca}`,
        );
        carregarValidacoes();
      }
    } catch (error) {
      console.error("❌ Erro ao processar arquivo:", error);
      alert("Erro ao processar arquivo: " + (error.response?.data?.detail || error.message));
    } finally {
      setUploadingFile(false);
    }
  };

  const processar = async (validacao) => {
    const confirmacao = validacao.requer_confirmacao;
    const precisaJustificativa = validacao.confianca === "BAIXA";
    const quantidadeParcelas = validacao.quantidade_parcelas || validacao.parcelas_confirmadas || 0;

    let justificativa = null;
    if (precisaJustificativa) {
      justificativa = prompt("⚠️ Confiança BAIXA.\n\nJustificativa obrigatória para processar:");
      if (!justificativa || justificativa.trim() === "") {
        alert("❌ Justificativa obrigatória para divergência alta");
        return;
      }
    }

    if (confirmacao && !precisaJustificativa) {
      const confirmar = window.confirm(
        `⚠️ Deseja confirmar o processamento?\n\nConfiança: ${validacao.confianca}\nDivergência: ${validacao.percentual_divergencia}%\nParcelas a processar: ${quantidadeParcelas}`,
      );
      if (!confirmar) return;
    }

    // AJUSTE 6: Marca como processando
    setProcessando((prev) => ({ ...prev, [validacao.id]: true }));

    try {
      const res = await api.post(`/conciliacao/processar/${validacao.id}`, {
        confirmacao_usuario: confirmacao,
        justificativa: justificativa,
      });

      if (res.data.success) {
        alert(
          `✅ Processado com sucesso!\n\nParcelas: ${res.data.parcelas_processadas}\nValor: R$ ${res.data.valor_total_processado}`,
        );
        carregarValidacoes();
      }
    } catch (error) {
      alert("Erro: " + (error.response?.data?.detail || error.message));
    } finally {
      // AJUSTE 6: Remove estado de processando
      setProcessando((prev) => ({ ...prev, [validacao.id]: false }));
    }
  };

  const reverter = async (validacao) => {
    const motivo = prompt("⚠️ REVERSÃO\n\nMotivo obrigatório:");
    if (!motivo || motivo.trim() === "") {
      alert("❌ Motivo obrigatório para reversão");
      return;
    }

    try {
      const res = await api.post(`/conciliacao/reverter/${validacao.id}`, {
        motivo: motivo,
      });

      if (res.data.success) {
        alert(
          `✅ Revertido com sucesso!\n\nParcelas revertidas: ${res.data.total_parcelas_revertidas}`,
        );
        carregarValidacoes();
      }
    } catch (error) {
      alert("Erro: " + (error.response?.data?.detail || error.message));
    }
  };

  // Visual de confiança (cores semáforo)
  const getConfiancaBadge = (confianca) => {
    const badges = {
      ALTA: { bg: "bg-green-100", text: "text-green-800", icon: CheckCircle, label: "✅ ALTA" },
      MEDIA: {
        bg: "bg-yellow-100",
        text: "text-yellow-800",
        icon: AlertTriangle,
        label: "⚠️ MÉDIA",
      },
      BAIXA: { bg: "bg-red-100", text: "text-red-800", icon: XCircle, label: "❌ BAIXA" },
    };
    const badge = badges[confianca] || badges["BAIXA"];
    const Icon = badge.icon;

    return (
      <div
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-lg ${badge.bg} ${badge.text}`}
      >
        <Icon className="w-6 h-6" />
        {badge.label}
      </div>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <CreditCard className="w-8 h-8" />
          Conciliação de Cartões
        </h1>
        <p className="text-gray-600 mt-2">
          Importe arquivos da operadora e valide pagamentos automaticamente
        </p>
      </div>

      {/* Upload Area */}
      <div className="mb-8 bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
          <Upload className="w-5 h-5" />
          1. Importar Arquivo da Operadora
        </h2>

        {/* Explicação de qual arquivo importar */}
        <div className="mb-4 bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
          <p className="text-sm font-medium text-blue-900 mb-1">📄 Qual arquivo importar?</p>
          <ul className="text-xs text-blue-800 space-y-1">
            <li>
              ✅ <strong>CSV/TXT que a Stone, Cielo ou Rede enviou por email</strong>
            </li>
            <li>
              ✅ <strong>Extrato de recebimentos/liquidações da operadora</strong>
            </li>
            <li>
              ❌{" "}
              <strong className="text-red-600">NÃO é o arquivo de vendas do seu PDV/sistema</strong>
            </li>
          </ul>
        </div>

        {/* Seleção de Adquirente */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Adquirente (Stone, Cielo, etc)
          </label>
          <select
            value={adquirenteSelecionado || ""}
            onChange={(e) => setAdquirenteSelecionado(parseInt(e.target.value))}
            className="w-full md:w-64 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Selecione...</option>
            {adquirentes.map((adq) => (
              <option key={adq.id} value={adq.id}>
                {adq.adquirente} v{adq.versao}
              </option>
            ))}
          </select>
        </div>

        {/* Drag & Drop Area */}
        <div
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-all ${
            dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.txt"
            onChange={handleChange}
            className="hidden"
          />

          {uploadingFile ? (
            <div className="flex flex-col items-center gap-4">
              <RefreshCw className="w-12 h-12 text-blue-500 animate-spin" />
              <p className="text-lg font-medium">Processando arquivo...</p>
            </div>
          ) : (
            <>
              <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl font-medium text-gray-700 mb-2">Arraste o arquivo CSV aqui</p>
              <p className="text-gray-500 mb-4">ou</p>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={!adquirenteSelecionado}
                className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                  adquirenteSelecionado
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-300 text-gray-500 cursor-not-allowed"
                }`}
              >
                Selecionar Arquivo
              </button>
            </>
          )}
        </div>
      </div>

      {/* Validações */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <FileText className="w-5 h-5" />
            2. Validações Pendentes
          </h2>
          <button
            onClick={carregarValidacoes}
            className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Atualizar
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mx-auto mb-4" />
            <p className="text-gray-500">Carregando validações...</p>
          </div>
        ) : validacoes.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Info className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>Nenhuma validação pendente</p>
            <p className="text-sm mt-2">Importe um arquivo para começar</p>
          </div>
        ) : (
          <div className="space-y-4">
            {validacoes.map((validacao) => (
              <ValidacaoCard
                key={validacao.id}
                validacao={validacao}
                onProcessar={processar}
                onReverter={reverter}
                getConfiancaBadge={getConfiancaBadge}
                processando={processando[validacao.id]}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Card de Validação - VISUAL SIMPLES E CLARO
function ValidacaoCard({ validacao, onProcessar, onReverter, getConfiancaBadge, processando }) {
  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(valor || 0);
  };

  const formatarData = (data) => {
    return new Date(data).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Determinar ação visual
  const podeProcessar = validacao.pode_processar && validacao.status_validacao === "aprovada";
  const jaProcessado = validacao.status_validacao === "concluida";
  const divergente = validacao.status_validacao === "divergente";

  return (
    <div
      className={`border-2 rounded-lg p-6 ${
        jaProcessado
          ? "border-green-300 bg-green-50"
          : divergente
            ? "border-red-300 bg-red-50"
            : podeProcessar
              ? "border-blue-300 bg-blue-50"
              : "border-gray-300"
      }`}
    >
      {/* Header com Status */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold text-gray-900">#{validacao.id}</span>
          {getConfiancaBadge(validacao.confianca)}
        </div>
        <div className="text-right text-sm text-gray-600">
          <p>{formatarData(validacao.data_validacao)}</p>
          <p className="font-medium">{validacao.adquirente}</p>
        </div>
      </div>

      {/* AJUSTE 1: Mostrar QUANTIDADE */}
      <div className="mb-4 bg-blue-50 border-l-4 border-blue-500 p-3 rounded">
        <p className="text-sm font-bold text-blue-900">
          📊 {validacao.quantidade_parcelas || validacao.parcelas_confirmadas || 0} parcelas
          encontradas
          {validacao.quantidade_nsus && ` • ${validacao.quantidade_nsus} NSUs`}
        </p>
      </div>

      {/* Estatísticas - GRID SIMPLES */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <p className="text-sm text-gray-600 mb-1">Total OFX/Pagamentos</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatarMoeda(validacao.total_pagamentos_ofx)}
          </p>
        </div>
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <p className="text-sm text-gray-600 mb-1">Total Recebimentos</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatarMoeda(validacao.total_recebimentos_parcelas)}
          </p>
        </div>
        <div
          className={`rounded-lg p-4 border-2 ${
            Math.abs(validacao.diferenca_absoluta) < 1
              ? "bg-green-50 border-green-300"
              : "bg-yellow-50 border-yellow-300"
          }`}
        >
          <p className="text-sm text-gray-600 mb-1">Divergência</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatarMoeda(validacao.diferenca_absoluta)}
          </p>
          <p className="text-sm font-medium mt-1">{validacao.percentual_divergencia}%</p>
          {/* AJUSTE 5: Link para ver detalhes */}
          {validacao.confianca === "BAIXA" && (
            <button
              onClick={() => alert("Modal de detalhes em desenvolvimento")}
              className="text-xs text-blue-600 hover:text-blue-800 underline mt-2"
            >
              Ver detalhes da divergência →
            </button>
          )}
        </div>
      </div>

      {/* Decisão em 5 segundos - BOTÕES GRANDES E CLAROS */}
      <div className="border-t pt-4">
        <div className="flex items-center gap-3">
          {/* STATUS VISUAL */}
          {jaProcessado && (
            <>
              <div className="flex-1 flex items-center gap-2 text-green-700 font-medium">
                <CheckCircle className="w-5 h-5" />
                Processado com sucesso
              </div>
              {/* AJUSTE 4: Reverter menos perigoso visualmente */}
              <button
                onClick={() => onReverter(validacao)}
                className="px-4 py-2 border-2 border-gray-400 text-gray-700 hover:bg-gray-100 rounded-lg font-medium text-sm"
              >
                ↩ Reverter
              </button>
            </>
          )}

          {divergente && (
            <div className="flex-1 flex items-center gap-2 text-red-700 font-medium">
              <XCircle className="w-5 h-5" />
              Divergente - Revertido
            </div>
          )}

          {podeProcessar && !jaProcessado && !divergente && (
            <>
              {/* Info rápida */}
              <div className="flex-1">
                {!validacao.requer_confirmacao && (
                  <div>
                    <p className="text-green-700 font-medium flex items-center gap-2">
                      <CheckCircle className="w-5 h-5" />✅ Pode processar automaticamente
                    </p>
                    {/* AJUSTE 3: Mensagem de reversibilidade */}
                    <p className="text-xs text-gray-600 mt-1 ml-7">
                      Esta ação poderá ser revertida posteriormente.
                    </p>
                  </div>
                )}
                {validacao.requer_confirmacao && validacao.confianca !== "BAIXA" && (
                  <div>
                    <p className="text-yellow-700 font-medium flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5" />
                      ⚠️ Precisa confirmação do usuário
                    </p>
                    {/* AJUSTE 3: Mensagem de reversibilidade */}
                    <p className="text-xs text-gray-600 mt-1 ml-7">
                      Esta ação poderá ser revertida posteriormente.
                    </p>
                  </div>
                )}
                {validacao.confianca === "BAIXA" && (
                  <div>
                    <p className="text-red-700 font-medium flex items-center gap-2">
                      <XCircle className="w-5 h-5" />❌ Risco alto - Justificativa obrigatória
                    </p>
                    {/* AJUSTE 3: Mensagem de reversibilidade */}
                    <p className="text-xs text-gray-600 mt-1 ml-7">
                      Esta ação poderá ser revertida posteriormente.
                    </p>
                  </div>
                )}
              </div>

              {/* AJUSTE 2 e 6: Botão explícito com estado de loading */}
              <button
                onClick={() => onProcessar(validacao)}
                disabled={processando}
                className={`px-8 py-3 rounded-lg font-bold text-base transition-all flex items-center gap-2 ${
                  processando
                    ? "bg-gray-400 cursor-not-allowed"
                    : validacao.confianca === "ALTA"
                      ? "bg-green-600 hover:bg-green-700 text-white shadow-lg hover:shadow-xl"
                      : validacao.confianca === "MEDIA"
                        ? "bg-yellow-600 hover:bg-yellow-700 text-white shadow-lg hover:shadow-xl"
                        : "bg-red-600 hover:bg-red-700 text-white shadow-lg hover:shadow-xl"
                }`}
              >
                {processando ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Processando...
                  </>
                ) : (
                  <>
                    {validacao.confianca === "ALTA" &&
                      `✅ Processar → avançar ${validacao.quantidade_parcelas || validacao.parcelas_confirmadas || 0} parcelas`}
                    {validacao.confianca === "MEDIA" &&
                      `⚠️ Confirmar → avançar ${validacao.quantidade_parcelas || validacao.parcelas_confirmadas || 0} parcelas`}
                    {validacao.confianca === "BAIXA" &&
                      `❌ Justificar → avançar ${validacao.quantidade_parcelas || validacao.parcelas_confirmadas || 0} parcelas`}
                  </>
                )}
              </button>
            </>
          )}
        </div>

        {/* Alertas (se houver) */}
        {validacao.alertas && validacao.alertas.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <p className="text-sm font-medium text-gray-700 mb-2">⚠️ Alertas:</p>
            <ul className="space-y-1">
              {validacao.alertas.map((alerta, idx) => (
                <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                  <span className="text-yellow-600">•</span>
                  {alerta.mensagem || alerta}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
