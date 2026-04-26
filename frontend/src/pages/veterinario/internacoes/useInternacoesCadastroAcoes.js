import { useCallback } from "react";

import { vetApi } from "../vetApi";
import {
  FORM_EVOLUCAO_INICIAL,
  FORM_NOVA_INTERNACAO_INICIAL,
} from "./internacoesInitialState";

export function useInternacoesCadastroAcoes({
  abrirDetalhe,
  carregar,
  carregarDetalheInternacao,
  consultaIdQuery,
  formAlta,
  formEvolucao,
  formNova,
  modalAlta,
  modalEvolucao,
  setAba,
  setCentroAba,
  setErro,
  setFiltroPessoaHistorico,
  setFiltroPetHistorico,
  setFormAlta,
  setFormEvolucao,
  setFormNova,
  setModalAlta,
  setModalEvolucao,
  setModalNova,
  setSalvando,
  setTutorNovaSelecionado,
}) {
  const abrirNovaInternacao = useCallback(() => {
    setAba("ativas");
    setTutorNovaSelecionado(null);
    setFormNova({ ...FORM_NOVA_INTERNACAO_INICIAL });
    setModalNova(true);
  }, [setAba, setFormNova, setModalNova, setTutorNovaSelecionado]);

  const selecionarInternacaoNoMapa = useCallback(
    (internacaoId) => {
      setAba("ativas");
      setCentroAba("lista");
      abrirDetalhe(internacaoId);
    },
    [abrirDetalhe, setAba, setCentroAba]
  );

  const selecionarPessoaHistorico = useCallback(
    (pessoaId) => {
      setFiltroPessoaHistorico(pessoaId);
      setFiltroPetHistorico("");
    },
    [setFiltroPessoaHistorico, setFiltroPetHistorico]
  );

  const criarInternacao = useCallback(async () => {
    if (!formNova.pet_id || !formNova.motivo) return;
    if (!formNova.box) {
      setErro("Selecione uma baia livre no mapa para internar.");
      return;
    }

    setSalvando(true);
    try {
      await vetApi.criarInternacao({
        pet_id: formNova.pet_id,
        consulta_id: consultaIdQuery ? Number(consultaIdQuery) : undefined,
        motivo: formNova.motivo,
        box: formNova.box || undefined,
      });
      setModalNova(false);
      setFormNova({ ...FORM_NOVA_INTERNACAO_INICIAL });
      setTutorNovaSelecionado(null);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao criar internação.");
    } finally {
      setSalvando(false);
    }
  }, [
    carregar,
    consultaIdQuery,
    formNova.box,
    formNova.motivo,
    formNova.pet_id,
    setErro,
    setFormNova,
    setModalNova,
    setSalvando,
    setTutorNovaSelecionado,
  ]);

  const darAlta = useCallback(async () => {
    if (!modalAlta) return;
    setSalvando(true);
    try {
      await vetApi.darAlta(modalAlta, formAlta || undefined);
      setModalAlta(null);
      setFormAlta("");
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao dar alta.");
    } finally {
      setSalvando(false);
    }
  }, [carregar, formAlta, modalAlta, setErro, setFormAlta, setModalAlta, setSalvando]);

  const registrarEvolucao = useCallback(async () => {
    if (!modalEvolucao) return;
    const internacaoId = modalEvolucao;
    setSalvando(true);
    try {
      await vetApi.registrarEvolucao(internacaoId, {
        temperatura: formEvolucao.temperatura ? Number.parseFloat(formEvolucao.temperatura) : undefined,
        frequencia_cardiaca: formEvolucao.fc ? Number.parseInt(formEvolucao.fc, 10) : undefined,
        frequencia_respiratoria: formEvolucao.fr ? Number.parseInt(formEvolucao.fr, 10) : undefined,
        observacoes: formEvolucao.observacoes || undefined,
      });
      await carregarDetalheInternacao(internacaoId, true);
      setModalEvolucao(null);
      setFormEvolucao({ ...FORM_EVOLUCAO_INICIAL });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar evolução.");
    } finally {
      setSalvando(false);
    }
  }, [
    carregarDetalheInternacao,
    formEvolucao.fc,
    formEvolucao.fr,
    formEvolucao.observacoes,
    formEvolucao.temperatura,
    modalEvolucao,
    setErro,
    setFormEvolucao,
    setModalEvolucao,
    setSalvando,
  ]);

  const fecharModalNovaInternacao = useCallback(() => {
    setModalNova(false);
    if (!consultaIdQuery) {
      setTutorNovaSelecionado(null);
      setFormNova({ ...FORM_NOVA_INTERNACAO_INICIAL });
    }
  }, [consultaIdQuery, setFormNova, setModalNova, setTutorNovaSelecionado]);

  return {
    abrirNovaInternacao,
    criarInternacao,
    darAlta,
    fecharModalNovaInternacao,
    registrarEvolucao,
    selecionarInternacaoNoMapa,
    selecionarPessoaHistorico,
  };
}
