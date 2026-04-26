import { Send } from "lucide-react";
import { assistenteIaCss, perguntasRapidasAssistenteIA } from "./assistenteIAUtils";

export default function AssistenteIAComposer({
  carregando,
  erro,
  mensagem,
  onEnviar,
  onPerguntaRapida,
  setMensagem,
}) {
  return (
    <>
      <div className="flex flex-wrap gap-2">
        {perguntasRapidasAssistenteIA.map((pergunta) => (
          <button
            key={pergunta.label}
            type="button"
            onClick={() => onPerguntaRapida(pergunta.texto)}
            className="text-xs px-2.5 py-1.5 rounded-md border border-cyan-200 text-cyan-700 hover:bg-cyan-50"
          >
            {pergunta.label}
          </button>
        ))}
      </div>

      <textarea
        value={mensagem}
        onChange={(event) => setMensagem(event.target.value)}
        className={assistenteIaCss.textarea}
        placeholder="Descreva o caso: sintomas, exames, medicações e sua pergunta..."
      />

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onEnviar}
          disabled={!mensagem.trim() || carregando}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-60"
        >
          <Send size={14} /> {carregando ? "Enviando..." : "Perguntar à IA"}
        </button>
      </div>

      {erro && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {erro}
        </div>
      )}
    </>
  );
}
