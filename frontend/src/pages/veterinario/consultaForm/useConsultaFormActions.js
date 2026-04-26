import { vetApi } from "../vetApi";
import {
  buildConsultaPayload,
  buildFinalizacaoPayload,
  buildInsumoProcedimentoPayload,
  buildItensPrescricao,
  buildNovoExamePayload,
  criarInsumoRapidoFormInicial,
  criarNovoExameFormInicial,
} from "./consultaFormState";
import { ETAPAS, parseNumero } from "./consultaFormUtils";

export default function useConsultaFormActions({
  agendamentoIdQuery,
  carregarTimelineConsulta,
  consultaIdAtual,
  contextoConsultaParams,
  etapa,
  form,
  insumoRapidoForm,
  insumoRapidoSelecionado,
  navigate,
  novoExameArquivo,
  novoExameForm,
  pets,
  selecionarPetCriado,
  setConsultaIdAtual,
  setErro,
  setEtapa,
  setFinalizado,
  setInsumoRapidoForm,
  setInsumoRapidoSelecionado,
  setModalInsumoAberto,
  setModalNovoExameAberto,
  setModalNovoPetAberto,
  setNovoExameArquivo,
  setNovoExameForm,
  setRefreshExamesToken,
  setSalvando,
  setSalvandoInsumoRapido,
  setSalvandoNovoExame,
  setSucesso,
  tipoQuery,
  tutorSelecionado,
}) {
  function abrirModalInsumoRapido() {
    if (!consultaIdAtual) {
      setErro("Salve a consulta primeiro para lançar insumos rápidos.");
      return;
    }
    setInsumoRapidoSelecionado(null);
    setInsumoRapidoForm(criarInsumoRapidoFormInicial());
    setModalInsumoAberto(true);
  }

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
        setErro("Selecione um pet válido vinculado a um tutor.");
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
          : "Rascunho salvo com sucesso. Você pode finalizar quando quiser."
      );

      if (etapa < ETAPAS.length - 1) setEtapa((etapaAtual) => etapaAtual + 1);
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Erro ao salvar. Tente novamente.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setSalvando(false);
    }
  }

  async function finalizar() {
    setSucesso(null);
    if (!consultaIdAtual) {
      setErro("Salve a consulta antes de finalizar.");
      return;
    }
    setSalvando(true);
    setErro(null);
    try {
      await vetApi.atualizarConsulta(consultaIdAtual, buildFinalizacaoPayload(form));

      if (form.prescricao_itens.length > 0) {
        const itensPrescricao = buildItensPrescricao(form.prescricao_itens);

        if (itensPrescricao.length === 0) {
          setErro("Adicione ao menos 1 item de prescrição com nome e posologia.");
          return;
        }

        await vetApi.criarPrescricao({
          consulta_id: consultaIdAtual,
          pet_id: form.pet_id ? Number.parseInt(form.pet_id) : undefined,
          veterinario_id: form.veterinario_id ? Number.parseInt(form.veterinario_id) : undefined,
          tipo_receituario: "simples",
          itens: itensPrescricao,
        });
      }

      if (form.procedimentos_realizados.length > 0) {
        const procedimentosValidos = form.procedimentos_realizados.filter((item) => item.nome?.trim());
        for (const procedimento of procedimentosValidos) {
          await vetApi.adicionarProcedimento({
            consulta_id: consultaIdAtual,
            catalogo_id: procedimento.catalogo_id ? Number.parseInt(procedimento.catalogo_id) : undefined,
            nome: procedimento.nome,
            descricao: procedimento.descricao || undefined,
            valor: procedimento.valor ? Number(String(procedimento.valor).replace(",", ".")) : undefined,
            observacoes: procedimento.observacoes || undefined,
            realizado: true,
            baixar_estoque: procedimento.baixar_estoque !== false,
          });
        }
      }

      await vetApi.finalizarConsulta(consultaIdAtual);
      setFinalizado(true);
      await carregarTimelineConsulta();
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Erro ao finalizar.");
    } finally {
      setSalvando(false);
    }
  }

  function abrirFluxoConsulta(pathname, extras = {}) {
    if (!contextoConsultaParams) {
      setErro("Salve a consulta com um pet válido antes de abrir outro fluxo clínico.");
      return;
    }
    const params = new URLSearchParams(contextoConsultaParams);
    Object.entries(extras).forEach(([chave, valor]) => {
      if (valor == null || valor === "") return;
      params.set(chave, String(valor));
    });
    navigate(`${pathname}?${params.toString()}`);
  }

  async function salvarNovoExameRapido() {
    if (!form.pet_id || !novoExameForm.nome.trim()) {
      setErro("Selecione o pet e informe o nome do exame.");
      return;
    }

    setSalvandoNovoExame(true);
    setErro(null);
    try {
      const res = await vetApi.criarExame(buildNovoExamePayload({
        form,
        novoExameForm,
        consultaIdAtual,
        agendamentoIdQuery,
      }));

      if (novoExameArquivo) {
        await vetApi.uploadArquivoExame(res.data.id, novoExameArquivo);
        try {
          await vetApi.processarArquivoExameIA(res.data.id);
        } catch {
          // O exame fica registrado mesmo se a leitura por IA não estiver disponível.
        }
      }

      setModalNovoExameAberto(false);
      setNovoExameForm(criarNovoExameFormInicial());
      setNovoExameArquivo(null);
      setRefreshExamesToken((prev) => prev + 1);
      setSucesso("Exame vinculado à consulta com sucesso.");
      await carregarTimelineConsulta();
      setEtapa(1);
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Não foi possível registrar o exame.");
    } finally {
      setSalvandoNovoExame(false);
    }
  }

  async function salvarInsumoRapidoConsulta() {
    if (!consultaIdAtual) {
      setErro("Salve a consulta primeiro para lançar insumos.");
      return;
    }
    if (!insumoRapidoSelecionado?.id) {
      setErro("Selecione o insumo do estoque.");
      return;
    }

    const quantidadeUtilizada = parseNumero(insumoRapidoForm.quantidade_utilizada);
    const quantidadeDesperdicio = parseNumero(insumoRapidoForm.quantidade_desperdicio) || 0;
    const quantidadeConsumida = quantidadeUtilizada + quantidadeDesperdicio;

    if (!Number.isFinite(quantidadeUtilizada) || quantidadeUtilizada <= 0) {
      setErro("Informe a quantidade efetivamente utilizada do insumo.");
      return;
    }
    if (!Number.isFinite(quantidadeConsumida) || quantidadeConsumida <= 0) {
      setErro("A baixa total do insumo precisa ser maior que zero.");
      return;
    }

    setSalvandoInsumoRapido(true);
    setErro(null);
    try {
      await vetApi.adicionarProcedimento(buildInsumoProcedimentoPayload({
        consultaIdAtual,
        insumoRapidoSelecionado,
        insumoRapidoForm,
        quantidadeUtilizada,
        quantidadeDesperdicio,
        quantidadeConsumida,
      }));

      setModalInsumoAberto(false);
      setInsumoRapidoSelecionado(null);
      setInsumoRapidoForm(criarInsumoRapidoFormInicial());
      setSucesso("Insumo lançado com sucesso na consulta.");
      await carregarTimelineConsulta();
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Não foi possível lançar o insumo.");
    } finally {
      setSalvandoInsumoRapido(false);
    }
  }

  return {
    abrirFluxoConsulta,
    abrirModalInsumoRapido,
    abrirModalNovoPet,
    finalizar,
    handleNovoPetCriado,
    salvarInsumoRapidoConsulta,
    salvarNovoExameRapido,
    salvarRascunho,
  };
}
