import { vetApi } from "../vetApi";
import {
  buildInsumoProcedimentoPayload,
  buildNovoExamePayload,
  criarInsumoRapidoFormInicial,
  criarNovoExameFormInicial,
} from "./consultaFormState";
import { parseNumero } from "./consultaFormUtils";

export default function useConsultaFluxosActions({
  agendamentoIdQuery,
  carregarTimelineConsulta,
  consultaIdAtual,
  contextoConsultaParams,
  form,
  insumoRapidoForm,
  insumoRapidoSelecionado,
  navigate,
  novoExameArquivo,
  novoExameForm,
  setErro,
  setEtapa,
  setInsumoRapidoForm,
  setInsumoRapidoSelecionado,
  setModalInsumoAberto,
  setModalNovoExameAberto,
  setNovoExameArquivo,
  setNovoExameForm,
  setRefreshExamesToken,
  setSalvandoInsumoRapido,
  setSalvandoNovoExame,
  setSucesso,
}) {
  function abrirModalInsumoRapido() {
    if (!consultaIdAtual) {
      setErro("Salve a consulta primeiro para lancar insumos rapidos.");
      return;
    }
    setInsumoRapidoSelecionado(null);
    setInsumoRapidoForm(criarInsumoRapidoFormInicial());
    setModalInsumoAberto(true);
  }

  function abrirFluxoConsulta(pathname, extras = {}) {
    if (!contextoConsultaParams) {
      setErro("Salve a consulta com um pet valido antes de abrir outro fluxo clinico.");
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
          // O exame fica registrado mesmo se a leitura por IA nao estiver disponivel.
        }
      }

      setModalNovoExameAberto(false);
      setNovoExameForm(criarNovoExameFormInicial());
      setNovoExameArquivo(null);
      setRefreshExamesToken((prev) => prev + 1);
      setSucesso("Exame vinculado a consulta com sucesso.");
      await carregarTimelineConsulta();
      setEtapa(1);
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Nao foi possivel registrar o exame.");
    } finally {
      setSalvandoNovoExame(false);
    }
  }

  async function salvarInsumoRapidoConsulta() {
    if (!consultaIdAtual) {
      setErro("Salve a consulta primeiro para lancar insumos.");
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
      setSucesso("Insumo lancado com sucesso na consulta.");
      await carregarTimelineConsulta();
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Nao foi possivel lancar o insumo.");
    } finally {
      setSalvandoInsumoRapido(false);
    }
  }

  return {
    abrirFluxoConsulta,
    abrirModalInsumoRapido,
    salvarInsumoRapidoConsulta,
    salvarNovoExameRapido,
  };
}
