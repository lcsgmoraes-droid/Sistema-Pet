import { vetApi } from "../vetApi";
import { buildConsultaPayload, buildRascunhoItensConsultaPayload } from "./consultaFormState";
import { buildMensagemRascunhoSalvo } from "./consultaRascunhoFeedback";
import { ETAPAS } from "./consultaFormUtils";

export default function useConsultaRascunhoActions({
  agendamentoIdQuery,
  consultaIdAtual,
  etapa,
  form,
  navigate,
  pets,
  selecionarPetCriado,
  setConsultaIdAtual,
  setErro,
  setEtapa,
  setModalNovoPetAberto,
  setModalRascunhoSalvoAberto,
  setRascunhoSalvoMensagem,
  setSalvando,
  setSucesso,
  tipoQuery,
  tutorSelecionado,
}) {
  function abrirModalNovoPet() {
    if (!tutorSelecionado) return;
    setModalNovoPetAberto(true);
  }

  function handleNovoPetCriado(petCriado) {
    if (!petCriado?.id) {
      setModalNovoPetAberto(false);
      return;
    }

    const mensagem = selecionarPetCriado(petCriado);
    setModalNovoPetAberto(false);
    setErro(null);
    setSucesso(mensagem);
  }

  async function salvarRascunho(opcoes = {}) {
    const { avancarEtapa = true, exibirFeedback = true } = opcoes;

    setSalvando(true);
    setErro(null);
    setSucesso(null);
    try {
      const petSelecionadoAtual = pets.find((pet) => String(pet.id) === String(form.pet_id));

      if (!petSelecionadoAtual?.cliente_id) {
        setErro("Selecione um pet valido vinculado a um tutor.");
        window.scrollTo({ top: 0, behavior: "smooth" });
        return { ok: false, consultaId: null };
      }

      const payload = buildConsultaPayload({
        form,
        petSelecionadoAtual,
        tipoQuery,
        agendamentoIdQuery,
      });

      let consultaIdParaSalvar = consultaIdAtual;

      if (!consultaIdAtual) {
        const res = await vetApi.criarConsulta(payload);
        const novoId = res.data.id;
        await vetApi.atualizarConsulta(novoId, payload);
        consultaIdParaSalvar = novoId;
        setConsultaIdAtual(novoId);
        navigate(`/veterinario/consultas/${novoId}`, { replace: true });
      } else {
        await vetApi.atualizarConsulta(consultaIdAtual, payload);
      }

      await vetApi.sincronizarRascunhoConsulta(
        consultaIdParaSalvar,
        buildRascunhoItensConsultaPayload(form)
      );

      if (exibirFeedback) {
        const mensagem = buildMensagemRascunhoSalvo({ etapa, totalEtapas: ETAPAS.length });
        setSucesso(mensagem);
        setRascunhoSalvoMensagem(mensagem);
        setModalRascunhoSalvoAberto(true);
      }

      if (avancarEtapa && etapa < ETAPAS.length - 1) setEtapa((etapaAtual) => etapaAtual + 1);
      return { ok: true, consultaId: consultaIdParaSalvar };
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Erro ao salvar. Tente novamente.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return { ok: false, consultaId: null };
    } finally {
      setSalvando(false);
    }
  }

  return {
    abrirModalNovoPet,
    handleNovoPetCriado,
    salvarRascunho,
  };
}
