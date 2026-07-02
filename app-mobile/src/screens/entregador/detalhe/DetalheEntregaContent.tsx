import React, { type Dispatch, type SetStateAction } from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";
import DraggableFlatList, {
  type RenderItemParams,
} from "react-native-draggable-flatlist";

import KeyboardSafeScrollView from "../../../components/KeyboardSafeScrollView";
import { detalheEntregaStyles as styles } from "./DetalheEntregaStyles";
import { DetalheEntregaModals } from "./DetalheEntregaModals";
import { DetalheEntregaStopCard } from "./DetalheEntregaStopCard";
import {
  rotaPermiteReordenacao,
  type FormaRecebimento,
  type Parada,
  type Rota,
  type VendaDetalhes,
} from "./DetalheEntregaUtils";

export type DetalheEntregaContentProps = {
  loading: boolean;
  rota: Rota | null;
  processando: number | null;
  processandoFinalizacao: boolean;
  iniciarRota: () => void | Promise<void>;
  finalizarRota: () => void | Promise<void>;
  salvarNovaOrdemParadas: (paradasOrdenadas: Parada[]) => boolean | Promise<boolean>;
  abrirModalOrdem: (parada: Parada) => void;
  abrirModalRecebimento: (paradaId: number) => void;
  abrirDetalhesVenda: (vendaId: number) => void | Promise<void>;
  marcarEntregue: (paradaId: number) => void | Promise<void>;
  marcarNaoEntregue: (paradaId: number) => void;
  modalOrdemAberto: boolean;
  paradaOrdemEmEdicao: Parada | null;
  novaOrdemTexto: string;
  setNovaOrdemTexto: Dispatch<SetStateAction<string>>;
  salvandoOrdemManual: boolean;
  fecharModalOrdem: () => void;
  confirmarNovaOrdemManual: () => void | Promise<void>;
  modalNaoEntregueAberto: boolean;
  paradaNaoEntregueId: number | null;
  motivoNaoEntregue: string;
  setMotivoNaoEntregue: Dispatch<SetStateAction<string>>;
  fecharModalNaoEntregue: () => void;
  confirmarNaoEntregue: () => void | Promise<void>;
  modalRecebimentoAberto: boolean;
  setModalRecebimentoAberto: Dispatch<SetStateAction<boolean>>;
  formaRecebimento: FormaRecebimento;
  setFormaRecebimento: Dispatch<SetStateAction<FormaRecebimento>>;
  parcelasRecebimento: number;
  setParcelasRecebimento: Dispatch<SetStateAction<number>>;
  processandoRecebimento: boolean;
  registrarRecebimento: () => void | Promise<void>;
  modalVendaAberto: boolean;
  setModalVendaAberto: Dispatch<SetStateAction<boolean>>;
  loadingVenda: boolean;
  vendaDetalhes: VendaDetalhes | null;
};

export function DetalheEntregaContent({
  loading,
  rota,
  processando,
  processandoFinalizacao,
  iniciarRota,
  finalizarRota,
  salvarNovaOrdemParadas,
  abrirModalOrdem,
  abrirModalRecebimento,
  abrirDetalhesVenda,
  marcarEntregue,
  marcarNaoEntregue,
  modalOrdemAberto,
  paradaOrdemEmEdicao,
  novaOrdemTexto,
  setNovaOrdemTexto,
  salvandoOrdemManual,
  fecharModalOrdem,
  confirmarNovaOrdemManual,
  modalNaoEntregueAberto,
  paradaNaoEntregueId,
  motivoNaoEntregue,
  setMotivoNaoEntregue,
  fecharModalNaoEntregue,
  confirmarNaoEntregue,
  modalRecebimentoAberto,
  setModalRecebimentoAberto,
  formaRecebimento,
  setFormaRecebimento,
  parcelasRecebimento,
  setParcelasRecebimento,
  processandoRecebimento,
  registrarRecebimento,
  modalVendaAberto,
  setModalVendaAberto,
  loadingVenda,
  vendaDetalhes,
}: DetalheEntregaContentProps) {
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
        <Text style={styles.errorText}>Rota nÃ£o encontrada.</Text>
      </View>
    );
  }

  const pendentes = rota.paradas.filter((p) => p.status === "pendente").length;
  const entregues = rota.paradas.filter((p) => p.status === "entregue").length;
  const podeFinalizar =
    ["em_rota", "em_andamento"].includes(rota.status) &&
    rota.paradas.length > 0 &&
    pendentes === 0;
  const podeReordenar = rotaPermiteReordenacao(rota.status);

  const renderParada = (
    parada: Parada,
    drag?: () => void,
    isActive?: boolean,
  ) => (
    <DetalheEntregaStopCard
      key={parada.id}
      parada={parada}
      rotaStatus={rota.status}
      processando={processando}
      drag={drag}
      isActive={isActive}
      abrirModalOrdem={abrirModalOrdem}
      abrirModalRecebimento={abrirModalRecebimento}
      abrirDetalhesVenda={abrirDetalhesVenda}
      marcarEntregue={marcarEntregue}
      marcarNaoEntregue={marcarNaoEntregue}
    />
  );

  return (
    <KeyboardSafeScrollView style={styles.container} contentContainerStyle={styles.content}>
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

      {rota.status === "pendente" && (
        <TouchableOpacity style={styles.btnIniciar} onPress={iniciarRota}>
          <Text style={styles.btnIniciarText}>? Iniciar Rota</Text>
        </TouchableOpacity>
      )}

      {podeFinalizar && (
        <TouchableOpacity
          style={[styles.btnFinalizar, processandoFinalizacao && { opacity: 0.6 }]}
          disabled={processandoFinalizacao}
          onPress={finalizarRota}
        >
          <Text style={styles.btnFinalizarText}>
            {processandoFinalizacao ? "Finalizando..." : "? Finalizar Rota"}
          </Text>
        </TouchableOpacity>
      )}

      {podeReordenar ? (
        <>
          <Text style={styles.dragHint}>
            Arraste pelo icone ou toque no numero azul para definir a ordem manualmente. Voce pode digitar n1, n2 ou apenas 1, 2.
          </Text>
          <DraggableFlatList
            data={[...rota.paradas].sort((a, b) => a.ordem - b.ordem)}
            keyExtractor={(item) => String(item.id)}
            activationDistance={4}
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
        rota.paradas.map((parada) => renderParada(parada))
      )}

      <DetalheEntregaModals
        rota={rota}
        processando={processando}
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
    </KeyboardSafeScrollView>
  );
}
