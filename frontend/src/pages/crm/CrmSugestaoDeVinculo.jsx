import { UserCheck } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

// Ao abrir um card sem cadastro, pergunta se ele deve ser ligado a uma pessoa que passou a
// existir com o mesmo telefone. Sim liga; Não só fecha o aviso (volta a perguntar na próxima
// abertura); Não perguntar novamente grava que aquela pessoa não deve mais ser sugerida
// para este card.
export default function CrmSugestaoDeVinculo({ card, onVinculado }) {
  const [sugestao, setSugestao] = useState(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const { data } = await api.get(`/crm/leads/${card.id}/sugestao-vinculo`, {
          params: { loja_id: card.loja_id },
        });
        if (ativo) setSugestao(data.sugestao || null);
      } catch {
        // A sugestão é um extra: se falhar, a ficha segue funcionando sem ela.
      }
    })();
    return () => {
      ativo = false;
    };
  }, [card.id, card.loja_id]);

  if (!sugestao) return null;

  const chamar = async (caminho, sucesso) => {
    setEnviando(true);
    try {
      await api.post(`/crm/leads/${card.id}/${caminho}`, {
        loja_id: card.loja_id,
        cliente_id: sugestao.cliente_id,
      });
      toast.success(sucesso);
      setSugestao(null);
      return true;
    } catch (error) {
      toast.error(mensagemDeErro(error, "Não foi possível concluir."));
      return false;
    } finally {
      setEnviando(false);
    }
  };

  const vincular = async () => {
    if (await chamar("vincular", "Card ligado ao cadastro.")) onVinculado();
  };

  return (
    <section
      aria-labelledby="crm-sugestao-vinculo"
      className="space-y-3 rounded-2xl border border-sky-200 bg-sky-50 p-4 dark:border-sky-800 dark:bg-sky-950/40"
    >
      <h3
        id="crm-sugestao-vinculo"
        className="flex items-center gap-2 text-sm font-bold text-sky-900 dark:text-sky-100"
      >
        <UserCheck className="h-4 w-4" aria-hidden="true" />
        Encontramos um cadastro com este telefone
      </h3>
      <p className="text-sm text-sky-900 dark:text-sky-100">
        <strong>{sugestao.nome}</strong>
        {sugestao.telefone ? ` · ${sugestao.telefone}` : ""}. Ligar este card a essa pessoa?
      </p>
      <div className="flex flex-wrap gap-2">
        <BotaoInteracao onClick={vincular} loading={enviando}>
          Sim, ligar
        </BotaoInteracao>
        <BotaoCancelar onClick={() => setSugestao(null)} disabled={enviando}>
          Não
        </BotaoCancelar>
        <BotaoCancelar
          onClick={() => chamar("sugestao-vinculo/ignorar", "Combinado, não vamos sugerir essa pessoa de novo.")}
          disabled={enviando}
        >
          Não perguntar novamente
        </BotaoCancelar>
      </div>
    </section>
  );
}
