import { MessageCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputDataHora from "../../components/v2/InputDataHora/InputDataHora";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import CrmBuscaTutor from "./CrmBuscaTutor";
import { formatarReais } from "../../utils/consumoWhatsapp";
import { whatsappUrl } from "../lembretes/lembretesUtils";
import { rotuloDaOportunidade } from "./crmUtils";

const TIPOS_DE_ACAO = [
  { value: "ligacao", label: "Ligação" },
  { value: "mensagem", label: "Mensagem" },
  { value: "visita", label: "Visita" },
  { value: "atendimento", label: "Atendimento" },
  { value: "observacao", label: "Observação" },
];
const TIPOS_DE_PASSO = [
  { value: "ligar", label: "Ligar" },
  { value: "mensagem", label: "Enviar mensagem" },
  { value: "visita", label: "Visita" },
  { value: "oferecer", label: "Oferecer" },
  { value: "outro", label: "Outro" },
];

function formatarQuando(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

// Ficha do card: oportunidades, caminhada de colunas, linha do tempo, registrar ação e
// agendar o próximo passo. A ficha 360 completa (compras, pets, vacinas) vem na etapa 3.
export default function CrmFichaModal({ card, onAlterado, onFechar }) {
  const [ficha, setFicha] = useState(null);
  const [erro, setErro] = useState("");
  const [tipoAcao, setTipoAcao] = useState("ligacao");
  const [observacao, setObservacao] = useState("");
  const [tipoPasso, setTipoPasso] = useState("ligar");
  const [quando, setQuando] = useState("");
  const [clienteVinculo, setClienteVinculo] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [tentouPasso, setTentouPasso] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.get(`/crm/leads/${card.id}`, {
        params: { loja_id: card.loja_id },
      });
      setFicha(data);
      setErro("");
    } catch (error) {
      setErro(mensagemDeErro(error, "Não foi possível abrir a ficha."));
    }
  }, [card.id, card.loja_id]);

  useEffect(() => {
    let ativo = true;
    (async () => {
      if (ativo) await carregar();
    })();
    return () => {
      ativo = false;
    };
  }, [carregar]);

  const enviar = async (caminho, corpo, sucesso) => {
    setEnviando(true);
    try {
      await api.post(`/crm/leads/${card.id}/${caminho}`, { loja_id: card.loja_id, ...corpo });
      toast.success(sucesso);
      await carregar();
      onAlterado();
      return true;
    } catch (error) {
      toast.error(mensagemDeErro(error, "Não foi possível salvar."));
      return false;
    } finally {
      setEnviando(false);
    }
  };

  // Contato manual enquanto o canal oficial da loja não existe (ROADMAP 2.10): abre o
  // WhatsApp e já deixa o contato registrado na linha do tempo e no "último contato".
  const conversarNoWhatsapp = async () => {
    const url = whatsappUrl(ficha?.telefone, "");
    if (!url) {
      toast.error("Este card não tem telefone.");
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
    await enviar(
      "acoes",
      { tipo: "mensagem", observacao: "Contato iniciado pelo WhatsApp" },
      "Contato registrado.",
    );
  };

  const vincular = async () => {
    if (!clienteVinculo) return;
    const ok = await enviar("vincular", { cliente_id: clienteVinculo }, "Card ligado ao cadastro.");
    if (ok) setClienteVinculo(null);
  };

  const registrarAcao = async () => {
    const ok = await enviar("acoes", { tipo: tipoAcao, observacao }, "Ação registrada.");
    if (ok) setObservacao("");
  };

  const agendarPasso = async () => {
    setTentouPasso(true);
    if (!quando) return;
    const ok = await enviar(
      "proximo-passo",
      { tipo: tipoPasso, agendado_para: new Date(quando).toISOString() },
      "Próximo passo agendado.",
    );
    if (ok) {
      setQuando("");
      setTentouPasso(false);
    }
  };

  return (
    <ModalPadrao
      titulo={card.nome}
      tamanho="grande"
      onFechar={onFechar}
      rodape={<BotaoCancelar onClick={onFechar}>Fechar</BotaoCancelar>}
    >
      {erro ? (
        <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}
      {!ficha && !erro ? (
        <p role="status" className="text-sm text-slate-500 dark:text-slate-400">
          Carregando a ficha…
        </p>
      ) : null}

      {ficha ? (
        <div className="space-y-6">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {card.loja_nome ? `${card.loja_nome} · ` : ""}
            {ficha.sem_cadastro ? "Lead novo · sem cadastro" : "Tutor cadastrado"} · origem{" "}
            {ficha.origem} · ciclo {ficha.ciclo}
            {ficha.telefone ? ` · ${ficha.telefone}` : ""}
          </p>

          {ficha.telefone ? (
            <BotaoInteracao icon={MessageCircle} onClick={conversarNoWhatsapp} loading={enviando}>
              Conversar no WhatsApp
            </BotaoInteracao>
          ) : null}

          {ficha.sem_cadastro ? (
            <section aria-labelledby="crm-ficha-vinculo" className="space-y-3">
              <h3 id="crm-ficha-vinculo" className="text-sm font-bold">
                Ligar a um cadastro
              </h3>
              <CrmBuscaTutor
                id="crm-vinculo"
                lojaId={card.loja_id}
                value={clienteVinculo}
                onEscolher={setClienteVinculo}
              />
              <BotaoInteracao onClick={vincular} loading={enviando} disabled={!clienteVinculo}>
                Ligar ao cadastro
              </BotaoInteracao>
            </section>
          ) : null}

          {ficha.mensagens && ficha.mensagens.enviadas + ficha.mensagens.recebidas > 0 ? (
            <p className="text-sm text-slate-700 dark:text-slate-300">
              Mensagens de WhatsApp: {ficha.mensagens.enviadas} enviada(s),{" "}
              {ficha.mensagens.recebidas} recebida(s) · {ficha.mensagens.cobraveis} cobrável(is) ·
              custo estimado {formatarReais(ficha.mensagens.custo_estimado)}
            </p>
          ) : null}

          <section aria-labelledby="crm-ficha-oportunidades">
            <h3 id="crm-ficha-oportunidades" className="text-sm font-bold">
              Oportunidades
            </h3>
            {ficha.oportunidades.length === 0 ? (
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Nenhuma oportunidade ainda.
              </p>
            ) : (
              <ul className="mt-1 space-y-1 text-sm">
                {ficha.oportunidades.map((item) => (
                  <li key={item.id}>
                    {rotuloDaOportunidade(item)} · ciclo {item.ciclo} · {item.estado}
                    {item.motivo ? ` (${item.motivo})` : ""}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="crm-ficha-acao" className="space-y-3">
            <h3 id="crm-ficha-acao" className="text-sm font-bold">
              Registrar o que foi feito
            </h3>
            <InputCombobox
              id="crm-acao-tipo"
              label="Tipo"
              value={tipoAcao}
              opcoes={TIPOS_DE_ACAO}
              onChange={setTipoAcao}
            />
            <InputTextoLongo
              id="crm-acao-obs"
              label="Observação"
              value={observacao}
              maxLength={2000}
              onChange={setObservacao}
            />
            <BotaoInteracao onClick={registrarAcao} loading={enviando}>
              Registrar
            </BotaoInteracao>
          </section>

          <section aria-labelledby="crm-ficha-passo" className="space-y-3">
            <h3 id="crm-ficha-passo" className="text-sm font-bold">
              Próximo passo
            </h3>
            <InputCombobox
              id="crm-passo-tipo"
              label="O que fazer"
              value={tipoPasso}
              opcoes={TIPOS_DE_PASSO}
              onChange={setTipoPasso}
            />
            <InputDataHora
              id="crm-passo-quando"
              label="Quando"
              value={quando}
              onChange={setQuando}
              error={tentouPasso && !quando ? "Escolha a data e a hora." : ""}
              required
            />
            <BotaoInteracao onClick={agendarPasso} loading={enviando}>
              Agendar
            </BotaoInteracao>
          </section>

          <section aria-labelledby="crm-ficha-caminhada">
            <h3 id="crm-ficha-caminhada" className="text-sm font-bold">
              Caminhada do card
            </h3>
            <ol className="mt-1 space-y-1 text-sm">
              {ficha.caminhada.map((passo, indice) => (
                <li key={`${passo.quando}-${indice}`}>
                  {formatarQuando(passo.quando)} · ciclo {passo.ciclo} ·{" "}
                  {passo.de ? `${passo.de} → ${passo.para}` : `Entrou em ${passo.para}`}
                  {passo.nota ? ` — ${passo.nota}` : ""}
                </li>
              ))}
            </ol>
          </section>

          <section aria-labelledby="crm-ficha-tempo">
            <h3 id="crm-ficha-tempo" className="text-sm font-bold">
              Linha do tempo
            </h3>
            <ul className="mt-1 space-y-1 text-sm">
              {ficha.linha_do_tempo.map((item, indice) => (
                <li key={`${item.quando}-${indice}`}>
                  {formatarQuando(item.quando)} · {item.resumo}
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}
    </ModalPadrao>
  );
}
