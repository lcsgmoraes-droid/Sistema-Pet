import { useCallback } from "react";
import { vetApi } from "../vetApi";
import {
  AGENDA_FORM_INICIAL,
  FORM_EVOLUCAO_INICIAL,
  FORM_FEITO_INICIAL,
  FORM_INSUMO_RAPIDO_INICIAL,
  FORM_NOVA_INTERNACAO_INICIAL,
} from "./internacoesInitialState";
import { formatQuantity, parseQuantity } from "./internacaoUtils";

export function useInternacoesAcoes({
  aba,
  agendaForm,
  carregarAgendaProcedimentos,
  consultaIdQuery,
  expandida,
  filtroDataAltaFim,
  filtroDataAltaInicio,
  filtroPessoaHistorico,
  filtroPetHistorico,
  formAlta,
  formEvolucao,
  formFeito,
  formInsumoRapido,
  formNova,
  insumoRapidoSelecionado,
  modalAlta,
  modalEvolucao,
  modalFeito,
  setAba,
  setAgendaForm,
  setAgendaProcedimentos,
  setCarregando,
  setCarregandoHistoricoPet,
  setCentroAba,
  setErro,
  setEvolucoes,
  setExpandida,
  setFiltroPessoaHistorico,
  setFiltroPetHistorico,
  setFormAlta,
  setFormEvolucao,
  setFormFeito,
  setFormInsumoRapido,
  setFormNova,
  setHistoricoPet,
  setInsumoRapidoSelecionado,
  setInternacoes,
  setModalAlta,
  setModalEvolucao,
  setModalFeito,
  setModalHistoricoPet,
  setModalInsumoRapido,
  setModalNova,
  setProcedimentosInternacao,
  setSalvando,
  setTutorNovaSelecionado,
  sugestaoHorario,
}) {
  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      const params = aba === "ativas"
        ? { status: "internado" }
        : {
            status: "alta",
            data_saida_inicio: filtroDataAltaInicio || undefined,
            data_saida_fim: filtroDataAltaFim || undefined,
            cliente_id: filtroPessoaHistorico || undefined,
            pet_id: filtroPetHistorico || undefined,
          };
      const res = await vetApi.listarInternacoes(params);
      setInternacoes(Array.isArray(res.data) ? res.data : (res.data?.items ?? []));
    } catch {
      setErro("Erro ao carregar internações.");
    } finally {
      setCarregando(false);
    }
  }, [
    aba,
    filtroDataAltaFim,
    filtroDataAltaInicio,
    filtroPessoaHistorico,
    filtroPetHistorico,
    setCarregando,
    setErro,
    setInternacoes,
  ]);

  async function carregarDetalheInternacao(id, manterExpandido = true) {
    try {
      const res = await vetApi.obterInternacao(id);
      setEvolucoes((prev) => ({ ...prev, [id]: res.data?.evolucoes ?? [] }));
      setProcedimentosInternacao((prev) => ({ ...prev, [id]: res.data?.procedimentos ?? [] }));
      if (manterExpandido) setExpandida(id);
    } catch {}
  }

  async function abrirDetalhe(id) {
    const fechando = expandida === id;
    setExpandida(fechando ? null : id);
    if (!fechando) {
      await carregarDetalheInternacao(id, true);
    }
  }

  function abrirNovaInternacao() {
    setAba("ativas");
    setTutorNovaSelecionado(null);
    setFormNova({ ...FORM_NOVA_INTERNACAO_INICIAL });
    setModalNova(true);
  }

  function selecionarInternacaoNoMapa(internacaoId) {
    setAba("ativas");
    setCentroAba("lista");
    abrirDetalhe(internacaoId);
  }

  function selecionarPessoaHistorico(pessoaId) {
    setFiltroPessoaHistorico(pessoaId);
    setFiltroPetHistorico("");
  }

  async function criarInternacao() {
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
  }

  async function darAlta() {
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
  }

  async function registrarEvolucao() {
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
  }

  async function adicionarProcedimentoAgenda() {
    if (!agendaForm.internacao_id || !agendaForm.horario || !agendaForm.medicamento) {
      setErro("Preencha internação, horário e medicamento na agenda de procedimentos.");
      return;
    }

    setSalvando(true);

    try {
      const lembreteMin = Number.parseInt(agendaForm.lembrete_min || "30", 10);
      const response = await vetApi.criarProcedimentoAgendaInternacao(agendaForm.internacao_id, {
        horario_agendado: agendaForm.horario,
        medicamento: agendaForm.medicamento.trim(),
        dose: agendaForm.dose || undefined,
        quantidade_prevista: parseQuantity(agendaForm.quantidade_prevista) ?? undefined,
        unidade_quantidade: agendaForm.unidade_quantidade?.trim() || undefined,
        via: agendaForm.via || undefined,
        lembrete_min: Number.isFinite(lembreteMin) ? lembreteMin : 30,
        observacoes_agenda: agendaForm.observacoes || undefined,
      });

      if (response.data?.id) {
        setAgendaProcedimentos((prev) => [response.data, ...prev]);
      } else {
        await carregarAgendaProcedimentos();
      }
      await carregarDetalheInternacao(agendaForm.internacao_id, expandida === Number(agendaForm.internacao_id));
      setAgendaForm((prev) => ({
        ...prev,
        horario: sugestaoHorario,
        medicamento: "",
        dose: "",
        quantidade_prevista: "",
        unidade_quantidade: "",
        via: "",
        observacoes: "",
      }));
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar procedimento agendado.");
    } finally {
      setSalvando(false);
    }
  }

  function abrirModalFeito(item) {
    const agora = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    const valorPadrao = `${agora.getFullYear()}-${pad(agora.getMonth() + 1)}-${pad(agora.getDate())}T${pad(agora.getHours())}:${pad(agora.getMinutes())}`;

    setModalFeito(item);
    setFormFeito({
      feito_por: item?.feito_por || "",
      horario_execucao: item?.horario_execucao || valorPadrao,
      observacao_execucao: item?.observacao_execucao || "",
      quantidade_prevista: item?.quantidade_prevista ?? "",
      quantidade_executada: item?.quantidade_executada ?? item?.quantidade_prevista ?? "",
      quantidade_desperdicio: item?.quantidade_desperdicio ?? "",
      unidade_quantidade: item?.unidade_quantidade ?? "",
    });
  }

  async function confirmarProcedimentoFeito() {
    if (!modalFeito) return;
    if (!formFeito.feito_por.trim()) {
      setErro("Informe quem executou o procedimento.");
      return;
    }
    if (!formFeito.horario_execucao) {
      setErro("Informe o horário da execução.");
      return;
    }

    setSalvando(true);

    try {
      const response = await vetApi.concluirProcedimentoAgendaInternacao(modalFeito.id, {
        quantidade_prevista: parseQuantity(formFeito.quantidade_prevista) ?? undefined,
        quantidade_executada: parseQuantity(formFeito.quantidade_executada) ?? undefined,
        quantidade_desperdicio: parseQuantity(formFeito.quantidade_desperdicio) ?? undefined,
        unidade_quantidade: formFeito.unidade_quantidade?.trim() || undefined,
        executado_por: formFeito.feito_por.trim(),
        horario_execucao: formFeito.horario_execucao,
        observacao_execucao: formFeito.observacao_execucao?.trim() || undefined,
      });

      await carregarDetalheInternacao(
        modalFeito.internacao_id,
        String(expandida) === String(modalFeito.internacao_id)
      );

      setAgendaProcedimentos((prev) => prev.map((procedimento) => {
        if (String(procedimento.id) !== String(modalFeito.id)) return procedimento;
        return response.data?.id ? response.data : {
          ...procedimento,
          feito: true,
          status: "concluido",
          feito_por: formFeito.feito_por.trim(),
          horario_execucao: formFeito.horario_execucao,
          observacao_execucao: formFeito.observacao_execucao?.trim() || "",
          quantidade_prevista: formFeito.quantidade_prevista,
          quantidade_executada: formFeito.quantidade_executada,
          quantidade_desperdicio: formFeito.quantidade_desperdicio,
          unidade_quantidade: formFeito.unidade_quantidade,
        };
      }));
      setModalFeito(null);
      setFormFeito({ ...FORM_FEITO_INICIAL });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar procedimento concluído.");
    } finally {
      setSalvando(false);
    }
  }

  function abrirModalInsumoRapido(internacaoId = "") {
    setModalInsumoRapido(true);
    setInsumoRapidoSelecionado(null);
    setFormInsumoRapido({
      ...FORM_INSUMO_RAPIDO_INICIAL,
      internacao_id: internacaoId ? String(internacaoId) : "",
      horario_execucao: sugestaoHorario,
    });
  }

  async function confirmarInsumoRapido() {
    if (!formInsumoRapido.internacao_id) {
      setErro("Selecione o internado para lançar o insumo.");
      return;
    }
    if (!insumoRapidoSelecionado?.id) {
      setErro("Selecione o insumo/produto utilizado.");
      return;
    }
    if (!formInsumoRapido.responsavel.trim()) {
      setErro("Informe quem realizou o uso do insumo.");
      return;
    }

    const quantidadeUtilizada = parseQuantity(formInsumoRapido.quantidade_utilizada);
    const quantidadeDesperdicio = parseQuantity(formInsumoRapido.quantidade_desperdicio) ?? 0;
    const quantidadeConsumida = (quantidadeUtilizada ?? 0) + quantidadeDesperdicio;

    if (!quantidadeUtilizada || quantidadeUtilizada <= 0) {
      setErro("Informe a quantidade efetivamente utilizada do insumo.");
      return;
    }
    if (quantidadeConsumida <= 0) {
      setErro("A baixa total do insumo precisa ser maior que zero.");
      return;
    }

    setSalvando(true);
    try {
      const unidade = insumoRapidoSelecionado.unidade || "un";
      const internacaoId = String(formInsumoRapido.internacao_id);

      await vetApi.registrarProcedimentoInternacao(internacaoId, {
        status: "concluido",
        tipo_registro: "insumo",
        medicamento: `Insumo: ${insumoRapidoSelecionado.nome}`,
        dose: formatQuantity(quantidadeUtilizada, unidade),
        quantidade_prevista: quantidadeUtilizada,
        quantidade_executada: quantidadeUtilizada,
        quantidade_desperdicio: quantidadeDesperdicio || undefined,
        unidade_quantidade: unidade,
        executado_por: formInsumoRapido.responsavel.trim(),
        horario_execucao: formInsumoRapido.horario_execucao,
        observacao_execucao: formInsumoRapido.observacoes?.trim() || undefined,
        insumos: [
          {
            produto_id: insumoRapidoSelecionado.id,
            nome: insumoRapidoSelecionado.nome,
            unidade,
            quantidade: quantidadeConsumida,
            baixar_estoque: true,
          },
        ],
      });

      await carregarDetalheInternacao(Number(internacaoId), expandida === Number(internacaoId));
      setModalInsumoRapido(false);
      setInsumoRapidoSelecionado(null);
      setFormInsumoRapido({
        ...FORM_INSUMO_RAPIDO_INICIAL,
        horario_execucao: sugestaoHorario,
      });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao lançar insumo rápido.");
    } finally {
      setSalvando(false);
    }
  }

  function reabrirProcedimento() {
    setErro("Procedimento concluído já faz parte do histórico clínico. Para corrigir, registre um novo ajuste/evolução.");
  }

  async function removerProcedimentoAgenda(id) {
    setSalvando(true);
    try {
      await vetApi.removerProcedimentoAgendaInternacao(id);
      setAgendaProcedimentos((prev) => prev.filter((procedimento) => String(procedimento.id) !== String(id)));
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao remover procedimento da agenda.");
    } finally {
      setSalvando(false);
    }
  }

  async function abrirHistoricoPet(petId, petNome) {
    setCarregandoHistoricoPet(true);
    setModalHistoricoPet({ petId, petNome });
    setHistoricoPet([]);
    try {
      const res = await vetApi.historicoInternacoesPet(petId);
      setHistoricoPet(Array.isArray(res.data?.historico) ? res.data.historico : []);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao carregar histórico do pet.");
      setHistoricoPet([]);
    } finally {
      setCarregandoHistoricoPet(false);
    }
  }

  function fecharModalNovaInternacao() {
    setModalNova(false);
    if (!consultaIdQuery) {
      setTutorNovaSelecionado(null);
      setFormNova({ ...FORM_NOVA_INTERNACAO_INICIAL });
    }
  }

  return {
    abrirDetalhe,
    abrirHistoricoPet,
    abrirModalFeito,
    abrirModalInsumoRapido,
    abrirNovaInternacao,
    adicionarProcedimentoAgenda,
    carregar,
    confirmarInsumoRapido,
    confirmarProcedimentoFeito,
    criarInternacao,
    darAlta,
    fecharModalNovaInternacao,
    reabrirProcedimento,
    registrarEvolucao,
    removerProcedimentoAgenda,
    selecionarInternacaoNoMapa,
    selecionarPessoaHistorico,
  };
}
