import { vetApi } from "../vetApi";
import { criarIdMensagemLocal } from "./assistenteIAUtils";

export default function useAssistenteIAChatHandlers({
  carregando,
  consultaId,
  conversaId,
  exameId,
  filtrarConversasContexto,
  med1,
  med2,
  mensagem,
  modo,
  pesoKg,
  petId,
  salvandoFeedbackId,
  setCarregando,
  setCarregandoHistorico,
  setConversaId,
  setConversas,
  setErro,
  setHistorico,
  setMensagem,
  setSalvandoFeedbackId,
}) {
  async function enviar() {
    if (!mensagem.trim() || carregando) return;

    const msg = mensagem.trim();
    const mensagemUsuarioLocalId = criarIdMensagemLocal();
    const mensagemIaLocalId = criarIdMensagemLocal();
    setErro("");
    setHistorico((h) => [...h, { localId: mensagemUsuarioLocalId, role: "user", text: msg }]);
    setMensagem("");
    setCarregando(true);

    try {
      const res = await vetApi.assistenteIA({
        modo,
        mensagem: msg,
        conversa_id: conversaId ? Number(conversaId) : undefined,
        salvar_historico: true,
        pet_id: petId ? Number(petId) : undefined,
        consulta_id: consultaId ? Number(consultaId) : undefined,
        exame_id: exameId ? Number(exameId) : undefined,
        medicamento_1: med1 || undefined,
        medicamento_2: med2 || undefined,
        peso_kg: pesoKg ? Number(String(pesoKg).replace(",", ".")) : undefined,
      });
      const novaConversaId = res.data?.conversa_id;
      setHistorico((h) => [
        ...h,
        { localId: mensagemIaLocalId, role: "ia", text: res.data?.resposta || "Sem resposta." },
      ]);

      if (novaConversaId) {
        setConversaId(String(novaConversaId));
        await carregarConversas();
        await carregarMensagensConversa(String(novaConversaId));
      }
    } catch (e) {
      const detail = e?.response?.data?.detail || "Não foi possível falar com a IA agora.";
      setErro(detail);
      setHistorico((h) => [...h, { localId: mensagemIaLocalId, role: "ia", text: `Erro: ${detail}` }]);
    } finally {
      setCarregando(false);
    }
  }

  async function carregarConversas() {
    try {
      const params = { limit: 30 };
      if (filtrarConversasContexto) {
        if (petId) params.pet_id = Number(petId);
        if (consultaId) params.consulta_id = Number(consultaId);
        if (exameId) params.exame_id = Number(exameId);
      }
      const res = await vetApi.listarConversasAssistenteIA(params);
      const lista = res.data?.items || [];
      setConversas(Array.isArray(lista) ? lista : []);
    } catch {
      setConversas([]);
    }
  }

  async function carregarMensagensConversa(id) {
    if (!id) return;
    setCarregandoHistorico(true);
    try {
      const res = await vetApi.listarMensagensConversaAssistenteIA(Number(id));
      const itens = res.data?.items || [];
      setHistorico(
        itens.map((item) => ({
          id: item.id,
          role: item.tipo === "usuario" ? "user" : "ia",
          text: item.conteudo || "",
          feedback: item.feedback || null,
        }))
      );
    } catch {
      setHistorico([]);
    } finally {
      setCarregandoHistorico(false);
    }
  }

  function novaConversa() {
    setConversaId("");
    setHistorico([]);
    setErro("");
  }

  async function enviarFeedback(mensagemId, util) {
    if (!mensagemId || salvandoFeedbackId) return;
    setSalvandoFeedbackId(String(mensagemId));
    try {
      const comentarioBruto = globalThis.prompt("Comentário opcional para melhorar a IA:", "") || "";
      const comentario = comentarioBruto.trim();
      const payload = {
        util,
        nota: util ? 5 : 2,
        comentario: comentario || undefined,
      };
      await vetApi.feedbackMensagemAssistenteIA(mensagemId, payload);
      setHistorico((atual) =>
        atual.map((msg) =>
          msg.id === mensagemId
            ? { ...msg, feedback: { util, nota: util ? 5 : 2, comentario: comentario || null } }
            : msg
        )
      );
    } catch {
      // Mantem a conversa sem interromper o fluxo principal.
    } finally {
      setSalvandoFeedbackId("");
    }
  }

  function perguntaRapida(texto) {
    setMensagem(texto);
  }

  return {
    carregarConversas,
    carregarMensagensConversa,
    enviar,
    enviarFeedback,
    novaConversa,
    perguntaRapida,
  };
}
