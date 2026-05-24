import { useState } from 'react';
import {
  CONFERENCIA_STATUS_META,
  calcularConferenciaItem,
  calcularResumoConferencia,
  detectarDivergencias,
  montarConferenciaState,
  normalizarNumeroConferencia,
  obterDraftConferenciaItem,
} from './entradaXmlUtils';

export default function useEntradaXmlConferencia({
  api,
  carregarDados,
  navigate,
  setMostrarDetalhes,
  setTipoRateio,
  sincronizarNotaNaLista,
  toast,
}) {
  const [notaSelecionada, setNotaSelecionada] = useState(null);
  const [mostrarCamposConferencia, setMostrarCamposConferencia] = useState(false);
  const [filtroItensNota, setFiltroItensNota] = useState('todos');
  const [conferenciaItens, setConferenciaItens] = useState({});
  const [conferenciaObservacaoGeral, setConferenciaObservacaoGeral] = useState('');
  const [salvandoConferencia, setSalvandoConferencia] = useState(false);
  const [desfazendoConferencia, setDesfazendoConferencia] = useState(false);
  const [gerandoRascunhoDevolucao, setGerandoRascunhoDevolucao] = useState(false);
  const [criandoPendenciaFornecedor, setCriandoPendenciaFornecedor] = useState(false);
  const [rascunhoDevolucao, setRascunhoDevolucao] = useState(null);
  const [mostrarRascunhoDevolucao, setMostrarRascunhoDevolucao] = useState(false);

  const aplicarNotaSelecionada = (dadosNota) => {
    const notaNormalizada = {
      ...dadosNota,
      itens: [...(dadosNota?.itens || [])].sort((a, b) => a.id - b.id),
    };

    setNotaSelecionada(notaNormalizada);
    setConferenciaItens(montarConferenciaState(notaNormalizada));
    setConferenciaObservacaoGeral(notaNormalizada?.conferencia?.observacao_geral || '');
    setTipoRateio(notaNormalizada.tipo_rateio || 'loja');

    return notaNormalizada;
  };

  const atualizarCampoConferenciaItem = (item, campo, valor) => {
    setConferenciaItens((prev) => {
      const atual = prev[item.id] || obterDraftConferenciaItem(item);
      const quantidadeNF = Number(item.quantidade ?? item.quantidade_nf ?? 0);
      const proximo = { ...atual };

      if (campo === 'quantidade_conferida') {
        proximo.quantidade_conferida = Math.max(
          0,
          Math.min(normalizarNumeroConferencia(valor, atual.quantidade_conferida), quantidadeNF),
        );
        proximo.quantidade_avariada = Math.min(
          Number(proximo.quantidade_avariada || 0),
          Math.max(0, quantidadeNF - proximo.quantidade_conferida),
        );
      } else if (campo === 'quantidade_avariada') {
        proximo.quantidade_avariada = Math.max(
          0,
          Math.min(
            normalizarNumeroConferencia(valor, atual.quantidade_avariada),
            Math.max(0, quantidadeNF - Number(proximo.quantidade_conferida ?? atual.quantidade_conferida ?? quantidadeNF)),
          ),
        );
      } else if (campo === 'observacao_conferencia') {
        proximo.observacao_conferencia = String(valor ?? '');
      } else if (campo === 'acao_sugerida') {
        proximo.acao_sugerida = valor || 'sem_acao';
      }

      const conferenciaItem = calcularConferenciaItem(item, proximo);
      if (!conferenciaItem.temDivergencia) {
        proximo.acao_sugerida = 'sem_acao';
      } else if (!proximo.acao_sugerida || proximo.acao_sugerida === 'sem_acao') {
        proximo.acao_sugerida = conferenciaItem.quantidadeAvariada > 0
          ? 'nf_devolucao'
          : 'contatar_fornecedor';
      }

      return {
        ...prev,
        [item.id]: proximo,
      };
    });
  };

  const construirPayloadConferencia = () => {
    if (!notaSelecionada) return null;

    return {
      observacao_geral: conferenciaObservacaoGeral || null,
      itens: notaSelecionada.itens.map((item) => {
        const conferenciaItem = calcularConferenciaItem(item, conferenciaItens[item.id]);
        return {
          item_id: item.id,
          quantidade_conferida: conferenciaItem.quantidadeConferida,
          quantidade_avariada: conferenciaItem.quantidadeAvariada,
          observacao_conferencia: conferenciaItem.observacaoConferencia || null,
          acao_sugerida: conferenciaItem.acaoSugerida,
        };
      }),
    };
  };

  const salvarConferenciaAtual = async ({ silencioso = false } = {}) => {
    if (!notaSelecionada) return false;

    setSalvandoConferencia(true);
    try {
      const payload = construirPayloadConferencia();
      await api.post(`/notas-entrada/${notaSelecionada.id}/conferencia`, payload);
      const notaResponse = await api.get(`/notas-entrada/${notaSelecionada.id}`);
      const notaAtualizada = aplicarNotaSelecionada(notaResponse.data);
      sincronizarNotaNaLista(notaAtualizada);
      await carregarDados();

      if (!silencioso) {
        toast.success('Conferencia salva com sucesso');
      }

      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar conferencia');
      return false;
    } finally {
      setSalvandoConferencia(false);
    }
  };

  const desfazerConferenciaAtual = async () => {
    if (!notaSelecionada) return false;

    const confirmou = window.confirm('Deseja desfazer a conferencia desta NF e voltar para o estado nao conferido?');
    if (!confirmou) {
      return false;
    }

    setDesfazendoConferencia(true);
    try {
      await api.post(`/notas-entrada/${notaSelecionada.id}/conferencia/desfazer`);
      const notaResponse = await api.get(`/notas-entrada/${notaSelecionada.id}`);
      const notaAtualizada = aplicarNotaSelecionada(notaResponse.data);
      sincronizarNotaNaLista(notaAtualizada);
      setMostrarCamposConferencia(false);
      await carregarDados();
      toast.success('Conferencia desfeita com sucesso');
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao desfazer conferencia');
      return false;
    } finally {
      setDesfazendoConferencia(false);
    }
  };

  const resumoConferenciaAtual = notaSelecionada
    ? calcularResumoConferencia(notaSelecionada, conferenciaItens)
    : null;

  const gerarRascunhoDevolucao = async () => {
    if (!notaSelecionada) return;

    if (notaSelecionada.status === 'pendente') {
      const conferenciaSalva = await salvarConferenciaAtual({ silencioso: true });
      if (!conferenciaSalva) return;
    }

    setGerandoRascunhoDevolucao(true);
    try {
      const { data } = await api.get(`/notas-entrada/${notaSelecionada.id}/devolucao-draft`);
      setRascunhoDevolucao(data);
      setMostrarRascunhoDevolucao(true);

      if (data.disponivel) {
        toast.success('Rascunho de NF de devolucao gerado');
      } else {
        toast('Nao ha itens avariados para NF de devolucao');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao gerar rascunho da NF de devolucao');
    } finally {
      setGerandoRascunhoDevolucao(false);
    }
  };

  const gerarPendenciaFornecedor = async () => {
    if (!notaSelecionada) return;

    if ((resumoConferenciaAtual?.itens_com_divergencia || 0) <= 0) {
      toast.error('Nao ha divergencias para acompanhar com o fornecedor');
      return;
    }

    if (notaSelecionada.status === 'pendente') {
      const conferenciaSalva = await salvarConferenciaAtual({ silencioso: true });
      if (!conferenciaSalva) return;
    }

    setCriandoPendenciaFornecedor(true);
    try {
      const { data } = await api.post(`/compras-pendencias/notas/${notaSelecionada.id}`, {});
      toast.success(`Pendencia ${data?.codigo || ''} criada para acompanhamento`);

      const abrirPendencias = window.confirm(
        'Pendencia criada com relatorio e texto de e-mail sugerido. Deseja abrir a tela de pendencias agora?'
      );

      if (abrirPendencias) {
        setMostrarDetalhes(false);
        navigate('/compras/pendencias');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao criar pendencia do fornecedor');
    } finally {
      setCriandoPendenciaFornecedor(false);
    }
  };

  const metaConferenciaAtual = CONFERENCIA_STATUS_META[resumoConferenciaAtual?.status || 'nao_iniciada'];
  const itensNotaDetalhe = notaSelecionada?.itens || [];
  const itensComDivergenciaDetalhe = itensNotaDetalhe.filter((item) => {
    const conferenciaItem = calcularConferenciaItem(item, conferenciaItens[item.id]);
    const divergenciasCadastro = detectarDivergencias(item);
    return Boolean(item.tem_divergencia) || conferenciaItem.temDivergencia || divergenciasCadastro.length > 0;
  });
  const itensExibidosNota = filtroItensNota === 'divergencias' && itensComDivergenciaDetalhe.length > 0
    ? itensComDivergenciaDetalhe
    : itensNotaDetalhe;

  return {
    aplicarNotaSelecionada,
    atualizarCampoConferenciaItem,
    conferenciaItens,
    conferenciaObservacaoGeral,
    criandoPendenciaFornecedor,
    desfazendoConferencia,
    desfazerConferenciaAtual,
    filtroItensNota,
    gerandoRascunhoDevolucao,
    gerarPendenciaFornecedor,
    gerarRascunhoDevolucao,
    itensComDivergenciaDetalhe,
    itensExibidosNota,
    itensNotaDetalhe,
    metaConferenciaAtual,
    mostrarCamposConferencia,
    mostrarRascunhoDevolucao,
    notaSelecionada,
    rascunhoDevolucao,
    resumoConferenciaAtual,
    salvandoConferencia,
    salvarConferenciaAtual,
    setConferenciaObservacaoGeral,
    setFiltroItensNota,
    setMostrarCamposConferencia,
    setMostrarRascunhoDevolucao,
    setNotaSelecionada,
  };
}
