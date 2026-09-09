import { useEffect, useState } from "react";
import { X, Copy, Download, MessageCircle } from "lucide-react";
import api from "../../api";
import { linkWhatsAppNota } from "./compartilharNota";

export default function NFSaidaCompartilharModal({ nota, fechar, baixarDanfe, documentoEmCurso }) {
  const [dados, setDados] = useState(null);
  const [telefone, setTelefone] = useState("");
  const [erro, setErro] = useState("");
  const [copiado, setCopiado] = useState(false);
  useEffect(() => {
    let ativo = true;
    api
      .get(`/nfe/${nota.id}/compartilhar`)
      .then(({ data }) => {
        if (ativo) {
          setDados(data);
          setTelefone(data.telefone || "");
        }
      })
      .catch((error) => {
        if (ativo)
          setErro(error.response?.data?.detail || "Não foi possível preparar o compartilhamento.");
      });
    return () => {
      ativo = false;
    };
  }, [nota.id]);
  const whatsapp = dados ? linkWhatsAppNota(dados, telefone) : "";
  async function copiar() {
    try {
      await navigator.clipboard.writeText(dados.link);
      setCopiado(true);
    } catch {
      setErro("Não foi possível copiar. Use o botão de WhatsApp ou baixe o PDF.");
    }
  }
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="compartilhar-nota-titulo"
        className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6"
      >
        <div className="flex justify-between items-center mb-4">
          <h2 id="compartilhar-nota-titulo" className="text-xl font-semibold">
            Compartilhar nota {nota.numero}
          </h2>
          <button onClick={fechar} aria-label="Fechar compartilhamento">
            <X />
          </button>
        </div>
        <p className="text-gray-600 mb-4">{nota.cliente?.nome}</p>
        {erro && (
          <p role="alert" className="text-red-700 mb-3">
            {erro}
          </p>
        )}
        {!dados && !erro && <p role="status">Preparando nota...</p>}
        {dados && (
          <>
            <label className="block text-sm font-medium" htmlFor="telefone-nota">
              WhatsApp do cliente
            </label>
            <input
              id="telefone-nota"
              type="tel"
              value={telefone}
              onChange={(event) => setTelefone(event.target.value)}
              placeholder="DDD + número"
              className="mt-1 w-full border rounded-lg p-3"
            />
            <p className="text-sm text-gray-500 mt-2 mb-4">
              Confira o número. O WhatsApp abrirá com o link da nota; você confirma o envio na
              conversa.
            </p>
            {whatsapp ? (
              <a
                href={whatsapp}
                target="_blank"
                rel="noopener noreferrer"
                className="flex justify-center gap-2 rounded-lg bg-green-700 text-white p-3"
              >
                <MessageCircle size={20} />
                Abrir WhatsApp
              </a>
            ) : (
              <p className="text-sm text-gray-600 mb-3">
                Informe um telefone com DDD para abrir o WhatsApp.
              </p>
            )}
            <div className="flex gap-3 mt-4">
              <button onClick={copiar} className="flex items-center gap-2 border rounded-lg p-3">
                <Copy size={18} />
                {copiado ? "Link copiado" : "Copiar link"}
              </button>
              <button
                disabled={documentoEmCurso === String(nota.id)}
                onClick={() => baixarDanfe(nota.id, nota.numero)}
                className="flex items-center gap-2 border rounded-lg p-3 disabled:opacity-50"
              >
                <Download size={18} />
                {documentoEmCurso ? "Baixando..." : "Baixar PDF"}
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
