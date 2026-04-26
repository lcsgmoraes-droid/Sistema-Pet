import { AlertCircle } from "lucide-react";

import ExameIABotoes from "./exameIA/ExameIABotoes";
import ExameIAChatBox from "./exameIA/ExameIAChatBox";
import ExameIAChatHeader from "./exameIA/ExameIAChatHeader";
import ExameIAIntro from "./exameIA/ExameIAIntro";
import ExameIAResumoCard from "./exameIA/ExameIAResumoCard";
import SeletorExameIA from "./exameIA/SeletorExameIA";
import { useExameChatIAAvancada } from "./exameIA/useExameChatIAAvancada";

export default function ExameChatIAAvancada({ petId, refreshToken, onNovoExame }) {
  const chat = useExameChatIAAvancada({ petId, refreshToken });

  return (
    <div className="overflow-hidden rounded-xl border border-indigo-200 bg-indigo-50">
      <ExameIAChatHeader
        expandido={chat.expandido}
        quantidadeExames={chat.exames.length}
        onToggle={() => chat.setExpandido((valorAtual) => !valorAtual)}
      />

      {chat.expandido && (
        <div className="space-y-3 px-4 pb-4">
          <ExameIAIntro />

          <div className="pt-1">
            <ExameIABotoes
              onNovoExame={onNovoExame}
              onProcessar={chat.exameSelecionado ? chat.processarExameSelecionado : undefined}
              processando={chat.processando}
              temAnaliseIA={chat.dadosIA.temAnaliseIA}
              temArquivo={chat.dadosIA.temArquivo}
            />
          </div>

          {chat.erroLocal && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-xs text-red-600">
              <AlertCircle size={14} />
              <span>{chat.erroLocal}</span>
            </div>
          )}

          {!petId ? (
            <p className="text-xs italic text-indigo-500">Selecione o pet para carregar os exames.</p>
          ) : chat.exames.length === 0 ? (
            <p className="text-xs italic text-indigo-500">
              Nenhum exame encontrado para este pet ainda. Voce ja pode cadastrar e anexar um arquivo acima.
            </p>
          ) : (
            <>
              <SeletorExameIA
                exameId={chat.exameId}
                exames={chat.exames}
                onChange={chat.alterarExame}
              />

              {chat.exameSelecionado && (
                <>
                  <ExameIAResumoCard dadosIA={chat.dadosIA} exame={chat.exameSelecionado} />

                  <ExameIAChatBox
                    carregando={chat.carregando}
                    chatFimRef={chat.chatFimRef}
                    historico={chat.historico}
                    onEnviar={chat.enviar}
                    onKeyDown={chat.handleKeyDown}
                    pergunta={chat.pergunta}
                    setPergunta={chat.setPergunta}
                    textoVazio={
                      'Pergunte sobre o exame selecionado. Ex.: "Ha anemia no hemograma?", "Tem alerta importante?", "O raio-x sugere alteracao pulmonar?" ou "Qual conduta devo revisar?".'
                    }
                  />
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
