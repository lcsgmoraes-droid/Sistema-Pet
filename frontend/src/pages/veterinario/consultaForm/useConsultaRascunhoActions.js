import { vetApi } from "../vetApi";
import { buildConsultaPayload } from "./consultaFormState";
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

  async function salvarRascunho() {
    setSalvando(true);
    setErro(null);
    setSucesso(null);
    try {
      const petSelecionadoAtual = pets.find((pet) => String(pet.id) === String(form.pet_id));

      if (!petSelecionadoAtual?.cliente_id) {
        setErro("Selecione um pet valido vinculado a um tutor.");
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }

      const payload = buildConsultaPayload({
        form,
        petSelecionadoAtual,
        tipoQuery,
        agendamentoIdQuery,
      });

      if (!consultaIdAtual) {
        const res = await vetApi.criarConsulta(payload);
        setConsultaIdAtual(res.data.id);
        navigate(`/veterinario/consultas/${res.data.id}`, { replace: true });
      } else {
        await vetApi.atualizarConsulta(consultaIdAtual, payload);
      }

      setSucesso(
        etapa < ETAPAS.length - 1
          ? "Rascunho salvo com sucesso."
          : "Rascunho salvo com sucesso. Voce pode finalizar quando quiser."
      );

      if (etapa < ETAPAS.length - 1) setEtapa((etapaAtual) => etapaAtual + 1);
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Erro ao salvar. Tente novamente.");
      window.scrollTo({ top: 0, behavior: "smooth" });
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
