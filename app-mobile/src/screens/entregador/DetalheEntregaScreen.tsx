import { RouteProp, useNavigation, useRoute } from "@react-navigation/native";
import * as Location from "expo-location";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import DraggableFlatList, {
  RenderItemParams,
} from "react-native-draggable-flatlist";
import api from "../../services/api";
import { EntregadorStackParamList } from "../../types/entregadorNavigation";

// ─── Tipos ───────────────────────────────────────────────────────────────────

interface Parada {
  id: number;
  venda_id: number;
  ordem: number;
  endereco: string;
  status: string; // pendente | entregue | nao_entregue
  cliente_nome?: string;
  cliente_telefone?: string;
  cliente_celular?: string;
  observacoes?: string;
  data_entrega?: string;
}

interface Rota {
  id: number;
  numero: string;
  status: string;
  paradas: Parada[];
}

interface VendaDetalhes {
  id: number;
  cliente?: {
    nome?: string;
    telefone?: string;
    celular?: string;
  };
  data_venda?: string;
  forma_pagamento?: string;
  status_pagamento?: string;
  endereco_entrega?: string;
  total?: number;
  valor_total?: number;
  itens?: Array<{
    produto_nome?: string;
    servico_descricao?: string;
    quantidade?: number;
    subtotal?: number;
    preco_unitario?: number;
  }>;
}

type RouteProps = RouteProp<EntregadorStackParamList, "DetalheEntrega">;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function abrirMapa(endereco: string) {
  const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(endereco)}`;
  Linking.openURL(url).catch(() =>
    Alert.alert("Erro", "Não foi possível abrir o mapa."),
  );
}

function ligar(telefone?: string | null) {
  if (!telefone) return;
  const digits = telefone.replaceAll(/\D/g, "");
  Linking.openURL(`tel:${digits}`).catch(() =>
    Alert.alert("Erro", "Não foi possível ligar."),
  );
}

const STATUS_BADGE: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  pendente: { label: "Pendente", color: "#92400e", bg: "#fef3c7" },
  entregue: { label: "Entregue ✓", color: "#065f46", bg: "#d1fae5" },
  nao_entregue: { label: "Não entregue ✗", color: "#7f1d1d", bg: "#fee2e2" },
};

// ─── Componente ──────────────────────────────────────────────────────────────

export default function DetalheEntregaScreen() {
  const navigation = useNavigation();
  const route = useRoute<RouteProps>();
  const { rotaId, numero } = route.params;

  const [rota, setRota] = useState<Rota | null>(null);
  const [loading, setLoading] = useState(true);
  const [processando, setProcessando] = useState<number | null>(null); // parada id em processamento
  const [modalRecebimentoAberto, setModalRecebimentoAberto] = useState(false);
  const [paradaRecebimentoId, setParadaRecebimentoId] = useState<number | null>(
    null,
  );
  const [formaRecebimento, setFormaRecebimento] = useState<
    "pix" | "cartao_debito" | "cartao_credito"
  >("pix");
  const [parcelasRecebimento, setParcelasRecebimento] = useState(1);
  const [processandoRecebimento, setProcessandoRecebimento] = useState(false);
  const [processandoFinalizacao, setProcessandoFinalizacao] = useState(false);
  const [modalVendaAberto, setModalVendaAberto] = useState(false);
  const [loadingVenda, setLoadingVenda] = useState(false);
  const [vendaDetalhes, setVendaDetalhes] = useState<VendaDetalhes | null>(null);

  const paradasPendentes =
    rota?.paradas?.filter((p) => p.status === "pendente").length ?? 0;
  const intervaloLocalizacaoMs = paradasPendentes <= 2 ? 5000 : 10000;

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.get<Rota>(`/rotas-entrega/${rotaId}`);
      let r: Rota = data;
      if (r.paradas) {
        r = { ...r, paradas: [...r.paradas].sort((a, b) => a.ordem - b.ordem) };
      }
      setRota(r);
    } catch {
      Alert.alert("Erro", "Não foi possível carregar a rota.");
    } finally {
      setLoading(false);
    }
  }, [rotaId]);

  useEffect(() => {
    navigation.setOptions({ title: `Rota #${numero}` });
    carregar();
  }, [carregar, navigation, numero]);

  useEffect(() => {
    if (!rota || !["em_rota", "em_andamento"].includes(rota.status)) {
      return;
    }

    let ativo = true;
    let timer: ReturnType<typeof setInterval> | null = null;

    const enviarLocalizacaoAtual = async () => {
      try {
        const permissao = await Location.getForegroundPermissionsAsync();
        if (!permissao.granted) return;

        const posicao = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });

        if (!ativo) return;

        await api.post(
          `/rotas-entrega/${rotaId}/atualizar-localizacao`,
          {},
          {
            params: {
              lat: posicao.coords.latitude,
              lon: posicao.coords.longitude,
            },
          },
        );
      } catch {
        // Não interrompe a tela se GPS/rede falhar momentaneamente.
      }
    };

    const iniciar = async () => {
      try {
        const permissao = await Location.getForegroundPermissionsAsync();
        if (!permissao.granted) {
          await Location.requestForegroundPermissionsAsync();
        }
      } catch {
        // Permissão opcional para operação da tela.
      }

      await enviarLocalizacaoAtual();
      timer = setInterval(enviarLocalizacaoAtual, intervaloLocalizacaoMs);
    };

    iniciar();

    return () => {
      ativo = false;
      if (timer) clearInterval(timer);
    };
  }, [rota, rotaId, intervaloLocalizacaoMs]);

  // ── Ações nas paradas ─────────────────────────────────────────────────────

  async function marcarEntregue(paradaId: number) {
    setProcessando(paradaId);
    try {
      let latEntrega: number | undefined;
      let lonEntrega: number | undefined;

      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === "granted") {
          const posicao = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          });
          latEntrega = posicao.coords.latitude;
          lonEntrega = posicao.coords.longitude;
        }
      } catch {
        // GPS é opcional: a entrega continua mesmo sem coordenadas.
      }

      await api.post(
        `/rotas-entrega/${rotaId}/paradas/${paradaId}/marcar-entregue`,
        {},
        {
          params: {
            lat_entrega: latEntrega,
            lon_entrega: lonEntrega,
          },
        },
      );
      await carregar();
    } catch {
      Alert.alert("Erro", "Não foi possível marcar como entregue.");
    } finally {
      setProcessando(null);
    }
  }

  async function marcarNaoEntregue(paradaId: number) {
    Alert.prompt(
      "Motivo",
      "Descreva o motivo da não entrega (opcional):",
      async (motivo) => {
        setProcessando(paradaId);
        try {
          await api.post(
            `/rotas-entrega/${rotaId}/paradas/${paradaId}/nao-entregue`,
            {
              motivo: motivo || "",
            },
          );
          await carregar();
        } catch {
          Alert.alert("Erro", "Não foi possível registrar a ocorrência.");
        } finally {
          setProcessando(null);
        }
      },
      "plain-text",
      "",
    );
  }

  async function iniciarRota() {
    try {
      await api.post(`/rotas-entrega/${rotaId}/iniciar`, {});
      await carregar();
    } catch {
      Alert.alert("Erro", "Não foi possível iniciar a rota.");
    }
  }

  async function moverParada(paradaId: number, direcao: "up" | "down") {
    if (rota?.status !== "pendente") return;

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
    try {
      await api.put(`/ecommerce/entregador/rotas/${rotaId}/paradas/reordenar`, {
        parada_ids: paradasOrdenadas.map((p) => p.id),
      });
      const atualizadas = paradasOrdenadas.map((p, index) => ({
        ...p,
        ordem: index + 1,
      }));
      setRota((prev) => (prev ? { ...prev, paradas: atualizadas } : prev));
    } catch {
      Alert.alert("Erro", "Não foi possível salvar a nova ordem das paradas.");
      await carregar();
    }
  }

  async function finalizarRota() {
    const confirmarFinalizacao = async () => {
      setProcessandoFinalizacao(true);
      try {
        await api.post(`/rotas-entrega/${rotaId}/fechar`, {});
        Alert.alert('Sucesso', 'Rota finalizada com sucesso.');
        await carregar();
      } catch {
        Alert.alert('Erro', 'Não foi possível finalizar a rota agora.');
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
        `/rotas-entrega/${rotaId}/paradas/${paradaRecebimentoId}/registrar-recebimento`,
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

  function renderParada(parada: Parada, drag?: () => void, isActive?: boolean) {
    const badge = STATUS_BADGE[parada.status] ?? {
      label: parada.status,
      color: "#374151",
      bg: "#f3f4f6",
    };
    const emProcessamento = processando === parada.id;

    return (
      <View
        key={parada.id}
        style={[styles.paradaCard, isActive ? styles.paradaCardAtiva : styles.paradaCardInativa]}
      >
        {/* Cabeçalho */}
        <View style={styles.paradaHeader}>
          <View style={styles.ordemCircle}>
            <Text style={styles.ordemText}>{parada.ordem}</Text>
          </View>
          <View style={styles.paradaInfo}>
            <Text style={styles.paradaCliente} numberOfLines={1}>
              {parada.cliente_nome ?? `Cliente da venda #${parada.venda_id}`}
            </Text>
            <Text style={styles.paradaEndereco} numberOfLines={2}>
              {parada.endereco}
            </Text>
          </View>
          {rota?.status === "pendente" && drag ? (
            <TouchableOpacity
              style={[styles.btnDrag, isActive && styles.btnDragAtivo]}
              onLongPress={drag}
              delayLongPress={120}
            >
              <Text style={styles.btnDragText}>☰</Text>
            </TouchableOpacity>
          ) : null}
          <View style={[styles.statusBadge, { backgroundColor: badge.bg }]}>
            <Text style={[styles.statusBadgeText, { color: badge.color }]}>
              {badge.label}
            </Text>
          </View>
        </View>

        {/* Observações (se houver) */}
        {!!parada.observacoes && (
          <Text style={styles.observacoes}>📝 {parada.observacoes}</Text>
        )}

        {/* Botões de ação */}
        <View style={styles.paradaBotoes}>
          <TouchableOpacity
            style={styles.btnMapa}
            onPress={() => abrirMapa(parada.endereco)}
          >
            <Text style={styles.btnMapaText}>📍 Navegar</Text>
          </TouchableOpacity>

          {parada.cliente_telefone || parada.cliente_celular ? (
            <TouchableOpacity
              style={styles.btnLigar}
              onPress={() =>
                ligar(parada.cliente_celular ?? parada.cliente_telefone)
              }
            >
              <Text style={styles.btnLigarText}>📞 Ligar</Text>
            </TouchableOpacity>
          ) : null}

          <TouchableOpacity
            style={styles.btnRecebimento}
            onPress={() => abrirModalRecebimento(parada.id)}
          >
            <Text style={styles.btnRecebimentoText}>💳 Recebimento</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.btnDetalhes}
            onPress={() => abrirDetalhesVenda(parada.venda_id)}
          >
            <Text style={styles.btnDetalhesText}>📄 Detalhes</Text>
          </TouchableOpacity>
        </View>

        {/* Ações de entrega — só mostrar se ainda estiver pendente */}
        {parada.status === "pendente" && (
          <View style={styles.paradaAcoes}>
            {emProcessamento ? (
              <ActivityIndicator color="#2563eb" />
            ) : (
              <>
                <TouchableOpacity
                  style={styles.btnEntregue}
                  onPress={() => marcarEntregue(parada.id)}
                >
                  <Text style={styles.btnEntregueText}>✅ Entregue</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.btnNaoEntregue}
                  onPress={() => marcarNaoEntregue(parada.id)}
                >
                  <Text style={styles.btnNaoEntregueText}>❌ Não entregue</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        )}
      </View>
    );
  }

  // ── Tela ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  if (!rota) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Rota não encontrada.</Text>
      </View>
    );
  }

  const pendentes = rota.paradas.filter((p) => p.status === "pendente").length;
  const entregues = rota.paradas.filter((p) => p.status === "entregue").length;
  const podeFinalizar =
    ["em_rota", "em_andamento"].includes(rota.status) &&
    rota.paradas.length > 0 &&
    pendentes === 0;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Resumo */}
      <View style={styles.resumo}>
        <View style={styles.resumoItem}>
          <Text style={styles.resumoValor}>{rota.paradas.length}</Text>
          <Text style={styles.resumoLabel}>Total</Text>
        </View>
        <View style={styles.resumoItem}>
          <Text style={[styles.resumoValor, { color: "#f59e0b" }]}>
            {pendentes}
          </Text>
          <Text style={styles.resumoLabel}>Pendentes</Text>
        </View>
        <View style={styles.resumoItem}>
          <Text style={[styles.resumoValor, { color: "#10b981" }]}>
            {entregues}
          </Text>
          <Text style={styles.resumoLabel}>Entregues</Text>
        </View>
      </View>

      {/* Botão iniciar rota (só se pendente) */}
      {rota.status === "pendente" && (
        <TouchableOpacity style={styles.btnIniciar} onPress={iniciarRota}>
          <Text style={styles.btnIniciarText}>▶ Iniciar Rota</Text>
        </TouchableOpacity>
      )}

      {podeFinalizar && (
        <TouchableOpacity
          style={[styles.btnFinalizar, processandoFinalizacao && { opacity: 0.6 }]}
          disabled={processandoFinalizacao}
          onPress={finalizarRota}
        >
          <Text style={styles.btnFinalizarText}>
            {processandoFinalizacao ? 'Finalizando...' : '✅ Finalizar Rota'}
          </Text>
        </TouchableOpacity>
      )}

      {/* Lista de paradas */}
      {rota.status === "pendente" ? (
        <>
          <Text style={styles.dragHint}>Arraste pelo ícone ↕️ para reordenar antes de iniciar</Text>
          <DraggableFlatList
            data={[...rota.paradas].sort((a, b) => a.ordem - b.ordem)}
            keyExtractor={(item) => String(item.id)}
            activationDistance={12}
            autoscrollThreshold={60}
            autoscrollSpeed={80}
            dragItemOverflow={false}
            onDragEnd={({ data }) => {
              void salvarNovaOrdemParadas(data);
            }}
            renderItem={({ item, drag, isActive }: RenderItemParams<Parada>) =>
              renderParada(item, drag, isActive)
            }
            scrollEnabled={false}
          />
        </>
      ) : (
        rota.paradas.map((p) => renderParada(p))
      )}

      <Modal
        visible={modalRecebimentoAberto}
        transparent
        animationType="fade"
        onRequestClose={() => setModalRecebimentoAberto(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitulo}>Registrar Recebimento</Text>
            <Text style={styles.modalSubtitulo}>
              Pré-integração Stone/Operadora
            </Text>

            <View style={styles.opcoesLinha}>
              <TouchableOpacity
                style={[
                  styles.opcaoBtn,
                  formaRecebimento === "pix" && styles.opcaoBtnAtivo,
                ]}
                onPress={() => {
                  setFormaRecebimento("pix");
                  setParcelasRecebimento(1);
                }}
              >
                <Text
                  style={[
                    styles.opcaoTexto,
                    formaRecebimento === "pix" && styles.opcaoTextoAtivo,
                  ]}
                >
                  PIX
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.opcaoBtn,
                  formaRecebimento === "cartao_debito" && styles.opcaoBtnAtivo,
                ]}
                onPress={() => {
                  setFormaRecebimento("cartao_debito");
                  setParcelasRecebimento(1);
                }}
              >
                <Text
                  style={[
                    styles.opcaoTexto,
                    formaRecebimento === "cartao_debito" &&
                      styles.opcaoTextoAtivo,
                  ]}
                >
                  Débito
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.opcaoBtn,
                  formaRecebimento === "cartao_credito" && styles.opcaoBtnAtivo,
                ]}
                onPress={() => setFormaRecebimento("cartao_credito")}
              >
                <Text
                  style={[
                    styles.opcaoTexto,
                    formaRecebimento === "cartao_credito" &&
                      styles.opcaoTextoAtivo,
                  ]}
                >
                  Crédito
                </Text>
              </TouchableOpacity>
            </View>

            {formaRecebimento === "cartao_credito" && (
              <View style={styles.parcelasWrap}>
                <Text style={styles.parcelasTitulo}>Parcelas</Text>
                <View style={styles.parcelasGrid}>
                  {[1, 2, 3, 4, 5, 6].map((n) => (
                    <TouchableOpacity
                      key={n}
                      style={[
                        styles.parcelaBtn,
                        parcelasRecebimento === n && styles.parcelaBtnAtivo,
                      ]}
                      onPress={() => setParcelasRecebimento(n)}
                    >
                      <Text
                        style={[
                          styles.parcelaTexto,
                          parcelasRecebimento === n && styles.parcelaTextoAtivo,
                        ]}
                      >
                        {n}x
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            <View style={styles.modalAcoes}>
              <TouchableOpacity
                style={styles.modalCancelar}
                onPress={() => setModalRecebimentoAberto(false)}
              >
                <Text style={styles.modalCancelarText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.modalConfirmar,
                  processandoRecebimento && { opacity: 0.6 },
                ]}
                disabled={processandoRecebimento}
                onPress={registrarRecebimento}
              >
                <Text style={styles.modalConfirmarText}>
                  {processandoRecebimento ? "Enviando..." : "Registrar"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={modalVendaAberto}
        transparent
        animationType="slide"
        onRequestClose={() => setModalVendaAberto(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalCard, { maxHeight: '85%' }]}>
            <View style={styles.modalHeaderDetalhes}>
              <Text style={styles.modalTitulo}>🧾 Detalhes da Venda</Text>
              <TouchableOpacity onPress={() => setModalVendaAberto(false)}>
                <Text style={styles.fecharDetalhes}>Fechar</Text>
              </TouchableOpacity>
            </View>

            {loadingVenda ? (
              <View style={{ paddingVertical: 20 }}>
                <ActivityIndicator size="small" color="#2563eb" />
              </View>
            ) : (
              <ScrollView>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Cliente: </Text>
                  {vendaDetalhes?.cliente?.nome || 'N/A'}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Telefone: </Text>
                  {vendaDetalhes?.cliente?.celular || vendaDetalhes?.cliente?.telefone || 'N/A'}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Data: </Text>
                  {vendaDetalhes?.data_venda
                    ? new Date(vendaDetalhes.data_venda).toLocaleString('pt-BR')
                    : 'N/A'}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Pagamento: </Text>
                  {vendaDetalhes?.forma_pagamento || 'N/A'}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Status pagamento: </Text>
                  {vendaDetalhes?.status_pagamento || 'N/A'}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Endereço: </Text>
                  {vendaDetalhes?.endereco_entrega || 'N/A'}
                </Text>
                <Text style={styles.detalheLinha}>
                  <Text style={styles.detalheLabel}>Total: </Text>
                  R$ {Number(vendaDetalhes?.valor_total ?? vendaDetalhes?.total ?? 0).toFixed(2)}
                </Text>

                <Text style={[styles.detalheLabel, { marginTop: 12, marginBottom: 8 }]}>Itens da venda:</Text>
                {(vendaDetalhes?.itens || []).map((item, index) => (
                  <View
                    key={`${item.produto_nome || item.servico_descricao || 'item'}-${index}`}
                    style={styles.itemVenda}
                  >
                    <Text style={styles.itemVendaNome}>
                      {item.produto_nome || item.servico_descricao || 'Item'}
                    </Text>
                    <Text style={styles.itemVendaValor}>
                      {Number(item.quantidade || 0)} x R$ {Number(item.preco_unitario || 0).toFixed(2)}
                      {' • '}R$ {Number(item.subtotal || 0).toFixed(2)}
                    </Text>
                  </View>
                ))}
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

// ─── Estilos ─────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  errorText: { color: "#ef4444", fontSize: 16 },

  // Resumo
  resumo: {
    flexDirection: "row",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    justifyContent: "space-around",
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
    elevation: 1,
  },
  resumoItem: { alignItems: "center" },
  resumoValor: { fontSize: 22, fontWeight: "700", color: "#111827" },
  resumoLabel: { fontSize: 12, color: "#6b7280", marginTop: 2 },

  // Botão iniciar
  btnIniciar: {
    backgroundColor: "#2563eb",
    borderRadius: 10,
    padding: 14,
    alignItems: "center",
    marginBottom: 16,
  },
  btnIniciarText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  btnFinalizar: {
    backgroundColor: '#2563eb',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginBottom: 16,
  },
  btnFinalizarText: { color: '#fff', fontSize: 16, fontWeight: '700' },

  // Card de parada
  paradaCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
    elevation: 1,
  },
  paradaCardInativa: {
    opacity: 1,
  },
  paradaCardAtiva: {
    opacity: 0.95,
    borderWidth: 1,
    borderColor: "#2563eb",
    shadowOpacity: 0.16,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
    transform: [{ scale: 1.01 }],
  },
  paradaHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    marginBottom: 10,
  },
  ordemCircle: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: "#2563eb",
    justifyContent: "center",
    alignItems: "center",
    flexShrink: 0,
    marginTop: 2,
  },
  ordemText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  paradaInfo: { flex: 1 },
  paradaCliente: { fontSize: 15, fontWeight: "600", color: "#111827" },
  paradaEndereco: { fontSize: 13, color: "#6b7280", marginTop: 2 },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 20,
    flexShrink: 0,
  },
  statusBadgeText: { fontSize: 11, fontWeight: "600" },

  observacoes: {
    fontSize: 13,
    color: "#374151",
    marginBottom: 8,
    fontStyle: "italic",
  },

  // Botões de ação (mapa + ligar)
  paradaBotoes: { flexDirection: "row", gap: 8, marginBottom: 10 },
  btnMapa: {
    flex: 1,
    backgroundColor: "#eff6ff",
    borderRadius: 8,
    padding: 10,
    alignItems: "center",
  },
  btnMapaText: { color: "#2563eb", fontWeight: "600", fontSize: 13 },
  btnLigar: {
    flex: 1,
    backgroundColor: "#f0fdf4",
    borderRadius: 8,
    padding: 10,
    alignItems: "center",
  },
  btnLigarText: { color: "#16a34a", fontWeight: "600", fontSize: 13 },
  btnRecebimento: {
    flex: 1,
    backgroundColor: "#f5f3ff",
    borderColor: "#c4b5fd",
    borderWidth: 1,
    borderRadius: 8,
    padding: 10,
    alignItems: "center",
  },
  btnRecebimentoText: { color: "#6d28d9", fontWeight: "600", fontSize: 13 },
  btnDetalhes: {
    flex: 1,
    backgroundColor: '#e0f2fe',
    borderRadius: 8,
    padding: 10,
    alignItems: 'center',
  },
  btnDetalhesText: { color: '#0369a1', fontWeight: '600', fontSize: 13 },
  btnDrag: {
    paddingHorizontal: 6,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: "#eff6ff",
    marginRight: 8,
    marginTop: 2,
  },
  btnDragAtivo: {
    backgroundColor: "#dbeafe",
  },
  btnDragText: { fontSize: 14, color: "#1d4ed8", fontWeight: "700" },
  dragHint: {
    fontSize: 12,
    color: "#4b5563",
    marginBottom: 10,
  },

  // Ações de entrega
  paradaAcoes: { flexDirection: "row", gap: 8 },
  btnEntregue: {
    flex: 1,
    backgroundColor: "#10b981",
    borderRadius: 8,
    padding: 12,
    alignItems: "center",
  },
  btnEntregueText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  btnNaoEntregue: {
    flex: 1,
    backgroundColor: "#ef4444",
    borderRadius: 8,
    padding: 12,
    alignItems: "center",
  },
  btnNaoEntregueText: { color: "#fff", fontWeight: "700", fontSize: 14 },

  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
  },
  modalTitulo: { fontSize: 18, fontWeight: "700", color: "#111827" },
  modalHeaderDetalhes: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  fecharDetalhes: { color: '#dc2626', fontWeight: '700' },
  detalheLinha: { fontSize: 14, color: '#374151', marginBottom: 6 },
  detalheLabel: { fontWeight: '700', color: '#111827' },
  itemVenda: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
    backgroundColor: '#f9fafb',
  },
  itemVendaNome: { fontSize: 14, fontWeight: '600', color: '#111827' },
  itemVendaValor: { fontSize: 12, color: '#4b5563', marginTop: 4 },
  modalSubtitulo: {
    marginTop: 4,
    marginBottom: 12,
    color: "#6b7280",
    fontSize: 13,
  },
  opcoesLinha: { flexDirection: "row", gap: 8 },
  opcaoBtn: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  opcaoBtnAtivo: {
    borderColor: "#2563eb",
    backgroundColor: "#eff6ff",
  },
  opcaoTexto: { color: "#374151", fontWeight: "600" },
  opcaoTextoAtivo: { color: "#1d4ed8" },
  parcelasWrap: { marginTop: 12 },
  parcelasTitulo: { marginBottom: 8, color: "#374151", fontWeight: "600" },
  parcelasGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  parcelaBtn: {
    width: 52,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: "center",
  },
  parcelaBtnAtivo: {
    borderColor: "#2563eb",
    backgroundColor: "#eff6ff",
  },
  parcelaTexto: { color: "#374151", fontWeight: "600" },
  parcelaTextoAtivo: { color: "#1d4ed8" },
  modalAcoes: {
    marginTop: 16,
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 8,
  },
  modalCancelar: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
    backgroundColor: "#f3f4f6",
  },
  modalCancelarText: { color: "#111827", fontWeight: "700" },
  modalConfirmar: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
    backgroundColor: "#2563eb",
  },
  modalConfirmarText: { color: "#fff", fontWeight: "700" },
});
