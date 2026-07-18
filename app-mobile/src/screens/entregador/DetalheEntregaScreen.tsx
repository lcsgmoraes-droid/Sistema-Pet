import { RouteProp, useNavigation, useRoute } from "@react-navigation/native";
import * as Location from "expo-location";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "react-native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { DetalheEntregaContent } from "./detalhe/DetalheEntregaContent";
import {
  extrairPosicaoOrdem,
  obterLocalizacaoOpcional,
  obterMensagemErro,
  reordenarParadasPorPosicao,
  rotaPermiteReordenacao,
  type FormaRecebimento,
  type Parada,
  type Rota,
  type VendaDetalhes,
} from "./detalhe/DetalheEntregaUtils";
import api from "../../services/api";
import {
  iniciarRastreamentoEntregaEmSegundoPlano,
  pararRastreamentoEntregaEmSegundoPlano,
} from "../../services/deliveryLocationTracking";
import { EntregadorStackParamList } from "../../types/entregadorNavigation";

type RouteProps = RouteProp<EntregadorStackParamList, "DetalheEntrega">;
type Nav = NativeStackNavigationProp<EntregadorStackParamList, "DetalheEntrega">;

export default function DetalheEntregaScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<RouteProps>();
  const { rotaId, numero } = route.params;

  const [rota, setRota] = useState<Rota | null>(null);
  const [loading, setLoading] = useState(true);
  const [processando, setProcessando] = useState<number | null>(null); // parada id em processamento
  const [modalRecebimentoAberto, setModalRecebimentoAberto] = useState(false);
  const [paradaRecebimentoId, setParadaRecebimentoId] = useState<number | null>(
    null,
  );
  const [formaRecebimento, setFormaRecebimento] = useState<FormaRecebimento>("pix");
  const [parcelasRecebimento, setParcelasRecebimento] = useState(1);
  const [processandoRecebimento, setProcessandoRecebimento] = useState(false);
  const [processandoFinalizacao, setProcessandoFinalizacao] = useState(false);
  const [modalVendaAberto, setModalVendaAberto] = useState(false);
  const [loadingVenda, setLoadingVenda] = useState(false);
  const [vendaDetalhes, setVendaDetalhes] = useState<VendaDetalhes | null>(null);
  const [modalOrdemAberto, setModalOrdemAberto] = useState(false);
  const [paradaOrdemEmEdicao, setParadaOrdemEmEdicao] = useState<Parada | null>(null);
  const [novaOrdemTexto, setNovaOrdemTexto] = useState("");
  const [salvandoOrdemManual, setSalvandoOrdemManual] = useState(false);
  const [modalNaoEntregueAberto, setModalNaoEntregueAberto] = useState(false);
  const [paradaNaoEntregueId, setParadaNaoEntregueId] = useState<number | null>(null);
  const [motivoNaoEntregue, setMotivoNaoEntregue] = useState("");
  const localizacaoSubscriptionRef = useRef<Location.LocationSubscription | null>(null);
  const enviandoLocalizacaoRef = useRef(false);

  const paradasPendentes =
    rota?.paradas?.filter((p) => p.status === "pendente").length ?? 0;
  const intervaloLocalizacaoMs = paradasPendentes <= 2 ? 4000 : 7000;
  const distanciaLocalizacaoM = paradasPendentes <= 2 ? 8 : 15;

  const carregar = useCallback(async (mostrarErro = true): Promise<Rota | null> => {
    try {
      const { data } = await api.get<Rota>(`/ecommerce/entregador/rotas/${rotaId}`);
      let r: Rota = data;
      if (r.paradas) {
        r = { ...r, paradas: [...r.paradas].sort((a, b) => a.ordem - b.ordem) };
      }
      setRota(r);
      return r;
    } catch {
      if (mostrarErro) {
        Alert.alert("Erro", "Nao foi possivel carregar a rota.");
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, [rotaId]);

  useEffect(() => {
    navigation.setOptions({ title: `Rota #${numero}` });
    carregar();
  }, [carregar, navigation, numero]);

  const voltarParaListaComRotaFinalizada = useCallback(() => {
    navigation.navigate("MinhasRotas", {
      rotaFinalizadaId: rota?.id ?? rotaId,
      refreshKey: Date.now(),
    });
  }, [navigation, rota?.id, rotaId]);

  useEffect(() => {
    if (!rota || !["em_rota", "em_andamento"].includes(rota.status)) {
      localizacaoSubscriptionRef.current?.remove();
      localizacaoSubscriptionRef.current = null;
      void pararRastreamentoEntregaEmSegundoPlano(rotaId);
      return;
    }

    let ativo = true;

    const enviarLocalizacaoAtual = async (
      coords: Pick<Location.LocationObjectCoords, "latitude" | "longitude">,
    ) => {
      try {
        if (!ativo || enviandoLocalizacaoRef.current) return;
        enviandoLocalizacaoRef.current = true;

        await api.post(
          `/ecommerce/entregador/rotas/${rotaId}/atualizar-localizacao`,
          {},
          {
            params: {
              lat: coords.latitude,
              lon: coords.longitude,
            },
          },
        );
      } catch {
        // Não interrompe a tela se GPS/rede falhar momentaneamente.
      }
      enviandoLocalizacaoRef.current = false;
    };

    const iniciar = async () => {
      const rastreioEmSegundoPlano =
        await iniciarRastreamentoEntregaEmSegundoPlano(rotaId);
      if (rastreioEmSegundoPlano || !ativo) return;

      try {
        const permissao = await Location.getForegroundPermissionsAsync();
        if (!permissao.granted) {
          await Location.requestForegroundPermissionsAsync();
        }
      } catch {
        // Permissão opcional para operação da tela.
      }

      try {
        const posicaoInicial = await Location.getCurrentPositionAsync({
          accuracy:
            paradasPendentes <= 2
              ? Location.Accuracy.High
              : Location.Accuracy.Balanced,
        });

        if (ativo) {
          await enviarLocalizacaoAtual(posicaoInicial.coords);
        }
      } catch {
        // Segue com o watch mesmo sem ponto inicial.
      }

      try {
        localizacaoSubscriptionRef.current = await Location.watchPositionAsync(
          {
            accuracy:
              paradasPendentes <= 2
                ? Location.Accuracy.High
                : Location.Accuracy.Balanced,
            timeInterval: intervaloLocalizacaoMs,
            distanceInterval: distanciaLocalizacaoM,
            mayShowUserSettingsDialog: true,
          },
          (posicao) => {
            void enviarLocalizacaoAtual(posicao.coords);
          },
        );
      } catch {
        // Se o GPS estiver bloqueado, a tela continua funcional.
      }
    };

    void iniciar();

    return () => {
      ativo = false;
      localizacaoSubscriptionRef.current?.remove();
      localizacaoSubscriptionRef.current = null;
    };
  }, [rota, rotaId, intervaloLocalizacaoMs, distanciaLocalizacaoM, paradasPendentes]);

  // ── Ações nas paradas ─────────────────────────────────────────────────────

  async function marcarEntregue(paradaId: number) {
    if (rota?.status === "pendente") {
      Alert.alert(
        "Rota ainda nao iniciada",
        "Toque em Iniciar Rota antes de confirmar uma entrega.",
      );
      return;
    }

    setProcessando(paradaId);
    try {
      const localizacao = await obterLocalizacaoOpcional();

      await api.post(
        `/ecommerce/entregador/rotas/${rotaId}/paradas/${paradaId}/marcar-entregue`,
        {},
        {
          params: {
            lat_entrega: localizacao.latitude,
            lon_entrega: localizacao.longitude,
          },
        },
      );
      const rastreioEmSegundoPlano =
        await iniciarRastreamentoEntregaEmSegundoPlano(rotaId);
      if (!rastreioEmSegundoPlano) {
        Alert.alert(
          "Rastreamento em segundo plano",
          "A rota foi iniciada, mas o acompanhamento continua somente enquanto esta tela estiver aberta. Para acompanhar ao abrir o mapa, permita a localizacao sempre.",
        );
      }
      await carregar();
    } catch (error) {
      const rotaAtualizada = await carregar(false);
      const paradaAtualizada = rotaAtualizada?.paradas.find((p) => p.id === paradaId);
      if (paradaAtualizada?.status === "entregue") {
        return;
      }

      Alert.alert(
        "Entrega nao concluida",
        obterMensagemErro(error, "Nao foi possivel marcar como entregue agora."),
      );
    } finally {
      setProcessando(null);
    }
  }

  function marcarNaoEntregue(paradaId: number) {
    setParadaNaoEntregueId(paradaId);
    setMotivoNaoEntregue("");
    setModalNaoEntregueAberto(true);
  }

  function limparModalNaoEntregue() {
    setModalNaoEntregueAberto(false);
    setParadaNaoEntregueId(null);
    setMotivoNaoEntregue("");
  }

  function fecharModalNaoEntregue() {
    if (processando === paradaNaoEntregueId) return;
    limparModalNaoEntregue();
  }

  async function confirmarNaoEntregue() {
    if (!paradaNaoEntregueId) return;

    const paradaId = paradaNaoEntregueId;
    setProcessando(paradaId);
    try {
      await api.post(
        `/ecommerce/entregador/rotas/${rotaId}/paradas/${paradaId}/nao-entregue`,
        {},
        {
          params: {
            motivo: motivoNaoEntregue.trim() || undefined,
          },
        },
      );
      limparModalNaoEntregue();
      await carregar();
    } catch {
      Alert.alert("Erro", "Nao foi possivel registrar a ocorrencia.");
    } finally {
      setProcessando(null);
    }
  }

  async function iniciarRota() {
    try {
      const localizacao = await obterLocalizacaoOpcional();
      await api.post(
        `/ecommerce/entregador/rotas/${rotaId}/iniciar`,
        {},
        {
          params: {
            lat_inicio: localizacao.latitude,
            lon_inicio: localizacao.longitude,
          },
        },
      );
      await carregar();
    } catch (error) {
      const rotaAtualizada = await carregar(false);
      if (rotaAtualizada && rotaAtualizada.status !== "pendente") {
        Alert.alert("Rota iniciada", "A rota ja esta em andamento.");
        return;
      }

      Alert.alert(
        "Rota nao iniciada",
        obterMensagemErro(error, "Nao foi possivel iniciar a rota agora."),
      );
    }
  }

  async function moverParada(paradaId: number, direcao: "up" | "down") {
    if (!rota || !rotaPermiteReordenacao(rota.status)) return;

    const ordenadas = [...rota.paradas].sort((a, b) => a.ordem - b.ordem);
    const idx = ordenadas.findIndex((p) => p.id === paradaId);
    if (idx < 0) return;

    const alvo = direcao === "up" ? idx - 1 : idx + 1;
    if (alvo < 0 || alvo >= ordenadas.length) return;

    const tmp = ordenadas[idx];
    ordenadas[idx] = ordenadas[alvo];
    ordenadas[alvo] = tmp;

    try {
      await api.put(`/ecommerce/entregador/rotas/${rotaId}/paradas/reordenar`, {
        parada_ids: ordenadas.map((p) => p.id),
      });
      const atualizadas = ordenadas.map((p, index) => ({ ...p, ordem: index + 1 }));
      setRota((prev) => (prev ? { ...prev, paradas: atualizadas } : prev));
    } catch {
      Alert.alert("Erro", "Não foi possível reordenar as paradas.");
    }
  }

  async function salvarNovaOrdemParadas(paradasOrdenadas: Parada[]) {
    if (!rotaPermiteReordenacao(rota?.status)) {
      Alert.alert("Rota encerrada", "Nao e possivel reordenar uma rota encerrada.");
      return false;
    }

    try {
      await api.put(`/ecommerce/entregador/rotas/${rotaId}/paradas/reordenar`, {
        parada_ids: paradasOrdenadas.map((p) => p.id),
      });
      const atualizadas = paradasOrdenadas.map((p, index) => ({
        ...p,
        ordem: index + 1,
      }));
      setRota((prev) => (prev ? { ...prev, paradas: atualizadas } : prev));
      return true;
    } catch {
      Alert.alert("Erro", "Não foi possível salvar a nova ordem das paradas.");
      await carregar();
      return false;
    }
  }

  function abrirModalOrdem(parada: Parada) {
    if (!rotaPermiteReordenacao(rota?.status)) return;
    setParadaOrdemEmEdicao(parada);
    setNovaOrdemTexto(`n${parada.ordem}`);
    setModalOrdemAberto(true);
  }

  function fecharModalOrdem() {
    if (salvandoOrdemManual) return;
    setModalOrdemAberto(false);
    setParadaOrdemEmEdicao(null);
    setNovaOrdemTexto("");
  }

  async function confirmarNovaOrdemManual() {
    if (!rota || !paradaOrdemEmEdicao) return;

    const novaPosicao = extrairPosicaoOrdem(novaOrdemTexto);
    if (!Number.isFinite(novaPosicao)) {
      Alert.alert("Posição inválida", "Digite um número válido para reordenar a entrega.");
      return;
    }

    const ordenadas = reordenarParadasPorPosicao(
      rota.paradas,
      paradaOrdemEmEdicao.id,
      novaPosicao,
    );

    if (!ordenadas) {
      Alert.alert("Erro", "Não foi possível localizar essa parada para reordenar.");
      return;
    }

    setSalvandoOrdemManual(true);
    const salvou = await salvarNovaOrdemParadas(ordenadas);
    setSalvandoOrdemManual(false);

    if (salvou) {
      fecharModalOrdem();
    }
  }

  async function finalizarRota() {
    const confirmarFinalizacao = async () => {
      setProcessandoFinalizacao(true);
      try {
        await api.post(`/ecommerce/entregador/rotas/${rotaId}/fechar`, {
          tentativas: 1,
        });
        await pararRastreamentoEntregaEmSegundoPlano(rotaId);
        await carregar(false);
        Alert.alert('Sucesso', 'Rota finalizada com sucesso.', [
          { text: 'OK', onPress: voltarParaListaComRotaFinalizada },
        ]);
      } catch (error) {
        const rotaAtualizada = await carregar(false);
        if (rotaAtualizada?.status === "concluida") {
          await pararRastreamentoEntregaEmSegundoPlano(rotaId);
          Alert.alert('Sucesso', 'Rota finalizada com sucesso.', [
            { text: 'OK', onPress: voltarParaListaComRotaFinalizada },
          ]);
          return;
        }

        Alert.alert(
          'Erro',
          obterMensagemErro(error, 'Nao foi possivel finalizar a rota agora.'),
        );
      } finally {
        setProcessandoFinalizacao(false);
      }
    };

    Alert.alert(
      'Finalizar rota',
      'Confirmar finalização da rota? Essa ação conclui a rota no ERP.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Finalizar',
          onPress: () => {
            void confirmarFinalizacao();
          },
        },
      ],
    );
  }

  async function abrirDetalhesVenda(vendaId: number) {
    setLoadingVenda(true);
    setModalVendaAberto(true);
    try {
      const { data } = await api.get<VendaDetalhes>(
        `/ecommerce/entregador/vendas/${vendaId}/detalhes`,
      );
      setVendaDetalhes(data);
    } catch {
      setModalVendaAberto(false);
      Alert.alert('Erro', 'Não foi possível carregar os detalhes da venda.');
    } finally {
      setLoadingVenda(false);
    }
  }

  function abrirModalRecebimento(paradaId: number) {
    setParadaRecebimentoId(paradaId);
    setFormaRecebimento("pix");
    setParcelasRecebimento(1);
    setModalRecebimentoAberto(true);
  }

  async function registrarRecebimento() {
    if (!paradaRecebimentoId) return;
    setProcessandoRecebimento(true);
    try {
      await api.post(
        `/ecommerce/entregador/rotas/${rotaId}/paradas/${paradaRecebimentoId}/registrar-recebimento`,
        {
          forma_pagamento: formaRecebimento,
          numero_parcelas:
            formaRecebimento === "cartao_credito" ? parcelasRecebimento : 1,
        },
      );

      Alert.alert(
        "Recebimento registrado",
        "Registrado como pendente de integração com a operadora/maquininha.",
      );
      setModalRecebimentoAberto(false);
      await carregar();
    } catch {
      Alert.alert("Erro", "Não foi possível registrar o recebimento agora.");
    } finally {
      setProcessandoRecebimento(false);
    }
  }

  // ── Render parada ─────────────────────────────────────────────────────────

  return (
    <DetalheEntregaContent
      loading={loading}
      rota={rota}
      processando={processando}
      processandoFinalizacao={processandoFinalizacao}
      iniciarRota={iniciarRota}
      finalizarRota={finalizarRota}
      salvarNovaOrdemParadas={salvarNovaOrdemParadas}
      abrirModalOrdem={abrirModalOrdem}
      abrirModalRecebimento={abrirModalRecebimento}
      abrirDetalhesVenda={abrirDetalhesVenda}
      marcarEntregue={marcarEntregue}
      marcarNaoEntregue={marcarNaoEntregue}
      modalOrdemAberto={modalOrdemAberto}
      paradaOrdemEmEdicao={paradaOrdemEmEdicao}
      novaOrdemTexto={novaOrdemTexto}
      setNovaOrdemTexto={setNovaOrdemTexto}
      salvandoOrdemManual={salvandoOrdemManual}
      fecharModalOrdem={fecharModalOrdem}
      confirmarNovaOrdemManual={confirmarNovaOrdemManual}
      modalNaoEntregueAberto={modalNaoEntregueAberto}
      paradaNaoEntregueId={paradaNaoEntregueId}
      motivoNaoEntregue={motivoNaoEntregue}
      setMotivoNaoEntregue={setMotivoNaoEntregue}
      fecharModalNaoEntregue={fecharModalNaoEntregue}
      confirmarNaoEntregue={confirmarNaoEntregue}
      modalRecebimentoAberto={modalRecebimentoAberto}
      setModalRecebimentoAberto={setModalRecebimentoAberto}
      formaRecebimento={formaRecebimento}
      setFormaRecebimento={setFormaRecebimento}
      parcelasRecebimento={parcelasRecebimento}
      setParcelasRecebimento={setParcelasRecebimento}
      processandoRecebimento={processandoRecebimento}
      registrarRecebimento={registrarRecebimento}
      modalVendaAberto={modalVendaAberto}
      setModalVendaAberto={setModalVendaAberto}
      loadingVenda={loadingVenda}
      vendaDetalhes={vendaDetalhes}
    />
  );
}
