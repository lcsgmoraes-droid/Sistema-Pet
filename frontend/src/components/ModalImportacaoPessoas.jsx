/**
 * Modal de Importacao de Pessoas (Clientes, Fornecedores, Veterinarios)
 */
import { useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

export default function ModalImportacaoPessoas({
  isOpen,
  onClose,
  onSuccess,
}) {
  const [arquivo, setArquivo] = useState(null);
  const [importando, setImportando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [etapa, setEtapa] = useState("upload");

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
        setArquivo(file);
        setResultado(null);
      } else {
        toast.error("Arquivo deve ser Excel (.xlsx ou .xls)");
        e.target.value = "";
      }
    }
  };

  const baixarTemplate = async () => {
    try {
      const token =
        localStorage.getItem("access_token") || localStorage.getItem("token");
      const response = await api.get("/pessoas/template-importacao", {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `template_pessoas_${new Date().toISOString().split("T")[0]}.xlsx`,
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success("Template baixado com sucesso!");
    } catch (error) {
      console.error("Erro ao baixar template:", error);
      toast.error("Erro ao baixar template");
    }
  };

  const handleImportar = async () => {
    if (!arquivo) {
      toast.error("Selecione um arquivo para importar");
      return;
    }

    setImportando(true);
    setEtapa("processando");

    try {
      const formData = new FormData();
      formData.append("file", arquivo);

      const response = await api.post("/pessoas/importar", formData);

      setResultado(response.data);
      setEtapa("resultado");

      const totalSucesso =
        (response.data.criados?.length || 0) +
        (response.data.atualizados?.length || 0);

      if (totalSucesso > 0) {
        toast.success(`${totalSucesso} pessoas processadas com sucesso!`);
        if (onSuccess) {
          onSuccess();
        }
      }

      if (response.data.total_erros > 0) {
        toast.error(`${response.data.total_erros} pessoas com erro`);
      }
    } catch (error) {
      console.error("Erro ao importar:", error);
      toast.error(error.response?.data?.detail || "Erro ao importar pessoas");
      setEtapa("upload");
    } finally {
      setImportando(false);
    }
  };

  const resetar = () => {
    setArquivo(null);
    setResultado(null);
    setEtapa("upload");
  };

  const fechar = () => {
    resetar();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-200 bg-gradient-to-r from-purple-600 to-purple-700 px-6 py-4">
          <div className="flex items-center gap-3">
            <svg
              className="h-6 w-6 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            <h2 className="text-xl font-bold text-white">
              Importacao de Pessoas em Lote
            </h2>
          </div>
          <button
            onClick={fechar}
            className="text-white transition-colors hover:text-gray-200"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="max-h-[calc(90vh-140px)] overflow-y-auto p-6">
          {etapa === "upload" && (
            <>
              <div className="mb-6 rounded-lg border border-purple-200 bg-purple-50 p-4">
                <h3 className="mb-2 flex items-center gap-2 font-semibold text-purple-900">
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  Como funciona
                </h3>
                <ul className="ml-7 space-y-1 text-sm text-purple-800">
                  <li>1. Baixe o template Excel clicando no botao abaixo</li>
                  <li>
                    2. Preencha os dados das pessoas (clientes, fornecedores,
                    veterinarios)
                  </li>
                  <li>3. Salve o arquivo e faca o upload aqui</li>
                  <li>
                    4. Pessoas novas serao criadas, existentes serao atualizadas
                    (baseado no CPF/CNPJ)
                  </li>
                </ul>
              </div>

              <div className="mb-6">
                <button
                  onClick={baixarTemplate}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-3 font-medium text-white transition-colors hover:bg-green-700"
                >
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  Baixar Template Excel
                </button>
              </div>

              <div className="mb-6">
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Selecione a Planilha Preenchida
                </label>
                <div className="flex w-full items-center justify-center">
                  <label className="flex h-64 w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 transition-colors hover:bg-gray-100">
                    <div className="flex flex-col items-center justify-center pb-6 pt-5">
                      <svg
                        className="mb-4 h-12 w-12 text-gray-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                        />
                      </svg>
                      <p className="mb-2 text-sm text-gray-500">
                        <span className="font-semibold">
                          Clique para selecionar
                        </span>{" "}
                        ou arraste o arquivo
                      </p>
                      <p className="text-xs text-gray-500">
                        Apenas arquivos Excel (.xlsx, .xls)
                      </p>

                      {arquivo && (
                        <div className="mt-4 flex items-center gap-2 text-purple-600">
                          <svg
                            className="h-5 w-5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                          </svg>
                          <span className="font-medium">{arquivo.name}</span>
                        </div>
                      )}
                    </div>
                    <input
                      type="file"
                      className="hidden"
                      accept=".xlsx,.xls"
                      onChange={handleFileChange}
                    />
                  </label>
                </div>
              </div>
            </>
          )}

          {etapa === "processando" && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="mb-4 h-16 w-16 animate-spin rounded-full border-b-2 border-purple-600" />
              <p className="text-lg text-gray-700">Processando planilha...</p>
              <p className="mt-2 text-sm text-gray-500">
                Isso pode levar alguns segundos
              </p>
            </div>
          )}

          {etapa === "resultado" && resultado && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
                  <div className="text-3xl font-bold text-blue-600">
                    {resultado.total_processados || 0}
                  </div>
                  <div className="mt-1 text-sm text-blue-800">
                    Total Processado
                  </div>
                </div>
                <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center">
                  <div className="text-3xl font-bold text-green-600">
                    {resultado.criados?.length || 0}
                  </div>
                  <div className="mt-1 text-sm text-green-800">Criados</div>
                </div>
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-600">
                    {resultado.atualizados?.length || 0}
                  </div>
                  <div className="mt-1 text-sm text-yellow-800">
                    Atualizados
                  </div>
                </div>
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
                  <div className="text-3xl font-bold text-red-600">
                    {resultado.total_erros || 0}
                  </div>
                  <div className="mt-1 text-sm text-red-800">Erros</div>
                </div>
              </div>

              {resultado.criados && resultado.criados.length > 0 && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                  <h4 className="mb-3 flex items-center gap-2 font-semibold text-green-900">
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                    Pessoas Criadas ({resultado.criados.length})
                  </h4>
                  <div className="max-h-40 overflow-y-auto">
                    <ul className="space-y-1 text-sm">
                      {resultado.criados.map((item, idx) => (
                        <li key={idx} className="text-green-800">
                          Linha {item.linha}:{" "}
                          <span className="font-medium">{item.nome}</span> (
                          {item.tipo})
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {resultado.atualizados && resultado.atualizados.length > 0 && (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                  <h4 className="mb-3 flex items-center gap-2 font-semibold text-yellow-900">
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                    Pessoas Atualizadas ({resultado.atualizados.length})
                  </h4>
                  <div className="max-h-40 overflow-y-auto">
                    <ul className="space-y-1 text-sm">
                      {resultado.atualizados.map((item, idx) => (
                        <li key={idx} className="text-yellow-800">
                          Linha {item.linha}:{" "}
                          <span className="font-medium">{item.nome}</span> (
                          {item.tipo})
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {resultado.erros && resultado.erros.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                  <h4 className="mb-3 flex items-center gap-2 font-semibold text-red-900">
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    Erros ({resultado.erros.length})
                  </h4>
                  <div className="max-h-40 overflow-y-auto">
                    <ul className="space-y-2 text-sm">
                      {resultado.erros.map((item, idx) => (
                        <li key={idx} className="text-red-800">
                          <strong>Linha {item.linha}</strong> (
                          {item.nome || "?"}): {item.erro}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4">
          {etapa === "upload" && (
            <>
              <button
                onClick={fechar}
                className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-100"
              >
                Cancelar
              </button>
              <button
                onClick={handleImportar}
                disabled={!arquivo || importando}
                className="flex items-center gap-2 rounded-lg bg-purple-600 px-6 py-2 text-white transition-colors hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-gray-400"
              >
                {importando ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-b-2 border-white" />
                    Importando...
                  </>
                ) : (
                  <>
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    Importar Pessoas
                  </>
                )}
              </button>
            </>
          )}

          {etapa === "resultado" && (
            <>
              <button
                onClick={resetar}
                className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-100"
              >
                Importar Novamente
              </button>
              <button
                onClick={fechar}
                className="rounded-lg bg-purple-600 px-6 py-2 text-white transition-colors hover:bg-purple-700"
              >
                Concluir
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
